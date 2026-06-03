"""Data lineage tracker for notebook DataFrames.

Tracks how pandas DataFrames evolve across cell executions by capturing
snapshots before and after each cell runs.  Computes structural diffs
(rows added/removed, columns changed, dtype mutations, null-count shifts)
and builds a lineage graph that shows the transformation history of every
variable.

Usage::

    tracker = LineageTracker()

    # Before executing a cell
    tracker.snapshot_before(cell_id, namespace)

    # ... execute the cell ...

    # After executing a cell
    entries = tracker.snapshot_after(cell_id, namespace)

    # Query lineage
    history = tracker.get_lineage("df")
    graph   = tracker.get_lineage_graph()
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DataSnapshot:
    """Point-in-time snapshot of a DataFrame's structure and content digest."""

    var_name: str
    cell_id: str
    shape: tuple[int, ...]
    columns: list[str]
    dtypes: dict[str, str]
    null_counts: dict[str, int]
    memory_bytes: int
    content_hash: str  # MD5 hex-digest of first 100 rows as CSV
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "var_name": self.var_name,
            "cell_id": self.cell_id,
            "shape": list(self.shape),
            "columns": self.columns,
            "dtypes": self.dtypes,
            "null_counts": self.null_counts,
            "memory_bytes": self.memory_bytes,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class LineageDiff:
    """Structural diff between two consecutive DataFrame snapshots."""

    var_name: str
    cell_id: str
    rows_added: int
    rows_removed: int
    columns_added: list[str]
    columns_removed: list[str]
    columns_retyped: dict[str, tuple[str, str]]  # col -> (old_dtype, new_dtype)
    nulls_changed: dict[str, tuple[int, int]]    # col -> (old_count, new_count)
    content_changed: bool

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "var_name": self.var_name,
            "cell_id": self.cell_id,
            "rows_added": self.rows_added,
            "rows_removed": self.rows_removed,
            "columns_added": self.columns_added,
            "columns_removed": self.columns_removed,
            "columns_retyped": {
                col: {"from": old, "to": new}
                for col, (old, new) in self.columns_retyped.items()
            },
            "nulls_changed": {
                col: {"from": old, "to": new}
                for col, (old, new) in self.nulls_changed.items()
            },
            "content_changed": self.content_changed,
        }


@dataclass
class LineageEntry:
    """A single entry in a variable's lineage history."""

    cell_id: str
    snapshot: DataSnapshot
    diff: LineageDiff | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "cell_id": self.cell_id,
            "snapshot": self.snapshot.to_dict(),
            "diff": self.diff.to_dict() if self.diff else None,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _is_dataframe(obj: Any) -> bool:
    """Check whether *obj* is a pandas DataFrame without importing pandas.

    Uses duck-typing on the class name and module to avoid importing pandas
    at module level, which keeps the module lightweight when pandas is not
    installed.
    """
    obj_type = type(obj)
    if obj_type.__name__ != "DataFrame":
        return False
    module = getattr(obj_type, "__module__", "") or ""
    return module.startswith("pandas")


def _capture_snapshot(var_name: str, cell_id: str, df: Any) -> DataSnapshot:
    """Capture a structural snapshot of a pandas DataFrame.

    Args:
        var_name: The variable name in the user's namespace.
        cell_id:  The notebook cell that owns this snapshot.
        df:       A pandas ``DataFrame`` instance.

    Returns:
        A fully-populated :class:`DataSnapshot`.
    """
    try:
        shape: tuple[int, ...] = tuple(df.shape)
    except Exception:
        shape = (0, 0)

    try:
        columns: list[str] = list(df.columns)
    except Exception:
        columns = []

    try:
        dtypes: dict[str, str] = {
            str(col): str(dtype) for col, dtype in df.dtypes.items()
        }
    except Exception:
        dtypes = {}

    try:
        null_counts: dict[str, int] = {
            str(col): int(count) for col, count in df.isnull().sum().items()
        }
    except Exception:
        null_counts = {}

    try:
        memory_bytes: int = int(df.memory_usage(deep=True).sum())
    except Exception:
        memory_bytes = 0

    try:
        csv_bytes = df.head(100).to_csv(index=False).encode("utf-8")
        content_hash = hashlib.md5(csv_bytes).hexdigest()  # noqa: S324
    except Exception:
        content_hash = ""

    return DataSnapshot(
        var_name=var_name,
        cell_id=cell_id,
        shape=shape,
        columns=columns,
        dtypes=dtypes,
        null_counts=null_counts,
        memory_bytes=memory_bytes,
        content_hash=content_hash,
    )


