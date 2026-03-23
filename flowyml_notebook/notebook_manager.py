"""Notebook file manager for multi-notebook support.

Manages a directory of .fml.json notebook files with CRUD operations,
metadata indexing, and auto-save capability.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_NOTEBOOKS_DIR = Path.home() / ".flowyml" / "notebooks"


class NotebookFileInfo:
    """Metadata about a saved notebook file."""

    def __init__(
        self,
        id: str,
        name: str,
        path: Path,
        created_at: str | None = None,
        modified_at: str | None = None,
        cell_count: int = 0,
        description: str = "",
        tags: list[str] | None = None,
    ):
        self.id = id
        self.name = name
        self.path = path
        self.created_at = created_at or datetime.now().isoformat()
        self.modified_at = modified_at or datetime.now().isoformat()
        self.cell_count = cell_count
        self.description = description
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "cell_count": self.cell_count,
            "description": self.description,
            "tags": self.tags,
        }


class NotebookManager:
    """Manages a directory of notebook files."""

    def __init__(self, notebooks_dir: str | Path | None = None):
        self.notebooks_dir = Path(notebooks_dir) if notebooks_dir else DEFAULT_NOTEBOOKS_DIR
        self.notebooks_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, NotebookFileInfo] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan the notebooks directory and build/refresh the index."""
        self._index.clear()
        for path in sorted(self.notebooks_dir.glob("*.fml.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                meta = data.get("metadata", {})
                nb_id = meta.get("id", str(uuid.uuid4()))
                info = NotebookFileInfo(
                    id=nb_id,
                    name=meta.get("name", path.stem.replace(".fml", "")),
                    path=path,
                    created_at=meta.get("created_at"),
                    modified_at=meta.get("modified_at", datetime.fromtimestamp(path.stat().st_mtime).isoformat()),
                    cell_count=len(data.get("cells", [])),
                    description=meta.get("description", ""),
                    tags=meta.get("tags", []),
                )
                self._index[nb_id] = info
            except Exception as e:
                logger.warning(f"Failed to read notebook {path}: {e}")

    def list_notebooks(self) -> list[dict[str, Any]]:
        """List all notebooks with metadata."""
        self._scan()
        return [info.to_dict() for info in sorted(self._index.values(), key=lambda x: x.modified_at or "", reverse=True)]

    def create_notebook(self, name: str = "Untitled", description: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        """Create a new empty notebook."""
        nb_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        filename = f"{name.lower().replace(' ', '_')}_{nb_id}.fml.json"
        path = self.notebooks_dir / filename

        notebook_data = {
            "metadata": {
                "id": nb_id,
                "name": name,
                "description": description,
                "tags": tags or [],
                "created_at": now,
                "modified_at": now,
                "kernel": "python3",
                "version": "1.1.0",
            },
            "cells": [],
        }

        path.write_text(json.dumps(notebook_data, indent=2), encoding="utf-8")
        logger.info(f"Created notebook: {name} ({nb_id})")

        info = NotebookFileInfo(
            id=nb_id, name=name, path=path,
            created_at=now, modified_at=now,
            description=description, tags=tags or [],
        )
        self._index[nb_id] = info
        return info.to_dict()

    def get_notebook(self, nb_id: str) -> dict[str, Any] | None:
        """Get full notebook data by ID."""
        info = self._index.get(nb_id)
        if not info or not info.path.exists():
            return None
        try:
            return json.loads(info.path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def rename_notebook(self, nb_id: str, new_name: str) -> dict[str, Any] | None:
        """Rename a notebook."""
        info = self._index.get(nb_id)
        if not info or not info.path.exists():
            return None

        try:
            data = json.loads(info.path.read_text(encoding="utf-8"))
            data["metadata"]["name"] = new_name
            data["metadata"]["modified_at"] = datetime.now().isoformat()
            info.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            info.name = new_name
            info.modified_at = data["metadata"]["modified_at"]
            return info.to_dict()
        except Exception as e:
            logger.error(f"Failed to rename notebook {nb_id}: {e}")
            return None

    def update_metadata(self, nb_id: str, description: str | None = None, tags: list[str] | None = None) -> dict[str, Any] | None:
        """Update notebook metadata (description, tags)."""
        info = self._index.get(nb_id)
        if not info or not info.path.exists():
            return None

        try:
            data = json.loads(info.path.read_text(encoding="utf-8"))
            if description is not None:
                data["metadata"]["description"] = description
                info.description = description
            if tags is not None:
                data["metadata"]["tags"] = tags
                info.tags = tags
            data["metadata"]["modified_at"] = datetime.now().isoformat()
            info.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            info.modified_at = data["metadata"]["modified_at"]
            return info.to_dict()
        except Exception as e:
            logger.error(f"Failed to update notebook {nb_id}: {e}")
            return None

    def delete_notebook(self, nb_id: str) -> bool:
        """Delete a notebook file."""
        info = self._index.get(nb_id)
        if not info:
            return False
        try:
            if info.path.exists():
                info.path.unlink()
            del self._index[nb_id]
            logger.info(f"Deleted notebook: {info.name} ({nb_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to delete notebook {nb_id}: {e}")
            return False

    def duplicate_notebook(self, nb_id: str) -> dict[str, Any] | None:
        """Duplicate a notebook."""
        info = self._index.get(nb_id)
        if not info or not info.path.exists():
            return None

        try:
            data = json.loads(info.path.read_text(encoding="utf-8"))
            new_name = f"{info.name} (copy)"
            return self.create_notebook(
                name=new_name,
                description=data.get("metadata", {}).get("description", ""),
                tags=data.get("metadata", {}).get("tags", []),
            )
        except Exception as e:
            logger.error(f"Failed to duplicate notebook {nb_id}: {e}")
            return None

    def save_notebook_data(self, nb_id: str, cells: list[dict], metadata: dict | None = None) -> bool:
        """Save notebook cells and metadata."""
        info = self._index.get(nb_id)
        if not info or not info.path.exists():
            return False

        try:
            data = json.loads(info.path.read_text(encoding="utf-8"))
            data["cells"] = cells
            if metadata:
                data["metadata"].update(metadata)
            data["metadata"]["modified_at"] = datetime.now().isoformat()
            info.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            info.cell_count = len(cells)
            info.modified_at = data["metadata"]["modified_at"]
            return True
        except Exception as e:
            logger.error(f"Failed to save notebook {nb_id}: {e}")
            return False
