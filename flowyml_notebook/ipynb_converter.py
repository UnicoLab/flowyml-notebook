"""Bidirectional converter between Jupyter/IPython `.ipynb` and FlowyML notebook formats.

Provides:
- ``from_ipynb(source)`` — Import a `.ipynb` (v4) file/dict into a FlowyML ``NotebookFile``
- ``to_ipynb(notebook)``  — Export a FlowyML ``NotebookFile`` to `.ipynb` v4 JSON
- ``convert_file(input_path, output_path)`` — CLI-friendly auto-detect conversion

The `.ipynb` v4 format is straightforward JSON documented at:
https://nbformat.readthedocs.io/en/latest/format_description.html
We implement a lightweight parser here to avoid requiring ``nbformat`` as a dependency.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from flowyml_notebook.cells import (
    Cell,
    CellOutput,
    CellType,
    NotebookFile,
    NotebookMetadata,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import: .ipynb → FlowyML
# ---------------------------------------------------------------------------


def from_ipynb(source: str | Path | dict) -> NotebookFile:
    """Import a Jupyter/IPython notebook (.ipynb v4) into a FlowyML NotebookFile.

    Args:
        source: One of:
            - Path to a ``.ipynb`` file (str or Path)
            - A dict already parsed from the ``.ipynb`` JSON

    Returns:
        A ``NotebookFile`` populated with cells and metadata from the notebook.

    Raises:
        ValueError: If the notebook format version is unsupported.
        FileNotFoundError: If ``source`` is a path that doesn't exist.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Notebook file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
    elif isinstance(source, dict):
        data = source
    else:
        raise TypeError(f"Expected str, Path, or dict; got {type(source).__name__}")

    nbformat_version = data.get("nbformat", 4)
    if nbformat_version < 4:
        raise ValueError(
            f"Unsupported nbformat version {nbformat_version}. "
            "Only nbformat ≥ 4 is supported. "
            "Open the notebook in Jupyter to auto-upgrade, then retry."
        )

    # --- Extract metadata ---
    ipynb_meta = data.get("metadata", {})
    kernelspec = ipynb_meta.get("kernelspec", {})

    metadata = NotebookMetadata(
        name=kernelspec.get("display_name", "Imported Notebook"),
        description=f"Imported from .ipynb (kernel: {kernelspec.get('name', 'python3')})",
    )

    # --- Convert cells ---
    cells: list[Cell] = []
    for i, ipynb_cell in enumerate(data.get("cells", [])):
        cell = _convert_ipynb_cell(ipynb_cell, index=i)
        if cell is not None:
            cells.append(cell)

    notebook = NotebookFile(metadata=metadata, cells=cells)
    logger.info(
        f"Imported .ipynb notebook: {len(cells)} cells "
        f"(kernel: {kernelspec.get('name', 'unknown')})"
    )
    return notebook


def _convert_ipynb_cell(ipynb_cell: dict, index: int) -> Cell | None:
    """Convert a single .ipynb cell dict into a FlowyML Cell."""
    cell_type_str = ipynb_cell.get("cell_type", "code")
    source_data = ipynb_cell.get("source", "")

    # .ipynb stores source as either a string or a list of lines
    if isinstance(source_data, list):
        source = "".join(source_data)
    else:
        source = str(source_data)

    # Strip trailing newline (common in .ipynb)
    source = source.rstrip("\n")

    # Cell ID — use .ipynb id if available, else generate
    cell_id = ipynb_cell.get("id", str(uuid.uuid4())[:8])
    if len(cell_id) > 8:
        cell_id = cell_id[:8]

    # Map cell types
    if cell_type_str == "code":
        cell_type = CellType.CODE

        # Detect SQL magic cells: %%sql at the top
        stripped = source.lstrip()
        if stripped.startswith("%%sql"):
            cell_type = CellType.SQL
            # Remove the %%sql magic line
            sql_lines = stripped.split("\n", 1)
            source = sql_lines[1] if len(sql_lines) > 1 else ""

    elif cell_type_str == "markdown":
        cell_type = CellType.MARKDOWN
    elif cell_type_str == "raw":
        # Raw cells → code cells with content as a comment
        cell_type = CellType.CODE
        if source.strip():
            source = "\n".join(f"# {line}" if line else "#" for line in source.split("\n"))
    else:
        # Unknown cell type → code
        cell_type = CellType.CODE

    # Convert outputs
    outputs = _convert_ipynb_outputs(ipynb_cell.get("outputs", []))

    # Execution count
    exec_count = ipynb_cell.get("execution_count") or 0

    return Cell(
        id=cell_id,
        cell_type=cell_type,
        source=source,
        outputs=outputs,
        execution_count=exec_count,
        metadata=ipynb_cell.get("metadata", {}),
    )