def _compute_diff(
    var_name: str,
    cell_id: str,
    before: DataSnapshot,
    after: DataSnapshot,
) -> LineageDiff:
    """Compute the structural diff between two :class:`DataSnapshot` instances.

    Args:
        var_name: The variable being compared.
        cell_id:  The cell that caused the transformation.
        before:   Snapshot captured **before** cell execution.
        after:    Snapshot captured **after** cell execution.

    Returns:
        A :class:`LineageDiff` describing what changed.
    """
    # --- Row changes ---
    rows_before = before.shape[0] if len(before.shape) > 0 else 0
    rows_after = after.shape[0] if len(after.shape) > 0 else 0
    rows_added = max(0, rows_after - rows_before)
    rows_removed = max(0, rows_before - rows_after)

    # --- Column changes ---
    before_cols = set(before.columns)
    after_cols = set(after.columns)
    columns_added = sorted(after_cols - before_cols)
    columns_removed = sorted(before_cols - after_cols)

    # --- Dtype changes (only for columns present in both) ---
    common_cols = before_cols & after_cols
    columns_retyped: dict[str, tuple[str, str]] = {}
    for col in sorted(common_cols):
        old_dtype = before.dtypes.get(col, "")
        new_dtype = after.dtypes.get(col, "")
        if old_dtype != new_dtype:
            columns_retyped[col] = (old_dtype, new_dtype)

    # --- Null-count changes ---
    nulls_changed: dict[str, tuple[int, int]] = {}
    for col in sorted(common_cols):
        old_nulls = before.null_counts.get(col, 0)
        new_nulls = after.null_counts.get(col, 0)
        if old_nulls != new_nulls:
            nulls_changed[col] = (old_nulls, new_nulls)

    # --- Content hash comparison ---
    content_changed = before.content_hash != after.content_hash

    return LineageDiff(
        var_name=var_name,
        cell_id=cell_id,
        rows_added=rows_added,
        rows_removed=rows_removed,
        columns_added=columns_added,
        columns_removed=columns_removed,
        columns_retyped=columns_retyped,
        nulls_changed=nulls_changed,
        content_changed=content_changed,
    )


# ---------------------------------------------------------------------------
# Lineage tracker
# ---------------------------------------------------------------------------


