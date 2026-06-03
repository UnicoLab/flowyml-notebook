"""Smart Cell Dependencies — automatic variable dependency analysis.

Parses Python cells with `ast` to detect which variables each cell defines
and which it consumes, then builds a full dependency graph with topological
ordering and stale-cell propagation.

This powers the "dependency map" view in the FlowyML Notebook GUI, letting
users see at a glance how cells relate and which cells need re-execution
after an upstream edit.
"""

from __future__ import annotations

import ast
import builtins
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)

# Names that are always available without user definition
_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins))


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CellDependency:
    """Analysis result for a single cell."""

    cell_id: str
    defines: list[str] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    functions_defined: list[str] = field(default_factory=list)
    classes_defined: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "defines": self.defines,
            "uses": self.uses,
            "imports": self.imports,
            "functions_defined": self.functions_defined,
            "classes_defined": self.classes_defined,
        }


@dataclass
class DependencyGraph:
    """Full notebook dependency graph."""

    cells: list[CellDependency] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)
    stale_cells: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cells": [c.to_dict() for c in self.cells],
            "edges": self.edges,
            "execution_order": self.execution_order,
            "stale_cells": self.stale_cells,
        }


# ---------------------------------------------------------------------------
# AST visitor — extracts defines / uses from a single cell
# ---------------------------------------------------------------------------