def _convert_ipynb_outputs(ipynb_outputs: list[dict]) -> list[CellOutput]:
    """Convert .ipynb output list to FlowyML CellOutput list."""
    outputs: list[CellOutput] = []

    for out in ipynb_outputs:
        output_type_str = out.get("output_type", "")

        if output_type_str == "stream":
            # stdout/stderr text
            text = out.get("text", "")
            if isinstance(text, list):
                text = "".join(text)
            stream_name = out.get("name", "stdout")
            outputs.append(
                CellOutput(
                    output_type="text",
                    data=text,
                    metadata={"stream": stream_name},
                )
            )

        elif output_type_str == "error":
            # Exception traceback
            ename = out.get("ename", "Error")
            evalue = out.get("evalue", "")
            traceback_lines = out.get("traceback", [])
            error_text = f"{ename}: {evalue}"
            if traceback_lines:
                # .ipynb traceback contains ANSI escape codes; strip them
                import re

                clean_tb = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in traceback_lines]
                error_text = "\n".join(clean_tb)
            outputs.append(CellOutput(output_type="error", data=error_text))

        elif output_type_str in ("display_data", "execute_result"):
            # Rich output — pick best representation
            mime_data = out.get("data", {})
            meta = out.get("metadata", {})

            if "text/html" in mime_data:
                html = mime_data["text/html"]
                if isinstance(html, list):
                    html = "".join(html)
                outputs.append(
                    CellOutput(
                        output_type="html",
                        data=html,
                        metadata=meta,
                    )
                )
            elif "image/png" in mime_data:
                # Base64 encoded image
                b64 = mime_data["image/png"]
                if isinstance(b64, list):
                    b64 = "".join(b64)
                outputs.append(
                    CellOutput(
                        output_type="image",
                        data=f"data:image/png;base64,{b64}",
                        metadata=meta,
                    )
                )
            elif "image/svg+xml" in mime_data:
                svg = mime_data["image/svg+xml"]
                if isinstance(svg, list):
                    svg = "".join(svg)
                outputs.append(
                    CellOutput(
                        output_type="html",
                        data=svg,
                        metadata=meta,
                    )
                )
            elif "application/json" in mime_data:
                outputs.append(
                    CellOutput(
                        output_type="json",
                        data=json.dumps(mime_data["application/json"], indent=2, default=str),
                        metadata=meta,
                    )
                )
            elif "text/plain" in mime_data:
                text = mime_data["text/plain"]
                if isinstance(text, list):
                    text = "".join(text)
                outputs.append(
                    CellOutput(
                        output_type="text",
                        data=text,
                        metadata=meta,
                    )
                )

    return outputs


# ---------------------------------------------------------------------------
# Export: FlowyML → .ipynb
# ---------------------------------------------------------------------------


def to_ipynb(notebook: NotebookFile, include_outputs: bool = True) -> dict:
    """Export a FlowyML NotebookFile to Jupyter/IPython .ipynb v4 format.

    Args:
        notebook: The FlowyML notebook to export.
        include_outputs: Whether to include cell outputs in the export.

    Returns:
        A dict representing a valid ``.ipynb`` v4 JSON structure.
    """
    ipynb_cells = []

    for cell in notebook.cells:
        ipynb_cell = _to_ipynb_cell(cell, include_outputs=include_outputs)
        ipynb_cells.append(ipynb_cell)

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0",
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "codemirror_mode": {"name": "ipython", "version": 3},
            },
            "flowyml": {
                "name": notebook.metadata.name,
                "description": notebook.metadata.description,
                "author": notebook.metadata.author,
                "tags": notebook.metadata.tags,
                "server": notebook.metadata.server,
            },
        },
        "cells": ipynb_cells,
    }


def _to_ipynb_cell(cell: Cell, include_outputs: bool = True) -> dict:
    """Convert a FlowyML Cell to a .ipynb cell dict."""
    cell_id = cell.id
    # .ipynb cell IDs should be longer UUIDs, but short ones are also valid
    if len(cell_id) < 8:
        cell_id = cell_id + str(uuid.uuid4())[: 8 - len(cell_id)]

    if cell.cell_type == CellType.CODE:
        outputs = _to_ipynb_outputs(cell.outputs) if include_outputs else []
        return {
            "cell_type": "code",
            "id": cell_id,
            "source": cell.source,
            "metadata": cell.metadata or {},
            "outputs": outputs,
            "execution_count": cell.execution_count or None,
        }

    elif cell.cell_type == CellType.MARKDOWN:
        return {
            "cell_type": "markdown",
            "id": cell_id,
            "source": cell.source,
            "metadata": cell.metadata or {},
        }

    elif cell.cell_type == CellType.SQL:
        # SQL cells become code cells with %%sql magic prefix
        source = f"%%sql\n{cell.source}" if cell.source else "%%sql"
        outputs = _to_ipynb_outputs(cell.outputs) if include_outputs else []
        return {
            "cell_type": "code",
            "id": cell_id,
            "source": source,
            "metadata": {"flowyml_cell_type": "sql"},
            "outputs": outputs,
            "execution_count": cell.execution_count or None,
        }

    else:
        # Fallback for unknown types
        return {
            "cell_type": "code",
            "id": cell_id,
            "source": cell.source,
            "metadata": cell.metadata or {},
            "outputs": [],
            "execution_count": None,
        }