class LineageTracker:
    """Track DataFrame transformations across notebook cell executions.

    The typical workflow wraps every cell execution:

    1. Call :meth:`snapshot_before` to record the state of all DataFrames.
    2. Execute the cell.
    3. Call :meth:`snapshot_after` to capture the new state and compute diffs.

    The accumulated history is queryable per variable or as a complete graph.
    """

    def __init__(self) -> None:
        self._lineage: dict[str, list[LineageEntry]] = {}
        self._pending_snapshots: dict[str, dict[str, DataSnapshot]] = {}

    # -- Snapshot lifecycle --------------------------------------------------

    def snapshot_before(self, cell_id: str, namespace: dict[str, Any]) -> None:
        """Capture snapshots of all DataFrames before a cell executes.

        Args:
            cell_id:   Unique identifier of the cell about to run.
            namespace: The execution namespace (``locals()`` / ``globals()``).
        """
        snapshots: dict[str, DataSnapshot] = {}
        for name, obj in namespace.items():
            if name.startswith("_"):
                continue
            try:
                if _is_dataframe(obj):
                    snapshots[name] = _capture_snapshot(name, cell_id, obj)
            except Exception:  # noqa: BLE001
                logger.debug("Failed to snapshot '%s' before cell %s", name, cell_id)
        self._pending_snapshots[cell_id] = snapshots
        logger.debug(
            "Captured %d before-snapshots for cell %s",
            len(snapshots),
            cell_id,
        )

    def snapshot_after(
        self,
        cell_id: str,
        namespace: dict[str, Any],
    ) -> list[LineageEntry]:
        """Capture snapshots after cell execution and compute diffs.

        Args:
            cell_id:   Unique identifier of the cell that just ran.
            namespace: The execution namespace after cell execution.

        Returns:
            A list of :class:`LineageEntry` instances created for this cell.
        """
        before_snapshots = self._pending_snapshots.pop(cell_id, {})
        entries: list[LineageEntry] = []

        for name, obj in namespace.items():
            if name.startswith("_"):
                continue
            try:
                if not _is_dataframe(obj):
                    continue
            except Exception:  # noqa: BLE001
                continue

            try:
                after_snap = _capture_snapshot(name, cell_id, obj)
            except Exception:  # noqa: BLE001
                logger.debug("Failed to snapshot '%s' after cell %s", name, cell_id)
                continue

            diff: LineageDiff | None = None
            if name in before_snapshots:
                try:
                    diff = _compute_diff(
                        name, cell_id, before_snapshots[name], after_snap
                    )
                except Exception:  # noqa: BLE001
                    logger.debug(
                        "Failed to compute diff for '%s' in cell %s", name, cell_id
                    )

            entry = LineageEntry(cell_id=cell_id, snapshot=after_snap, diff=diff)
            self._lineage.setdefault(name, []).append(entry)
            entries.append(entry)

        logger.debug(
            "Recorded %d lineage entries for cell %s", len(entries), cell_id
        )
        return entries

    # -- Query API -----------------------------------------------------------

    def get_lineage(self, var_name: str) -> list[LineageEntry]:
        """Return the full transformation history of a single variable.

        Args:
            var_name: The DataFrame variable name.

        Returns:
            Chronologically-ordered list of :class:`LineageEntry`.
        """
        return list(self._lineage.get(var_name, []))

    def get_all_lineage(self) -> dict[str, list[LineageEntry]]:
        """Return the lineage history for every tracked variable.

        Returns:
            Mapping of variable name → list of :class:`LineageEntry`.
        """
        return {k: list(v) for k, v in self._lineage.items()}

    def get_lineage_graph(self) -> dict[str, Any]:
        """Build a graph representation of the complete lineage.

        The returned dict has two keys:

        * ``nodes`` – list of dicts, each describing a snapshot (variable name,
          cell_id, shape, timestamp, content_hash).
        * ``edges`` – list of dicts, each describing a transformation between
          two consecutive snapshots of the same variable (cell_id, diff
          summary).

        Returns:
            A graph-like dict suitable for visualisation or serialisation.
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for var_name, entries in self._lineage.items():
            for idx, entry in enumerate(entries):
                node_id = f"{var_name}@{entry.cell_id}#{idx}"
                nodes.append(
                    {
                        "id": node_id,
                        "var_name": var_name,
                        "cell_id": entry.cell_id,
                        "shape": entry.snapshot.shape,
                        "timestamp": entry.snapshot.timestamp,
                        "content_hash": entry.snapshot.content_hash,
                        "memory_bytes": entry.snapshot.memory_bytes,
                    }
                )

                if idx > 0 and entry.diff is not None:
                    prev_id = f"{var_name}@{entries[idx - 1].cell_id}#{idx - 1}"
                    edges.append(
                        {
                            "source": prev_id,
                            "target": node_id,
                            "cell_id": entry.cell_id,
                            "rows_added": entry.diff.rows_added,
                            "rows_removed": entry.diff.rows_removed,
                            "columns_added": entry.diff.columns_added,
                            "columns_removed": entry.diff.columns_removed,
                            "columns_retyped": {
                                col: {"from": old, "to": new}
                                for col, (old, new) in entry.diff.columns_retyped.items()
                            },
                            "content_changed": entry.diff.content_changed,
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    # -- Lifecycle -----------------------------------------------------------

    def clear(self) -> None:
        """Remove all recorded lineage data and pending snapshots."""
        self._lineage.clear()
        self._pending_snapshots.clear()
        logger.info("Lineage tracker cleared")
