"""Notebook diff tool for comparing FlowyML notebook files.

Provides structural comparison of two notebooks, detecting added, removed,
modified, moved, and unchanged cells. Renders diffs in both terminal (ANSI)
and HTML formats.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from html import escape as html_escape
from typing import Any

from flowyml_notebook.cells import CellType, NotebookFile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CellDiff:
    """Represents the diff result for a single cell between two notebooks.

    Attributes:
        status: One of ``'added'``, ``'removed'``, ``'modified'``,
            ``'unchanged'``, or ``'moved'``.
        cell_id: The unique identifier of the cell.
        cell_type: Human-readable cell type (e.g. ``'CODE'``).
        name: Display name of the cell.
        source_a: Source code from notebook A (empty string if the cell was
            added in notebook B).
        source_b: Source code from notebook B (empty string if the cell was
            removed from notebook A).
        unified_diff: Output of :func:`difflib.unified_diff` for modified
            cells, empty string otherwise.
        index_a: Position (0-based) of the cell in notebook A, or ``None``
            if the cell does not exist there.
        index_b: Position (0-based) of the cell in notebook B, or ``None``
            if the cell does not exist there.
    """

    status: str
    cell_id: str
    cell_type: str
    name: str
    source_a: str = ""
    source_b: str = ""
    unified_diff: str = ""
    index_a: int | None = None
    index_b: int | None = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "status": self.status,
            "cell_id": self.cell_id,
            "cell_type": self.cell_type,
            "name": self.name,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "unified_diff": self.unified_diff,
            "index_a": self.index_a,
            "index_b": self.index_b,
        }


@dataclass
class NotebookDiff:
    """Aggregated diff between two notebooks.

    Attributes:
        cells: Ordered list of per-cell diff results.
        metadata_changes: Mapping of changed metadata field names to
            ``(old_value, new_value)`` tuples.
        summary: Counts keyed by status (``added``, ``removed``,
            ``modified``, ``unchanged``, ``moved``).
    """

    cells: list[CellDiff] = field(default_factory=list)
    metadata_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    summary: dict[str, int] = field(default_factory=lambda: {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 0,
        "moved": 0,
    })

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "cells": [c.to_dict() for c in self.cells],
            "metadata_changes": {
                k: list(v) for k, v in self.metadata_changes.items()
            },
            "summary": dict(self.summary),
        }


# ---------------------------------------------------------------------------
# Core diff logic
# ---------------------------------------------------------------------------


def _compute_unified_diff(source_a: str, source_b: str, label: str) -> str:
    """Return a unified-diff string between *source_a* and *source_b*.

    Args:
        source_a: Original source text.
        source_b: Modified source text.
        label: Label used in the diff header lines.

    Returns:
        A string containing the unified diff output, or an empty string if
        the sources are identical.
    """
    lines_a = source_a.splitlines(keepends=True)
    lines_b = source_b.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
    )
    return "".join(diff_lines)


def diff_notebooks(nb_a: NotebookFile, nb_b: NotebookFile) -> NotebookDiff:
    """Compare two notebooks and return a structured diff.

    The algorithm indexes cells by their unique *id*. It walks through
    notebook A to find removed, modified, moved, or unchanged cells, then
    walks through notebook B to find newly added cells.

    Args:
        nb_a: The *base* (original) notebook.
        nb_b: The *target* (modified) notebook.

    Returns:
        A :class:`NotebookDiff` capturing all differences.

    Raises:
        TypeError: If either argument is not a :class:`NotebookFile`.
    """
    if not isinstance(nb_a, NotebookFile):
        raise TypeError(f"nb_a must be a NotebookFile, got {type(nb_a).__name__}")
    if not isinstance(nb_b, NotebookFile):
        raise TypeError(f"nb_b must be a NotebookFile, got {type(nb_b).__name__}")

    logger.debug("Diffing notebooks: %s vs %s", nb_a.metadata.name, nb_b.metadata.name)

    # -- Metadata comparison ------------------------------------------------
    meta_a = nb_a.metadata.to_dict()
    meta_b = nb_b.metadata.to_dict()
    metadata_changes: dict[str, tuple[Any, Any]] = {}
    all_keys = set(meta_a) | set(meta_b)
    for key in sorted(all_keys):
        val_a = meta_a.get(key)
        val_b = meta_b.get(key)
        if val_a != val_b:
            metadata_changes[key] = (val_a, val_b)

    # -- Build cell lookups -------------------------------------------------
    cells_a_by_id: dict[str, tuple[int, Any]] = {
        cell.id: (idx, cell) for idx, cell in enumerate(nb_a.cells)
    }
    cells_b_by_id: dict[str, tuple[int, Any]] = {
        cell.id: (idx, cell) for idx, cell in enumerate(nb_b.cells)
    }

    cell_diffs: list[CellDiff] = []
    visited_ids: set[str] = set()

    # -- Walk notebook A ----------------------------------------------------
    for idx_a, cell_a in enumerate(nb_a.cells):
        cid = cell_a.id
        visited_ids.add(cid)

        if cid not in cells_b_by_id:
            # Removed
            cell_diffs.append(CellDiff(
                status="removed",
                cell_id=cid,
                cell_type=cell_a.cell_type.name if isinstance(cell_a.cell_type, CellType) else str(cell_a.cell_type),
                name=cell_a.name,
                source_a=cell_a.source,
                source_b="",
                unified_diff="",
                index_a=idx_a,
                index_b=None,
            ))
            logger.debug("Cell %s (%s) removed", cid, cell_a.name)
        else:
            idx_b, cell_b = cells_b_by_id[cid]
            cell_type_str = cell_a.cell_type.name if isinstance(cell_a.cell_type, CellType) else str(cell_a.cell_type)

            if cell_a.source == cell_b.source:
                # Content identical – check position
                if idx_a != idx_b:
                    status = "moved"
                    logger.debug("Cell %s (%s) moved %d -> %d", cid, cell_a.name, idx_a, idx_b)
                else:
                    status = "unchanged"

                cell_diffs.append(CellDiff(
                    status=status,
                    cell_id=cid,
                    cell_type=cell_type_str,
                    name=cell_a.name,
                    source_a=cell_a.source,
                    source_b=cell_b.source,
                    unified_diff="",
                    index_a=idx_a,
                    index_b=idx_b,
                ))
            else:
                # Modified
                udiff = _compute_unified_diff(cell_a.source, cell_b.source, cell_a.name or cid)
                cell_diffs.append(CellDiff(
                    status="modified",
                    cell_id=cid,
                    cell_type=cell_type_str,
                    name=cell_a.name,
                    source_a=cell_a.source,
                    source_b=cell_b.source,
                    unified_diff=udiff,
                    index_a=idx_a,
                    index_b=idx_b,
                ))
                logger.debug("Cell %s (%s) modified", cid, cell_a.name)

    # -- Walk notebook B for additions --------------------------------------
    for idx_b, cell_b in enumerate(nb_b.cells):
        cid = cell_b.id
        if cid in visited_ids:
            continue
        cell_diffs.append(CellDiff(
            status="added",
            cell_id=cid,
            cell_type=cell_b.cell_type.name if isinstance(cell_b.cell_type, CellType) else str(cell_b.cell_type),
            name=cell_b.name,
            source_a="",
            source_b=cell_b.source,
            unified_diff="",
            index_a=None,
            index_b=idx_b,
        ))
        logger.debug("Cell %s (%s) added", cid, cell_b.name)

    # -- Sort by position (prefer nb_b order, removed cells use nb_a) -------
    def _sort_key(cd: CellDiff) -> tuple[int, int]:
        if cd.index_b is not None:
            return (cd.index_b, 0)
        if cd.index_a is not None:
            return (cd.index_a, 1)
        return (999_999, 0)  # pragma: no cover – defensive fallback

    cell_diffs.sort(key=_sort_key)

    # -- Build summary ------------------------------------------------------
    summary: dict[str, int] = {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 0,
        "moved": 0,
    }
    for cd in cell_diffs:
        summary[cd.status] = summary.get(cd.status, 0) + 1

    logger.info(
        "Diff complete – added=%d removed=%d modified=%d unchanged=%d moved=%d",
        summary["added"],
        summary["removed"],
        summary["modified"],
        summary["unchanged"],
        summary["moved"],
    )

    return NotebookDiff(
        cells=cell_diffs,
        metadata_changes=metadata_changes,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Terminal (ANSI) renderer
# ---------------------------------------------------------------------------

# ANSI colour codes
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

_STATUS_COLORS: dict[str, str] = {
    "added": _GREEN,
    "removed": _RED,
    "modified": _YELLOW,
    "moved": _CYAN,
    "unchanged": "",
}


def render_diff_terminal(diff: NotebookDiff) -> str:
    """Render a notebook diff as an ANSI-coloured terminal string.

    Args:
        diff: The :class:`NotebookDiff` to render.

    Returns:
        A human-readable string with embedded ANSI escape codes suitable
        for printing to a terminal.

    Raises:
        TypeError: If *diff* is not a :class:`NotebookDiff`.
    """
    if not isinstance(diff, NotebookDiff):
        raise TypeError(f"Expected NotebookDiff, got {type(diff).__name__}")

    lines: list[str] = []

    # Header
    lines.append(f"{'═' * 60}")
    lines.append("  Notebook Diff Summary")
    lines.append(f"{'═' * 60}")

    s = diff.summary
    lines.append(
        f"  {_GREEN}+{s['added']} added{_RESET}  "
        f"{_RED}-{s['removed']} removed{_RESET}  "
        f"{_YELLOW}~{s['modified']} modified{_RESET}  "
        f"{_CYAN}↔{s['moved']} moved{_RESET}  "
        f"={s['unchanged']} unchanged"
    )
    lines.append("")

    # Metadata changes
    if diff.metadata_changes:
        lines.append(f"{_YELLOW}Metadata changes:{_RESET}")
        for field_name, (old, new) in diff.metadata_changes.items():
            lines.append(f"  {field_name}: {old!r} → {new!r}")
        lines.append("")

    # Cell diffs
    for cd in diff.cells:
        color = _STATUS_COLORS.get(cd.status, "")
        badge = f"[{cd.status.upper()}]"
        pos_info = ""
        if cd.status == "moved" and cd.index_a is not None and cd.index_b is not None:
            pos_info = f" (pos {cd.index_a} → {cd.index_b})"

        lines.append(
            f"{color}{badge}{_RESET} {cd.cell_type} | {cd.name or cd.cell_id}{pos_info}"
        )

        if cd.status == "modified" and cd.unified_diff:
            for diff_line in cd.unified_diff.splitlines():
                if diff_line.startswith("+"):
                    lines.append(f"  {_GREEN}{diff_line}{_RESET}")
                elif diff_line.startswith("-"):
                    lines.append(f"  {_RED}{diff_line}{_RESET}")
                else:
                    lines.append(f"  {diff_line}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

_HTML_STATUS_COLORS: dict[str, str] = {
    "added": "#22c55e",
    "removed": "#ef4444",
    "modified": "#f59e0b",
    "moved": "#06b6d4",
    "unchanged": "#64748b",
}


def render_diff_html(diff: NotebookDiff) -> str:
    """Render a notebook diff as a standalone dark-themed HTML document.

    Args:
        diff: The :class:`NotebookDiff` to render.

    Returns:
        A complete HTML string that can be written to a file or served
        directly.

    Raises:
        TypeError: If *diff* is not a :class:`NotebookDiff`.
    """
    if not isinstance(diff, NotebookDiff):
        raise TypeError(f"Expected NotebookDiff, got {type(diff).__name__}")

    s = diff.summary

    # -- Build HTML parts ---------------------------------------------------
    meta_section = ""
    if diff.metadata_changes:
        meta_rows = []
        for field_name, (old, new) in diff.metadata_changes.items():
            meta_rows.append(
                f'<tr><td style="padding:6px 12px;color:#94a3b8;">{html_escape(str(field_name))}</td>'
                f'<td style="padding:6px 12px;color:#f87171;">{html_escape(repr(old))}</td>'
                f'<td style="padding:6px 12px;color:#4ade80;">{html_escape(repr(new))}</td></tr>'
            )
        meta_section = (
            '<div style="margin-bottom:24px;">'
            '<h2 style="color:#f59e0b;font-size:18px;margin-bottom:12px;">Metadata Changes</h2>'
            '<table style="border-collapse:collapse;width:100%;">'
            '<thead><tr>'
            '<th style="text-align:left;padding:6px 12px;color:#94a3b8;border-bottom:1px solid #334155;">Field</th>'
            '<th style="text-align:left;padding:6px 12px;color:#94a3b8;border-bottom:1px solid #334155;">Old</th>'
            '<th style="text-align:left;padding:6px 12px;color:#94a3b8;border-bottom:1px solid #334155;">New</th>'
            '</tr></thead><tbody>'
            + "\n".join(meta_rows)
            + '</tbody></table></div>'
        )

    cell_cards: list[str] = []
    for cd in diff.cells:
        color = _HTML_STATUS_COLORS.get(cd.status, "#64748b")

        badge = (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:4px;'
            f'background:{color};color:#fff;font-size:12px;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{html_escape(cd.status)}</span>'
        )

        cell_info = (
            f'<span style="color:#cbd5e1;margin-left:12px;">{html_escape(cd.cell_type)}</span>'
            f'<span style="color:#94a3b8;margin-left:8px;">|</span>'
            f'<span style="color:#e2e8f0;margin-left:8px;">{html_escape(cd.name or cd.cell_id)}</span>'
        )

        pos_info = ""
        if cd.status == "moved" and cd.index_a is not None and cd.index_b is not None:
            pos_info = (
                f'<span style="color:#06b6d4;margin-left:12px;font-size:13px;">'
                f'(pos {cd.index_a} → {cd.index_b})</span>'
            )

        diff_block = ""
        if cd.status == "modified" and cd.unified_diff:
            diff_lines: list[str] = []
            for dl in cd.unified_diff.splitlines():
                escaped = html_escape(dl)
                if dl.startswith("+++") or dl.startswith("---"):
                    diff_lines.append(
                        f'<div style="color:#94a3b8;">{escaped}</div>'
                    )
                elif dl.startswith("@@"):
                    diff_lines.append(
                        f'<div style="color:#7c3aed;background:#1e1b4b;padding:2px 8px;'
                        f'margin:4px 0;border-radius:3px;">{escaped}</div>'
                    )
                elif dl.startswith("+"):
                    diff_lines.append(
                        f'<div style="background:rgba(34,197,94,0.15);color:#4ade80;'
                        f'padding:1px 8px;">{escaped}</div>'
                    )
                elif dl.startswith("-"):
                    diff_lines.append(
                        f'<div style="background:rgba(239,68,68,0.15);color:#f87171;'
                        f'padding:1px 8px;">{escaped}</div>'
                    )
                else:
                    diff_lines.append(
                        f'<div style="color:#cbd5e1;padding:1px 8px;">{escaped}</div>'
                    )
            diff_block = (
                '<div style="margin-top:12px;background:#020617;border-radius:6px;'
                'padding:12px;font-family:\'JetBrains Mono\',\'Fira Code\',monospace;'
                'font-size:13px;line-height:1.5;overflow-x:auto;">'
                + "\n".join(diff_lines)
                + '</div>'
            )

        card = (
            f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
            f'padding:16px;margin-bottom:12px;">'
            f'<div style="display:flex;align-items:center;flex-wrap:wrap;">'
            f'{badge}{cell_info}{pos_info}'
            f'</div>'
            f'{diff_block}'
            f'</div>'
        )
        cell_cards.append(card)

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Notebook Diff</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#0f172a;
    color:#e2e8f0;
    font-family:'Inter','Segoe UI',system-ui,sans-serif;
    padding:32px;
    line-height:1.6;
  }}
</style>
</head>
<body>
<div style="max-width:960px;margin:0 auto;">
  <h1 style="font-size:24px;margin-bottom:8px;">Notebook Diff</h1>
  <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;font-size:14px;">
    <span style="color:#22c55e;">+{s["added"]} added</span>
    <span style="color:#ef4444;">-{s["removed"]} removed</span>
    <span style="color:#f59e0b;">~{s["modified"]} modified</span>
    <span style="color:#06b6d4;">↔{s["moved"]} moved</span>
    <span style="color:#64748b;">={s["unchanged"]} unchanged</span>
  </div>
  {meta_section}
  <div>
    {"".join(cell_cards)}
  </div>
</div>
</body>
</html>"""

    return html
