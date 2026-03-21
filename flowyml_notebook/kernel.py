"""WebSocket execution kernel — bridges the browser GUI to the Python runtime.

Receives cell execution requests via WebSocket, executes them in a
NotebookSession, and streams outputs back in real-time.
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Any

from flowyml_notebook.cells import Cell, CellType
from flowyml_notebook.core import Notebook, NotebookSession, ExecutionResult
from flowyml_notebook.reactive import CellState

logger = logging.getLogger(__name__)


class KernelMessage:
    """Protocol message between GUI and kernel."""

    # Client → Kernel
    EXECUTE_CELL = "execute_cell"
    EXECUTE_ALL = "execute_all"
    UPDATE_CELL = "update_cell"
    ADD_CELL = "add_cell"
    DELETE_CELL = "delete_cell"
    MOVE_CELL = "move_cell"
    INTERRUPT = "interrupt"
    RESET_KERNEL = "reset_kernel"
    GET_STATE = "get_state"
    GET_VARIABLES = "get_variables"
    GET_COMPLETIONS = "get_completions"
    SAVE_NOTEBOOK = "save_notebook"
    LOAD_NOTEBOOK = "load_notebook"

    # Kernel → Client
    CELL_OUTPUT = "cell_output"
    CELL_STATE = "cell_state"
    CELL_COMPLETE = "cell_complete"
    EXECUTION_ERROR = "execution_error"
    STATE_UPDATE = "state_update"
    VARIABLES_UPDATE = "variables_update"
    GRAPH_UPDATE = "graph_update"
    NOTEBOOK_SAVED = "notebook_saved"
    NOTEBOOK_LOADED = "notebook_loaded"
    COMPLETIONS = "completions"
    KERNEL_STATUS = "kernel_status"


class NotebookKernel:
    """WebSocket-bridged notebook execution kernel.

    Handles bidirectional communication between the browser GUI
    and the Python execution environment.
    """

    def __init__(self, notebook: Notebook | None = None):
        self.notebook = notebook or Notebook()
        self._connections: list[Any] = []  # WebSocket connections
        self._executing = False
        self._interrupt_requested = False

    async def handle_message(self, websocket: Any, raw_message: str) -> None:
        """Process an incoming WebSocket message from the GUI.

        Args:
            websocket: The WebSocket connection.
            raw_message: JSON-encoded message string.
        """
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            data = message.get("data", {})

            handler = {
                KernelMessage.EXECUTE_CELL: self._handle_execute_cell,
                KernelMessage.EXECUTE_ALL: self._handle_execute_all,
                KernelMessage.UPDATE_CELL: self._handle_update_cell,
                KernelMessage.ADD_CELL: self._handle_add_cell,
                KernelMessage.DELETE_CELL: self._handle_delete_cell,
                KernelMessage.MOVE_CELL: self._handle_move_cell,
                KernelMessage.INTERRUPT: self._handle_interrupt,
                KernelMessage.RESET_KERNEL: self._handle_reset,
                KernelMessage.GET_STATE: self._handle_get_state,
                KernelMessage.GET_VARIABLES: self._handle_get_variables,
                KernelMessage.GET_COMPLETIONS: self._handle_get_completions,
                KernelMessage.SAVE_NOTEBOOK: self._handle_save,
                KernelMessage.LOAD_NOTEBOOK: self._handle_load,
            }.get(msg_type)

            if handler:
                await handler(websocket, data)
            else:
                await self._send(websocket, KernelMessage.EXECUTION_ERROR, {
                    "error": f"Unknown message type: {msg_type}"
                })

        except json.JSONDecodeError:
            await self._send(websocket, KernelMessage.EXECUTION_ERROR, {
                "error": "Invalid JSON message"
            })
        except Exception as e:
            logger.error(f"Kernel error: {e}", exc_info=True)
            await self._send(websocket, KernelMessage.EXECUTION_ERROR, {
                "error": str(e), "traceback": traceback.format_exc()
            })

    async def _handle_execute_cell(self, ws: Any, data: dict) -> None:
        """Execute a single cell with reactive downstream propagation."""
        cell_id = data.get("cell_id")
        reactive = data.get("reactive", True)

        if not cell_id:
            await self._send(ws, KernelMessage.EXECUTION_ERROR, {"error": "Missing cell_id"})
            return

        self._executing = True
        self._interrupt_requested = False

        try:
            if reactive:
                results = await asyncio.get_event_loop().run_in_executor(
                    None, self.notebook.execute_cell_reactive, cell_id
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.notebook.execute_cell, cell_id
                )
                results = [result]

            for result in results:
                await self._send(ws, KernelMessage.CELL_COMPLETE, result.to_dict())
                # Update cell state in graph
                await self._send(ws, KernelMessage.CELL_STATE, {
                    "cell_id": result.cell_id,
                    "state": self.notebook.graph.get_cell_state(result.cell_id).value,
                })

            # Send updated graph and variables
            await self._send(ws, KernelMessage.GRAPH_UPDATE, self.notebook.graph.to_dict())
            await self._send(ws, KernelMessage.VARIABLES_UPDATE, self.notebook.session.get_variables())

        finally:
            self._executing = False

    async def _handle_execute_all(self, ws: Any, data: dict) -> None:
        """Execute all cells in order."""
        self._executing = True
        self._interrupt_requested = False

        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None, self.notebook.run
            )
            for result in results:
                await self._send(ws, KernelMessage.CELL_COMPLETE, result.to_dict())

            await self._send(ws, KernelMessage.GRAPH_UPDATE, self.notebook.graph.to_dict())
            await self._send(ws, KernelMessage.VARIABLES_UPDATE, self.notebook.session.get_variables())

        finally:
            self._executing = False

    async def _handle_update_cell(self, ws: Any, data: dict) -> None:
        """Update cell source and report stale cells."""
        cell_id = data.get("cell_id")
        source = data.get("source", "")

        stale = self.notebook.update_cell(cell_id, source)

        # Notify about stale cells
        for stale_id in stale:
            await self._send(ws, KernelMessage.CELL_STATE, {
                "cell_id": stale_id, "state": CellState.STALE.value,
            })

        await self._send(ws, KernelMessage.GRAPH_UPDATE, self.notebook.graph.to_dict())

    async def _handle_add_cell(self, ws: Any, data: dict) -> None:
        """Add a new cell."""
        source = data.get("source", "")
        cell_type = CellType(data.get("cell_type", "code"))
        name = data.get("name", "")
        index = data.get("index")  # None = append

        cell = self.notebook.cell(source, cell_type, name)

        if index is not None:
            self.notebook.notebook.move_cell(cell.id, index)

        await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())

    async def _handle_delete_cell(self, ws: Any, data: dict) -> None:
        """Delete a cell."""
        cell_id = data.get("cell_id")
        self.notebook.notebook.remove_cell(cell_id)
        stale = self.notebook.graph.remove_cell(cell_id)

        for stale_id in stale:
            await self._send(ws, KernelMessage.CELL_STATE, {
                "cell_id": stale_id, "state": CellState.STALE.value,
            })

        await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())

    async def _handle_move_cell(self, ws: Any, data: dict) -> None:
        """Move a cell to a new position."""
        cell_id = data.get("cell_id")
        new_index = data.get("index", 0)
        self.notebook.notebook.move_cell(cell_id, new_index)
        await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())

    async def _handle_interrupt(self, ws: Any, data: dict) -> None:
        """Interrupt current execution."""
        self._interrupt_requested = True
        await self._send(ws, KernelMessage.KERNEL_STATUS, {"status": "interrupted"})

    async def _handle_reset(self, ws: Any, data: dict) -> None:
        """Reset the kernel (clear namespace)."""
        self.notebook.session.reset()
        # Mark all cells as idle
        for cell in self.notebook.cells:
            self.notebook.graph.set_cell_state(cell.id, CellState.IDLE)
        await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())
        await self._send(ws, KernelMessage.KERNEL_STATUS, {"status": "restarted"})

    async def _handle_get_state(self, ws: Any, data: dict) -> None:
        """Send complete notebook state."""
        await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())

    async def _handle_get_variables(self, ws: Any, data: dict) -> None:
        """Send current variable inspector data."""
        await self._send(ws, KernelMessage.VARIABLES_UPDATE, self.notebook.session.get_variables())

    async def _handle_get_completions(self, ws: Any, data: dict) -> None:
        """Get code completions for the cursor position."""
        source = data.get("source", "")
        cursor_pos = data.get("cursor_pos", len(source))

        completions = []
        try:
            if self.notebook.session._ip:
                # Use IPython's completer
                with_text = source[:cursor_pos]
                _, matches = self.notebook.session._ip.complete(with_text)
                completions = matches[:50]  # Limit results
        except Exception:
            pass

        await self._send(ws, KernelMessage.COMPLETIONS, {"completions": completions})

    async def _handle_save(self, ws: Any, data: dict) -> None:
        """Save notebook to file."""
        path = data.get("path")
        saved_path = self.notebook.save(path)
        await self._send(ws, KernelMessage.NOTEBOOK_SAVED, {"path": saved_path})

    async def _handle_load(self, ws: Any, data: dict) -> None:
        """Load notebook from file."""
        path = data.get("path")
        if path:
            self.notebook.load(path)
            await self._send(ws, KernelMessage.STATE_UPDATE, self.notebook.get_state())
            await self._send(ws, KernelMessage.NOTEBOOK_LOADED, {"path": path})

    async def _send(self, ws: Any, msg_type: str, data: dict) -> None:
        """Send a message to the WebSocket client."""
        message = json.dumps({
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }, default=str)

        try:
            await ws.send_text(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