def _to_ipynb_outputs(outputs: list[CellOutput]) -> list[dict]:
    """Convert FlowyML CellOutputs to .ipynb output dicts."""
    ipynb_outputs = []

    for output in outputs:
        if output.output_type == "text":
            stream = (output.metadata or {}).get("stream", "stdout")
            ipynb_outputs.append(
                {
                    "output_type": "stream",
                    "name": stream,
                    "text": output.data or "",
                }
            )

        elif output.output_type == "error":
            # Parse error text
            error_text = str(output.data or "Error")
            parts = error_text.split(": ", 1)
            ename = parts[0] if len(parts) > 1 else "Error"
            evalue = parts[1] if len(parts) > 1 else error_text
            ipynb_outputs.append(
                {
                    "output_type": "error",
                    "ename": ename,
                    "evalue": evalue,
                    "traceback": error_text.split("\n"),
                }
            )

        elif output.output_type == "html":
            ipynb_outputs.append(
                {
                    "output_type": "display_data",
                    "data": {
                        "text/html": output.data or "",
                        "text/plain": "",
                    },
                    "metadata": output.metadata or {},
                }
            )

        elif output.output_type == "image":
            # Extract base64 from data URI
            data_str = str(output.data or "")
            b64 = data_str
            if "base64," in data_str:
                b64 = data_str.split("base64,", 1)[1]
            ipynb_outputs.append(
                {
                    "output_type": "display_data",
                    "data": {
                        "image/png": b64,
                        "text/plain": "<Image>",
                    },
                    "metadata": output.metadata or {},
                }
            )

        elif output.output_type == "dataframe":
            # DataFrames → execute_result with text/plain
            ipynb_outputs.append(
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": str(output.data),
                    },
                    "metadata": output.metadata or {},
                    "execution_count": None,
                }
            )

        elif output.output_type == "json":
            ipynb_outputs.append(
                {
                    "output_type": "execute_result",
                    "data": {
                        "application/json": output.data,
                        "text/plain": str(output.data),
                    },
                    "metadata": output.metadata or {},
                    "execution_count": None,
                }
            )

        else:
            # Generic text output
            ipynb_outputs.append(
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": str(output.data or ""),
                    },
                    "metadata": output.metadata or {},
                    "execution_count": None,
                }
            )

    return ipynb_outputs


# ---------------------------------------------------------------------------
# File conversion helper
# ---------------------------------------------------------------------------


def convert_file(input_path: str | Path, output_path: str | Path | None = None) -> str:
    """Convert a notebook file between .ipynb and .py formats.

    Auto-detects the conversion direction based on file extension:
    - ``.ipynb`` → ``.py`` (FlowyML percent format)
    - ``.py`` → ``.ipynb`` (Jupyter format)

    Args:
        input_path: Path to the input notebook file.
        output_path: Path to the output file.
            Defaults to the same name with the opposite extension.

    Returns:
        Path to the output file.

    Raises:
        ValueError: If the input file extension is unsupported.
    """
    from flowyml_notebook.cells import parse_notebook, serialize_notebook

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix == ".ipynb":
        # .ipynb → .py
        out_path = Path(output_path) if output_path else input_path.with_suffix(".py")
        notebook = from_ipynb(input_path)
        content = serialize_notebook(notebook)
        out_path.write_text(content, encoding="utf-8")
        logger.info(f"Converted {input_path} → {out_path} ({len(notebook.cells)} cells)")
        return str(out_path)

    elif input_path.suffix == ".py":
        # .py → .ipynb
        out_path = Path(output_path) if output_path else input_path.with_suffix(".ipynb")
        content = input_path.read_text(encoding="utf-8")
        notebook = parse_notebook(content)
        ipynb_data = to_ipynb(notebook)
        out_path.write_text(
            json.dumps(ipynb_data, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"Converted {input_path} → {out_path} ({len(notebook.cells)} cells)")
        return str(out_path)

    else:
        raise ValueError(
            f"Unsupported file extension: {input_path.suffix}. Use .ipynb or .py files."
        )
