"""Cell model and pure Python file format (.py) parser/writer.

Uses the industry-standard **percent format** (`# %%`) which is natively
supported by VS Code, PyCharm, Spyder, and Jupyter. This gives users
a first-class notebook experience in ANY editor — no extension needed.

File format example:
    # /// flowyml-notebook
    # name: my_analysis
    # version: 1
    # ///

    # %% [code] id=abc123 "Load Data"
    import pandas as pd
    df = pd.read_csv("data.csv")

    # %% [markdown]
    # ## Analysis Results
    # This shows the key findings.

    # %% [sql] id=def456
    # SELECT * FROM experiments WHERE metric > 0.9

    # %% [code] id=ghi789 "Train Model"
    model = train(df)

IDE behavior:
    - VS Code: Shows "Run Cell" buttons, cell folding, interactive output
    - PyCharm: Recognizes cells with run buttons
    - Spyder: Native cell support
    - Any editor: Valid Python file with clear visual separators
    - CLI: `python my_notebook.py` runs the entire file as a script
    - Git: Clean diffs, no JSON noise
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# --- Regex patterns for parsing ---

# PEP 723-style metadata block
_METADATA_START = re.compile(r"^# /// flowyml-notebook\s*$")
_METADATA_END = re.compile(r"^# ///\s*$")
_METADATA_LINE = re.compile(r"^# (\w[\w_]*):\s*(.+)$")

# Percent format cell marker (VS Code / Spyder / PyCharm compatible)
# Matches: # %% [type] id=xxx "name"
# All parts after # %% are optional
_CELL_MARKER = re.compile(
    r'^# %%'                          # Required: cell marker
    r'(?:\s+\[(\w+)\])?'             # Optional: [code], [markdown], [sql]
    r'(?:\s+id=(\S+))?'              # Optional: id=abc123
    r'(?:\s+"([^"]*)")?'             # Optional: "Cell Name"
    r'\s*$'
)


class CellType(str, Enum):
    """Type of notebook cell."""

    CODE = "code"
    MARKDOWN = "markdown"
    SQL = "sql"


@dataclass
class CellOutput:
    """Output from cell execution."""

    output_type: str  # "text", "html", "image", "dataframe", "chart", "error", "widget", "asset", "json"
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialize for API/WebSocket transmission."""
        import json

        # For complex types (list, dict), use json.dumps to produce valid JSON
        # str() produces Python repr with single quotes which breaks JSON.parse()
        if self.data is None:
            serialized_data = None
        elif isinstance(self.data, (list, dict)):
            try:
                serialized_data = json.dumps(self.data, default=str)
            except (TypeError, ValueError):
                serialized_data = str(self.data)
        else:
            serialized_data = str(self.data)

        return {
            "output_type": self.output_type,
            "data": serialized_data,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class Cell:
    """A single notebook cell."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cell_type: CellType = CellType.CODE
    source: str = ""
    name: str = ""  # Optional display name
    outputs: list[CellOutput] = field(default_factory=list)
    execution_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_executed: str | None = None

    def to_dict(self) -> dict:
        """Serialize for API/WebSocket transmission."""
        return {
            "id": self.id,
            "cell_type": self.cell_type.value,
            "source": self.source,
            "name": self.name,
            "outputs": [o.to_dict() for o in self.outputs],
            "execution_count": self.execution_count,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_executed": self.last_executed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cell":
        """Deserialize from API/WebSocket data."""
        outputs = [
            CellOutput(
                output_type=o.get("output_type", "text"),
                data=o.get("data"),
                metadata=o.get("metadata", {}),
                timestamp=o.get("timestamp", ""),
            )
            for o in data.get("outputs", [])
        ]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            cell_type=CellType(data.get("cell_type", "code")),
            source=data.get("source", ""),
            name=data.get("name", ""),
            outputs=outputs,
            execution_count=data.get("execution_count", 0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_executed=data.get("last_executed"),
        )


@dataclass
class NotebookMetadata:
    """Metadata header for a notebook file."""

    name: str = "untitled"
    version: int = 1
    server: str = ""
    author: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "server": self.server,
            "author": self.author,
            "description": self.description,
            "created_at": self.created_at,
            "tags": self.tags,
        }


@dataclass
class NotebookFile:
    """A complete notebook file with metadata and cells."""

    metadata: NotebookMetadata = field(default_factory=NotebookMetadata)
    cells: list[Cell] = field(default_factory=list)

    def add_cell(
        self,
        source: str = "",
        cell_type: CellType = CellType.CODE,
        name: str = "",
        cell_id: str | None = None,
    ) -> Cell:
        """Add a new cell to the notebook."""
        cell = Cell(
            id=cell_id or str(uuid.uuid4())[:8],
            cell_type=cell_type,
            source=source,
            name=name,
        )
        self.cells.append(cell)
        return cell

    def remove_cell(self, cell_id: str) -> bool:
        """Remove a cell by ID."""
        for i, cell in enumerate(self.cells):
            if cell.id == cell_id:
                self.cells.pop(i)
                return True
        return False

    def move_cell(self, cell_id: str, new_index: int) -> bool:
        """Move a cell to a new position."""
        for i, cell in enumerate(self.cells):
            if cell.id == cell_id:
                self.cells.pop(i)
                self.cells.insert(min(new_index, len(self.cells)), cell)
                return True
        return False

    def get_cell(self, cell_id: str) -> Cell | None:
        """Get a cell by ID."""
        for cell in self.cells:
            if cell.id == cell_id:
                return cell
        return None

    def to_dict(self) -> dict:
        """Serialize the entire notebook."""
        return {
            "metadata": self.metadata.to_dict(),
            "cells": [c.to_dict() for c in self.cells],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotebookFile":
        """Deserialize from dict."""
        meta_data = data.get("metadata", {})
        metadata = NotebookMetadata(
            name=meta_data.get("name", "untitled"),
            version=meta_data.get("version", 1),
            server=meta_data.get("server", ""),
            author=meta_data.get("author", ""),
            description=meta_data.get("description", ""),
            created_at=meta_data.get("created_at", ""),
            tags=meta_data.get("tags", []),
        )
        cells = [Cell.from_dict(c) for c in data.get("cells", [])]
        return cls(metadata=metadata, cells=cells)


def serialize_notebook(notebook: NotebookFile) -> str:
    """Serialize a notebook to the pure Python percent format.

    The output is a valid Python file that:
    - Runs with `python notebook.py` (code cells execute, markdown/SQL are comments)
    - Shows as interactive cells in VS Code / PyCharm / Spyder
    - Has clean git diffs
    - Can be linted with ruff/black
    - Can be imported as a Python module
    """
    lines: list[str] = []

    # Write metadata header (PEP 723 inspired)
    lines.append("# /// flowyml-notebook")
    lines.append(f"# name: {notebook.metadata.name}")
    lines.append(f"# version: {notebook.metadata.version}")
    if notebook.metadata.server:
        lines.append(f"# server: {notebook.metadata.server}")
    if notebook.metadata.author:
        lines.append(f"# author: {notebook.metadata.author}")
    if notebook.metadata.description:
        lines.append(f"# description: {notebook.metadata.description}")
    if notebook.metadata.tags:
        lines.append(f"# tags: {', '.join(notebook.metadata.tags)}")
    lines.append("# ///")
    lines.append("")

    # Write cells using percent format
    for cell in notebook.cells:
        # Build cell marker: # %% [type] id=xxx "name"
        marker_parts = ["# %%"]

        # Always include type for clarity
        marker_parts.append(f"[{cell.cell_type.value}]")

        # Include cell ID for round-trip fidelity
        marker_parts.append(f"id={cell.id}")

        # Include name if set
        if cell.name:
            marker_parts.append(f'"{cell.name}"')

        lines.append(" ".join(marker_parts))

        if cell.cell_type == CellType.CODE:
            # Code cells: written as-is (executable Python)
            if cell.source.strip():
                lines.append(cell.source.rstrip())
            else:
                lines.append("pass  # empty cell")
        elif cell.cell_type == CellType.MARKDOWN:
            # Markdown cells: each line prefixed with #
            # VS Code recognizes # %% [markdown] cells and renders
            # the comments as markdown
            for md_line in cell.source.split("\n"):
                lines.append(f"# {md_line}" if md_line else "#")
        elif cell.cell_type == CellType.SQL:
            # SQL cells: stored as comments with a magic prefix
            # The notebook engine interprets these; as Python they're just comments
            lines.append("# %%sql")
            for sql_line in cell.source.split("\n"):
                lines.append(f"# {sql_line}" if sql_line else "#")

        lines.append("")  # Blank separator between cells

    return "\n".join(lines) + "\n"


def parse_notebook(source: str) -> NotebookFile:
    """Parse a .py notebook file in percent format back into a NotebookFile.

    Handles:
    - Standard percent format (# %%) as used by VS Code
    - FlowyML extensions (id=, [type], "name")
    - PEP 723-style metadata block
    - Round-trip fidelity: parse(serialize(nb)) preserves structure
    """
    lines = source.split("\n")
    metadata = NotebookMetadata()
    cells: list[Cell] = []

    i = 0
    total = len(lines)

    # Parse metadata header if present
    if i < total and _METADATA_START.match(lines[i]):
        i += 1
        while i < total and not _METADATA_END.match(lines[i]):
            m = _METADATA_LINE.match(lines[i])
            if m:
                key, value = m.group(1), m.group(2).strip()
                if key == "name":
                    metadata.name = value
                elif key == "version":
                    try:
                        metadata.version = int(value)
                    except ValueError:
                        metadata.version = 1
                elif key == "server":
                    metadata.server = value
                elif key == "author":
                    metadata.author = value
                elif key == "description":
                    metadata.description = value
                elif key == "tags":
                    metadata.tags = [t.strip() for t in value.split(",")]
                elif key == "created_at":
                    metadata.created_at = value
            i += 1
        if i < total:
            i += 1  # Skip closing # ///

    # Skip blank lines after metadata
    while i < total and not lines[i].strip():
        i += 1

    # Parse cells
    while i < total:
        line = lines[i]

        # Skip blank lines between cells at top level
        if not line.strip():
            i += 1
            continue

        # Check for cell marker
        cell_match = _CELL_MARKER.match(line)
        if cell_match:
            cell_type_str = cell_match.group(1) or "code"
            cell_id = cell_match.group(2) or str(uuid.uuid4())[:8]
            cell_name = cell_match.group(3) or ""

            try:
                cell_type = CellType(cell_type_str)
            except ValueError:
                cell_type = CellType.CODE

            i += 1

            # Collect cell content until next cell marker or EOF
            content_lines: list[str] = []
            while i < total:
                if _CELL_MARKER.match(lines[i]):
                    break
                content_lines.append(lines[i])
                i += 1

            # Remove trailing blank lines
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()

            # Process content based on cell type
            if cell_type == CellType.MARKDOWN:
                source_lines = []
                for cl in content_lines:
                    if cl.startswith("# "):
                        source_lines.append(cl[2:])
                    elif cl == "#":
                        source_lines.append("")
                    else:
                        source_lines.append(cl)
                source_text = "\n".join(source_lines)

            elif cell_type == CellType.SQL:
                source_lines = []
                for cl in content_lines:
                    # Skip the %%sql magic prefix
                    if cl.strip() == "# %%sql":
                        continue
                    if cl.startswith("# "):
                        source_lines.append(cl[2:])
                    elif cl == "#":
                        source_lines.append("")
                    else:
                        source_lines.append(cl)
                source_text = "\n".join(source_lines)

            else:  # CODE
                source_text = "\n".join(content_lines)
                if source_text.strip() == "pass  # empty cell":
                    source_text = ""

            cells.append(
                Cell(id=cell_id, cell_type=cell_type, source=source_text, name=cell_name)
            )

        else:
            # Content before any cell marker — treat as an implicit code cell
            pre_content: list[str] = []
            while i < total and not _CELL_MARKER.match(lines[i]):
                pre_content.append(lines[i])
                i += 1
            source_text = "\n".join(pre_content).strip()
            if source_text:
                cells.append(Cell(cell_type=CellType.CODE, source=source_text))

    return NotebookFile(metadata=metadata, cells=cells)
