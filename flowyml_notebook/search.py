"""Notebook Search Engine — full-text search across notebook cells.

Provides powerful search capabilities including:
- Exact, fuzzy (Levenshtein), and regex matching
- Search in cell source *and* outputs
- Search and replace with preview
- Variable / function definition discovery
- Duplicate / near-duplicate cell detection
- Rich HTML output with highlighted matches
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from typing import Any

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single search match inside a notebook cell."""

    cell_id: str
    cell_index: int
    cell_type: str
    line_number: int
    match_text: str
    context: str  # surrounding lines for preview
    score: float  # relevance 0-1
    match_type: str  # "exact", "fuzzy", "regex"

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "cell_index": self.cell_index,
            "cell_type": self.cell_type,
            "line_number": self.line_number,
            "match_text": self.match_text,
            "context": self.context,
            "score": round(self.score, 4),
            "match_type": self.match_type,
        }


# ---------------------------------------------------------------------------
# Helpers — pure-Python Levenshtein distance (no external deps)
# ---------------------------------------------------------------------------


def _edit_distance(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between *a* and *b*."""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la

    # Optimised single-row DP
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def _fuzzy_score(query: str, candidate: str, *, threshold: float = 0.6) -> float:
    """Return a similarity score in [0, 1] between *query* and *candidate*.

    Returns 0.0 when the score falls below *threshold* (fast reject).
    """
    if query == candidate:
        return 1.0
    max_len = max(len(query), len(candidate))
    if max_len == 0:
        return 1.0
    dist = _edit_distance(query, candidate)
    score = 1.0 - dist / max_len
    return score if score >= threshold else 0.0


def _context_lines(lines: list[str], idx: int, radius: int = 2) -> str:
    """Return a snippet of *lines* centred on *idx* (0-based)."""
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# Search engine
# ---------------------------------------------------------------------------


class NotebookSearch:
    """Full-text search engine for FlowyML notebook cells."""

    # -- public API ---------------------------------------------------------

    def search(
        self,
        cells: list[Any],
        query: str,
        *,
        case_sensitive: bool = False,
        regex: bool = False,
        search_outputs: bool = False,
        cell_type: str | None = None,
        max_results: int = 50,
        fuzzy_threshold: float = 0.6,
    ) -> list[SearchResult]:
        """Search across notebook cells for *query*.

        Args:
            cells: List of Cell objects (from ``notebook.cells``).
            query: The search string (plain text or regex pattern).
            case_sensitive: Perform case-sensitive matching.
            regex: Treat *query* as a regular expression.
            search_outputs: Also search cell outputs.
            cell_type: Restrict to a cell type (``"code"``, ``"markdown"``, …).
            max_results: Cap on returned results.
            fuzzy_threshold: Minimum fuzzy-match score (0–1).

        Returns:
            Sorted list of :class:`SearchResult` (best matches first).
        """
        if not query:
            return []

        results: list[SearchResult] = []

        for idx, cell in enumerate(cells):
            ct = cell.cell_type.value if hasattr(cell.cell_type, "value") else str(cell.cell_type)
            if cell_type and ct != cell_type:
                continue

            # Search source lines
            source = cell.source or ""
            results.extend(
                self._search_text(
                    source,
                    query,
                    cell.id,
                    idx,
                    ct,
                    case_sensitive=case_sensitive,
                    regex=regex,
                    fuzzy_threshold=fuzzy_threshold,
                )
            )

            # Optionally search outputs
            if search_outputs:
                for output in getattr(cell, "outputs", []):
                    out_text = self._output_to_text(output)
                    if out_text:
                        results.extend(
                            self._search_text(
                                out_text,
                                query,
                                cell.id,
                                idx,
                                ct,
                                case_sensitive=case_sensitive,
                                regex=regex,
                                fuzzy_threshold=fuzzy_threshold,
                            )
                        )

        # Sort by score descending, then by cell index
        results.sort(key=lambda r: (-r.score, r.cell_index, r.line_number))
        return results[:max_results]

    def search_and_replace(
        self,
        cells: list[Any],
        query: str,
        replacement: str,
        *,
        case_sensitive: bool = False,
        regex: bool = False,
    ) -> list[dict]:
        """Find & replace *query* → *replacement* in cell sources (in-place).

        Returns a list of change dicts:
        ``{cell_id, old_text, new_text, line}``
        """
        if not query:
            return []

        changes: list[dict] = []
        flags = 0 if case_sensitive else re.IGNORECASE

        for cell in cells:
            source = cell.source or ""
            lines = source.split("\n")
            new_lines: list[str] = []
            cell_changed = False

            for lineno, line in enumerate(lines, 1):
                if regex:
                    try:
                        new_line = re.sub(query, replacement, line, flags=flags)
                    except re.error:
                        new_line = line
                else:
                    if case_sensitive:
                        new_line = line.replace(query, replacement)
                    else:
                        # Case-insensitive literal replace
                        new_line = re.sub(re.escape(query), replacement, line, flags=flags)

                if new_line != line:
                    changes.append(
                        {
                            "cell_id": cell.id,
                            "old_text": line,
                            "new_text": new_line,
                            "line": lineno,
                        }
                    )
                    cell_changed = True

                new_lines.append(new_line)

            if cell_changed:
                cell.source = "\n".join(new_lines)

        return changes

    def find_all_variables(self, cells: list[Any]) -> dict[str, list[str]]:
        """Map variable names → list of cell IDs where they are assigned."""
        var_map: dict[str, list[str]] = {}

        for cell in cells:
            ct = cell.cell_type.value if hasattr(cell.cell_type, "value") else str(cell.cell_type)
            if ct != "code":
                continue

            try:
                tree = ast.parse(cell.source or "")
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        names.extend(self._extract_names(target))
                elif isinstance(node, ast.AnnAssign) and node.target:
                    names.extend(self._extract_names(node.target))
                elif isinstance(node, ast.AugAssign):
                    names.extend(self._extract_names(node.target))
                elif isinstance(node, (ast.For, ast.AsyncFor)):
                    names.extend(self._extract_names(node.target))
                elif isinstance(node, ast.With):
                    for item in node.items:
                        if item.optional_vars:
                            names.extend(self._extract_names(item.optional_vars))

                for name in names:
                    var_map.setdefault(name, [])
                    if cell.id not in var_map[name]:
                        var_map[name].append(cell.id)

        return var_map

    def find_all_functions(self, cells: list[Any]) -> dict[str, list[str]]:
        """Map function/class names → list of cell IDs where they are defined."""
        func_map: dict[str, list[str]] = {}

        for cell in cells:
            ct = cell.cell_type.value if hasattr(cell.cell_type, "value") else str(cell.cell_type)
            if ct != "code":
                continue

            try:
                tree = ast.parse(cell.source or "")
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                name: str | None = None
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = node.name
                elif isinstance(node, ast.ClassDef):
                    name = node.name

                if name:
                    func_map.setdefault(name, [])
                    if cell.id not in func_map[name]:
                        func_map[name].append(cell.id)

        return func_map

    def find_duplicates(self, cells: list[Any], *, threshold: float = 0.85) -> list[dict]:
        """Find cells with similar or identical source code.

        Returns a list of dicts:
        ``{cell_ids: [...], similarity: float, snippet: str}``
        """
        code_cells: list[tuple[int, Any]] = []
        for idx, cell in enumerate(cells):
            ct = cell.cell_type.value if hasattr(cell.cell_type, "value") else str(cell.cell_type)
            if ct == "code" and (cell.source or "").strip():
                code_cells.append((idx, cell))

        duplicates: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i in range(len(code_cells)):
            for j in range(i + 1, len(code_cells)):
                idx_a, cell_a = code_cells[i]
                idx_b, cell_b = code_cells[j]

                pair_key = (cell_a.id, cell_b.id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                src_a = self._normalise(cell_a.source)
                src_b = self._normalise(cell_b.source)

                # Fast identical check
                if src_a == src_b:
                    similarity = 1.0
                else:
                    # For long cells, compare line sets first (cheap heuristic)
                    if max(len(src_a), len(src_b)) > 500:
                        similarity = self._jaccard_lines(src_a, src_b)
                    else:
                        similarity = _fuzzy_score(src_a, src_b, threshold=threshold)

                if similarity >= threshold:
                    snippet = (cell_a.source or "")[:120]
                    duplicates.append(
                        {
                            "cell_ids": [cell_a.id, cell_b.id],
                            "cell_indices": [idx_a, idx_b],
                            "similarity": round(similarity, 4),
                            "snippet": snippet,
                        }
                    )

        duplicates.sort(key=lambda d: -d["similarity"])
        return duplicates

    # -- private helpers ----------------------------------------------------

    def _search_text(
        self,
        text: str,
        query: str,
        cell_id: str,
        cell_index: int,
        cell_type: str,
        *,
        case_sensitive: bool,
        regex: bool,
        fuzzy_threshold: float,
    ) -> list[SearchResult]:
        """Search *text* for *query*, returning matches."""
        results: list[SearchResult] = []
        lines = text.split("\n")
        flags = 0 if case_sensitive else re.IGNORECASE

        for lineno_0, line in enumerate(lines):
            lineno = lineno_0 + 1
            ctx = _context_lines(lines, lineno_0)

            if regex:
                try:
                    for m in re.finditer(query, line, flags):
                        results.append(
                            SearchResult(
                                cell_id=cell_id,
                                cell_index=cell_index,
                                cell_type=cell_type,
                                line_number=lineno,
                                match_text=m.group(),
                                context=ctx,
                                score=1.0,
                                match_type="regex",
                            )
                        )
                except re.error:
                    pass  # invalid regex — skip silently
            else:
                # Exact match
                cmp_line = line if case_sensitive else line.lower()
                cmp_query = query if case_sensitive else query.lower()

                if cmp_query in cmp_line:
                    results.append(
                        SearchResult(
                            cell_id=cell_id,
                            cell_index=cell_index,
                            cell_type=cell_type,
                            line_number=lineno,
                            match_text=query,
                            context=ctx,
                            score=1.0,
                            match_type="exact",
                        )
                    )
                else:
                    # Token-level fuzzy matching (compare against each word)
                    words = re.findall(r"\w+", line)
                    for word in words:
                        cmp_word = word if case_sensitive else word.lower()
                        score = _fuzzy_score(cmp_query, cmp_word, threshold=fuzzy_threshold)
                        if score > 0:
                            results.append(
                                SearchResult(
                                    cell_id=cell_id,
                                    cell_index=cell_index,
                                    cell_type=cell_type,
                                    line_number=lineno,
                                    match_text=word,
                                    context=ctx,
                                    score=score,
                                    match_type="fuzzy",
                                )
                            )
                            break  # one fuzzy match per line is enough

        return results

    @staticmethod
    def _output_to_text(output: Any) -> str:
        """Extract plain text from a CellOutput (or dict)."""
        if isinstance(output, dict):
            return str(output.get("data", ""))
        data = getattr(output, "data", None)
        if data is None:
            return ""
        return str(data)

    @staticmethod
    def _extract_names(node: ast.AST) -> list[str]:
        """Recursively extract variable names from an assignment target node."""
        names: list[str] = []
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                names.extend(NotebookSearch._extract_names(elt))
        elif isinstance(node, ast.Starred):
            names.extend(NotebookSearch._extract_names(node.value))
        return names

    @staticmethod
    def _normalise(source: str) -> str:
        """Normalise source for duplicate comparison (strip comments, whitespace)."""
        lines = (source or "").strip().split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                cleaned.append(stripped)
        return "\n".join(cleaned)

    @staticmethod
    def _jaccard_lines(a: str, b: str) -> float:
        """Jaccard similarity on the set of normalised lines."""
        set_a = set(a.split("\n"))
        set_b = set(b.split("\n"))
        if not set_a and not set_b:
            return 1.0
        inter = set_a & set_b
        union = set_a | set_b
        return len(inter) / len(union) if union else 1.0


# ---------------------------------------------------------------------------
# Rich HTML output formatter
# ---------------------------------------------------------------------------


def format_search_output(results: list[SearchResult]) -> CellOutput:
    """Format a list of search results as a rich HTML ``CellOutput``."""
    if not results:
        return CellOutput(
            output_type="html",
            data="<p style='color:#94a3b8;'>No results found.</p>",
        )

    rows: list[str] = []
    for r in results:
        # Highlight matched text in context
        escaped_ctx = _html_escape(r.context)
        escaped_match = _html_escape(r.match_text)
        if escaped_match:
            highlighted = escaped_ctx.replace(
                escaped_match,
                f"<mark style='background:#fbbf24;color:#000;border-radius:2px;"
                f"padding:0 2px;'>{escaped_match}</mark>",
                1,
            )
        else:
            highlighted = escaped_ctx

        badge_colors = {
            "exact": "#22c55e",
            "fuzzy": "#f59e0b",
            "regex": "#8b5cf6",
        }
        badge_color = badge_colors.get(r.match_type, "#64748b")

        rows.append(
            f"<tr>"
            f"<td style='padding:6px 10px;white-space:nowrap;'>"
            f"<span style='background:{badge_color};color:#fff;padding:2px 6px;"
            f"border-radius:4px;font-size:0.75rem;'>{r.match_type}</span></td>"
            f"<td style='padding:6px 10px;font-family:monospace;font-size:0.85rem;'>"
            f"Cell {r.cell_index} <span style='color:#64748b;'>({r.cell_type})</span>"
            f" L{r.line_number}</td>"
            f"<td style='padding:6px 10px;'>"
            f"<pre style='margin:0;font-size:0.82rem;white-space:pre-wrap;'>"
            f"{highlighted}</pre></td>"
            f"<td style='padding:6px 10px;text-align:center;'>{r.score:.0%}</td>"
            f"</tr>"
        )

    html = (
        f"<div style='font-family:system-ui;'>"
        f"<p style='margin:0 0 8px;color:#94a3b8;'>"
        f"Found <strong style='color:#e2e8f0;'>{len(results)}</strong> match(es)</p>"
        f"<table style='border-collapse:collapse;width:100%;font-size:0.9rem;'>"
        f"<thead><tr style='border-bottom:1px solid #334155;color:#94a3b8;'>"
        f"<th style='padding:6px 10px;text-align:left;'>Type</th>"
        f"<th style='padding:6px 10px;text-align:left;'>Location</th>"
        f"<th style='padding:6px 10px;text-align:left;'>Context</th>"
        f"<th style='padding:6px 10px;text-align:center;'>Score</th>"
        f"</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )

    return CellOutput(output_type="html", data=html)


def _html_escape(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