class _DepVisitor(ast.NodeVisitor):
    """Walk an AST and collect defined names, used names, imports, etc."""

    def __init__(self) -> None:
        self.defines: set[str] = set()
        self.uses: set[str] = set()
        self.imports: list[str] = []
        self.functions: list[str] = []
        self.classes: list[str] = []
        # Track locally scoped names that should NOT leak (comprehension vars)
        self._local_scopes: list[set[str]] = []

    # -- helpers ------------------------------------------------------------

    def _add_define(self, name: str) -> None:
        self.defines.add(name)

    def _add_use(self, name: str) -> None:
        # Ignore builtins and names defined in a local comprehension scope
        if name in _BUILTIN_NAMES:
            return
        for scope in reversed(self._local_scopes):
            if name in scope:
                return
        self.uses.add(name)

    def _collect_target_names(self, target: ast.AST, *, as_define: bool = True) -> None:
        """Recursively collect names from assignment targets / for-targets."""
        if isinstance(target, ast.Name):
            if as_define:
                self._add_define(target.id)
            else:
                self._add_use(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_target_names(elt, as_define=as_define)
        elif isinstance(target, ast.Starred):
            self._collect_target_names(target.value, as_define=as_define)
        elif isinstance(target, ast.Attribute):
            # e.g. self.x = ... — visit the value (self) as a use
            self.visit(target.value)
        elif isinstance(target, ast.Subscript):
            self.visit(target.value)
            self.visit(target.slice)

    # -- visitors -----------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        # Visit value side first (uses)
        self.visit(node.value)
        for target in node.targets:
            self._collect_target_names(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.visit(node.value)
        if node.target:
            self._collect_target_names(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        # Augmented assignment both uses and defines
        self._collect_target_names(node.target)
        # The target is also *used* (e.g. x += 1 reads x first)
        if isinstance(node.target, ast.Name):
            self._add_use(node.target.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add_define(node.name)
        self.functions.append(node.name)
        # Visit decorator list (they're executed at definition time)
        for dec in node.decorator_list:
            self.visit(dec)
        # Visit default argument values
        for default in node.args.defaults + node.args.kw_defaults:
            if default:
                self.visit(default)
        # Visit annotations
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation:
                self.visit(arg.annotation)
        if node.returns:
            self.visit(node.returns)
        # We intentionally do NOT recurse into the body — function body
        # names are local to the function and don't create cell-level deps.

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add_define(node.name)
        self.classes.append(node.name)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw.value)
        for dec in node.decorator_list:
            self.visit(dec)
        # Don't recurse into the class body — method names are not cell-level

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self._add_define(name)
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                self.imports.append(f"{module}.*")
                continue
            name = alias.asname or alias.name
            self._add_define(name)
            self.imports.append(f"{module}.{alias.name}")

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._add_use(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self._add_define(node.id)

    def visit_For(self, node: ast.For) -> None:
        # Visit the iterator first (uses)
        self.visit(node.iter)
        # Loop variable is a definition at cell level
        self._collect_target_names(node.target)
        for child in node.body + node.orelse:
            self.visit(child)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._collect_target_names(item.optional_vars)
        for child in node.body:
            self.visit(child)

    visit_AsyncWith = visit_With

    # --- Comprehensions: variables do NOT leak to cell scope ---------------

    def _visit_comprehension(self, node: ast.AST, generators: list[ast.comprehension]) -> None:
        scope: set[str] = set()
        self._local_scopes.append(scope)
        for gen in generators:
            # iter may reference outer names
            self.visit(gen.iter)
            # target is local
            self._collect_comp_target(gen.target, scope)
            for if_clause in gen.ifs:
                self.visit(if_clause)
        # Visit the element expression (or key/value for DictComp)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            self.visit(node.elt)
        self._local_scopes.pop()

    def _collect_comp_target(self, target: ast.AST, scope: set[str]) -> None:
        if isinstance(target, ast.Name):
            scope.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_comp_target(elt, scope)
        elif isinstance(target, ast.Starred):
            self._collect_comp_target(target.value, scope)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node, node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node, node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node, node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node, node.generators)

    # --- Exception handling ------------------------------------------------

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type:
            self.visit(node.type)
        if node.name:
            self._add_define(node.name)
        for child in node.body:
            self.visit(child)

    # --- NamedExpr (walrus) ------------------------------------------------

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._collect_target_names(node.target)

    # --- Global / Nonlocal -------------------------------------------------

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._add_define(name)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._add_use(target.id)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class CellDependencyAnalyzer:
    """Analyzes Python cells to detect variable dependencies."""

    def analyze_cell(self, cell_id: str, source: str) -> CellDependency:
        """Parse *source* and return a CellDependency with defines/uses."""
        dep = CellDependency(cell_id=cell_id)
        if not source or not source.strip():
            return dep

        try:
            tree = ast.parse(source, filename=f"<cell:{cell_id}>")
        except SyntaxError:
            logger.debug("SyntaxError in cell %s — skipping analysis", cell_id)
            return dep

        visitor = _DepVisitor()
        visitor.visit(tree)

        dep.defines = sorted(visitor.defines)
        # Only report *external* uses — names used but NOT defined in this cell
        dep.uses = sorted(visitor.uses - visitor.defines)
        dep.imports = visitor.imports
        dep.functions_defined = visitor.functions
        dep.classes_defined = visitor.classes

        return dep

    # -- graph building -----------------------------------------------------

    def build_graph(self, cells: list[tuple[str, str]]) -> DependencyGraph:
        """Build a full dependency graph for a list of *(cell_id, source)* pairs."""
        deps = [self.analyze_cell(cid, src) for cid, src in cells]

        # Map variable → defining cell (last writer wins for ordering purposes)
        var_to_cell: dict[str, str] = {}
        for dep in deps:
            for name in dep.defines:
                var_to_cell[name] = dep.cell_id

        # Build edges
        edges: list[dict[str, str]] = []
        adj: dict[str, set[str]] = defaultdict(set)  # from → {to}
        for dep in deps:
            for var in dep.uses:
                provider = var_to_cell.get(var)
                if provider and provider != dep.cell_id:
                    edges.append({
                        "from_cell": provider,
                        "to_cell": dep.cell_id,
                        "via_variable": var,
                    })
                    adj[provider].add(dep.cell_id)

        execution_order = self._topo_sort(deps, adj)

        return DependencyGraph(
            cells=deps,
            edges=edges,
            execution_order=execution_order,
            stale_cells=[],
        )

    # -- topological sort ---------------------------------------------------

    def get_execution_order(self, cells: list[tuple[str, str]]) -> list[str]:
        """Return a topologically sorted execution order."""
        graph = self.build_graph(cells)
        return graph.execution_order

    def _topo_sort(
        self,
        deps: list[CellDependency],
        adj: dict[str, set[str]],
    ) -> list[str]:
        """Kahn's algorithm. Falls back to original order on cycles."""
        all_ids = [d.cell_id for d in deps]
        in_degree: dict[str, int] = {cid: 0 for cid in all_ids}
        for src, targets in adj.items():
            for tgt in targets:
                if tgt in in_degree:
                    in_degree[tgt] += 1

        queue: deque[str] = deque()
        # Seed with zero-in-degree nodes, preserving original relative order
        for cid in all_ids:
            if in_degree[cid] == 0:
                queue.append(cid)

        ordered: list[str] = []
        while queue:
            node = queue.popleft()
            ordered.append(node)
            for neighbour in sorted(adj.get(node, []), key=lambda n: all_ids.index(n) if n in all_ids else 0):
                if neighbour in in_degree:
                    in_degree[neighbour] -= 1
                    if in_degree[neighbour] == 0:
                        queue.append(neighbour)

        # If there's a cycle, append remaining nodes in original order
        if len(ordered) < len(all_ids):
            remaining = [cid for cid in all_ids if cid not in set(ordered)]
            ordered.extend(remaining)

        return ordered

    # -- stale detection ----------------------------------------------------

    def find_stale_cells(
        self,
        modified_cell_id: str,
        cells: list[tuple[str, str]],
    ) -> list[str]:
        """Return cell IDs that transitively depend on *modified_cell_id*."""
        graph = self.build_graph(cells)

        # Build adjacency from edges
        adj: dict[str, set[str]] = defaultdict(set)
        for edge in graph.edges:
            adj[edge["from_cell"]].add(edge["to_cell"])

        # BFS from the modified cell
        visited: set[str] = set()
        queue: deque[str] = deque([modified_cell_id])
        while queue:
            node = queue.popleft()
            for child in adj.get(node, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)

        # Return stale cells in execution order
        stale = [cid for cid in graph.execution_order if cid in visited]
        return stale

    # -- convenience --------------------------------------------------------

    def suggest_cell_order(self, cells: list[tuple[str, str]]) -> list[str]:
        """Alias for ``get_execution_order`` — returns the optimal order."""
        return self.get_execution_order(cells)


# ---------------------------------------------------------------------------
# Rich output formatter
# ---------------------------------------------------------------------------

def format_dependency_output(graph: DependencyGraph) -> CellOutput:
    """Render a text-based dependency tree as rich HTML."""
    lines: list[str] = []

    # Header
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     📊 Cell Dependency Graph         ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")

    # Per-cell summary
    for dep in graph.cells:
        label = f"[{dep.cell_id}]"
        lines.append(f"┌─ {label}")
        if dep.defines:
            lines.append(f"│  defines : {', '.join(dep.defines)}")
        if dep.uses:
            lines.append(f"│  uses    : {', '.join(dep.uses)}")
        if dep.imports:
            lines.append(f"│  imports : {', '.join(dep.imports)}")
        if dep.functions_defined:
            lines.append(f"│  funcs   : {', '.join(dep.functions_defined)}")
        if dep.classes_defined:
            lines.append(f"│  classes : {', '.join(dep.classes_defined)}")
        lines.append("└──────────")

    # Edges
    if graph.edges:
        lines.append("")
        lines.append("Edges:")
        for edge in graph.edges:
            lines.append(
                f"  {edge['from_cell']} ──({edge['via_variable']})──▶ {edge['to_cell']}"
            )

    # Execution order
    lines.append("")
    lines.append(f"Execution order: {' → '.join(graph.execution_order)}")

    # Stale cells
    if graph.stale_cells:
        lines.append(f"⚠ Stale cells: {', '.join(graph.stale_cells)}")

    text = "\n".join(lines)

    html = (
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
        "padding:14px;background:#0f172a;border-radius:8px;"
        'border:1px solid rgba(255,255,255,0.06);white-space:pre;overflow-x:auto;'
        f'color:#e2e8f0">{_html_escape(text)}</div>'
    )

    return CellOutput(
        output_type="html",
        data=html,
        metadata={"dependency_graph": graph.to_dict()},
    )


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
