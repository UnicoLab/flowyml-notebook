"""Reactive dependency graph for notebook cells.

Analyzes Python AST to determine which variables each cell reads/writes,
builds a dependency DAG, and computes topological execution order.
When a cell is modified, identifies all downstream cells that need re-execution.
"""

import ast
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CellState(str, Enum):
    """Execution state of a cell."""

    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    STALE = "stale"  # Upstream changed, needs re-run


@dataclass
class CellDependency:
    """Dependency information for a single cell."""

    cell_id: str
    reads: set[str] = field(default_factory=set)  # Variables this cell reads
    writes: set[str] = field(default_factory=set)  # Variables this cell defines
    upstream: set[str] = field(default_factory=set)  # Cell IDs this depends on
    downstream: set[str] = field(default_factory=set)  # Cell IDs that depend on this
    state: CellState = CellState.IDLE


# Known mutating methods on common types (list, dict, set, DataFrame, etc.)
_MUTATING_METHODS = frozenset({
    # Python builtins (list, dict, set)
    "append", "extend", "insert", "pop", "remove", "update", "clear",
    "sort", "reverse", "add", "discard",
    # Pandas DataFrame / Series
    "drop", "fillna", "sort_values", "sort_index", "rename", "reset_index",
    "set_index", "replace", "clip", "interpolate", "dropna",
    "assign", "eval", "query",  # return new unless inplace=True
    # NumPy in-place
    "fill", "resize", "put", "itemset",
})


class _NameExtractor(ast.NodeVisitor):
    """AST visitor that extracts read/write variable names from Python code.

    Enhanced to detect:
    - Direct assignments: x = ...
    - Subscript mutations: df['col'] = ...
    - Attribute mutations: obj.attr = ...
    - Augmented assignments: x += ...
    - Mutating method calls: lst.append(...), df.drop(..., inplace=True)
    - Order-aware read/write for self-referencing: df = df.dropna()
    """

    def __init__(self):
        self.reads: set[str] = set()
        self.writes: set[str] = set()
        self.mutations: set[str] = set()  # Variables mutated in-place
        self._in_target = False
        # Position tracking for order-aware analysis: {name: (line, col)}
        self.read_positions: dict[str, tuple[int, int]] = {}  # first read position
        self.write_positions: dict[str, tuple[int, int]] = {}  # first write position

    def _record_read(self, name: str, node: ast.AST) -> None:
        """Record a read and its position (first occurrence only)."""
        self.reads.add(name)
        if name not in self.read_positions:
            self.read_positions[name] = (getattr(node, 'lineno', 0), getattr(node, 'col_offset', 0))

    def _record_write(self, name: str, node: ast.AST) -> None:
        """Record a write and its position (first occurrence only)."""
        self.writes.add(name)
        if name not in self.write_positions:
            self.write_positions[name] = (getattr(node, 'lineno', 0), getattr(node, 'col_offset', 0))

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._record_write(node.id, node)
        elif isinstance(node.ctx, ast.Load):
            self._record_read(node.id, node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._record_write(node.name, node)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults:
            self.visit(default)
        for child in node.body:
            self.visit(child)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._record_write(node.name, node)
        for base in node.bases:
            self.visit(base)
        for child in node.body:
            self.visit(child)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self._record_write(name, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname if alias.asname else alias.name
            self._record_write(name, node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self._extract_target_names(node.target)
        self.visit(node.iter)
        for child in node.body:
            self.visit(child)
        for child in node.orelse:
            self.visit(child)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._extract_target_names(item.optional_vars)
        for child in node.body:
            self.visit(child)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        """Track subscript and attribute assignments as mutations.

        e.g. df['new_col'] = values  →  marks 'df' as mutated (write)
             obj.attr = value        →  marks 'obj' as mutated (write)
        """
        for target in node.targets:
            base = self._get_base_name(target)
            if base and isinstance(target, (ast.Subscript, ast.Attribute)):
                self.mutations.add(base)
                self._record_read(base, target)  # also a read (we access then mutate)
            else:
                self._extract_target_names(target)
        self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        """Track augmented assignments: x += ... marks x as both read and write."""
        base = self._get_base_name(node.target)
        if base:
            self._record_read(base, node)
            self.mutations.add(base)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        """Handle annotated assignments: x: int = ..."""
        if node.target:
            self._extract_target_names(node.target)
        if node.value:
            self.visit(node.value)

    def visit_Delete(self, node: ast.Delete) -> None:  # noqa: N802
        for target in node.targets:
            base = self._get_base_name(target)
            if base:
                self.mutations.add(base)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Detect mutating method calls.

        e.g. lst.append(x)             → marks 'lst' as mutated
             df.drop('col', inplace=True) → marks 'df' as mutated
        """
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            base = self._get_base_name(node.func.value)

            if base and method_name in _MUTATING_METHODS:
                # Check for inplace=True for pandas-style methods
                has_inplace = any(
                    isinstance(kw.arg, str) and kw.arg == "inplace"
                    and isinstance(kw.value, ast.Constant) and kw.value.value is True
                    for kw in node.keywords
                )
                # For known always-mutating methods (list.append, etc.) or inplace=True
                always_mutating = method_name in {
                    "append", "extend", "insert", "pop", "remove",
                    "update", "clear", "sort", "reverse", "add", "discard",
                    "fill", "resize", "put", "itemset",
                }
                if always_mutating or has_inplace:
                    self.mutations.add(base)
                    self._record_read(base, node)

        # Visit all children (arguments, etc.)
        self.generic_visit(node)

    def _get_base_name(self, node: ast.AST) -> str | None:
        """Extract the root variable name from a chain of attribute/subscript access.

        e.g. df['col']  → 'df'
             obj.attr   → 'obj'
             a.b.c      → 'a'
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, (ast.Attribute, ast.Subscript)):
            return self._get_base_name(
                node.value if isinstance(node, (ast.Attribute, ast.Subscript)) else node
            )
        return None

    def _extract_target_names(self, node: ast.AST) -> None:
        """Extract variable names from assignment targets."""
        if isinstance(node, ast.Name):
            self._record_write(node.id, node)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._extract_target_names(elt)
        elif isinstance(node, ast.Starred):
            self._extract_target_names(node.value)
        elif isinstance(node, (ast.Subscript, ast.Attribute)):
            base = self._get_base_name(node)
            if base:
                self.mutations.add(base)
                self._record_read(base, node)


def analyze_cell_dependencies(source: str) -> tuple[set[str], set[str]]:
    """Analyze a cell's source code to determine which variables it reads and writes.

    Uses order-aware analysis: if a cell has `df = df.dropna()`, 'df' is both
    a read (dependency on upstream) AND a write (produces new value). This is
    critical for reactive propagation — the cell depends on whoever defined 'df'
    upstream, and downstream cells depend on this cell's new 'df'.

    However, if a cell has `x = 1; y = x + 1`, then 'x' is NOT an upstream
    dependency because 'x' is defined before it is read.

    Args:
        source: Python source code of the cell.

    Returns:
        Tuple of (reads, writes) sets of variable names.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        logger.debug("Failed to parse cell source for dependency analysis")
        return set(), set()

    extractor = _NameExtractor()
    extractor.visit(tree)

    # Combine explicit writes with mutations (in-place modifications count as writes)
    all_writes = extractor.writes | extractor.mutations

    # Order-aware read/write analysis using position tracking:
    # A variable is a TRUE upstream read dependency only if:
    #   1. It's only read (never written) in this cell, OR
    #   2. It's read BEFORE its first write (on an earlier statement/line)
    #   3. It's read and written on the SAME line (e.g. df = df.dropna())
    #      — in Python the RHS is always evaluated before the LHS store
    # A variable is NOT an upstream dependency if:
    #   - It's written on an earlier line than it is first read (e.g. x = 1\ny = x + 1)
    true_reads = set()
    for name in extractor.reads:
        if name not in extractor.writes and name not in extractor.mutations:
            # Only read, never written — always a dependency
            true_reads.add(name)
        else:
            # Both read and written — check order using LINE numbers only.
            # Column offsets are misleading for same-line assignments because
            # Python evaluates the RHS before storing to the LHS target.
            read_line = extractor.read_positions.get(name, (0, 0))[0]
            write_line = extractor.write_positions.get(name, (float('inf'), 0))[0]
            # For mutations (augmented assign, in-place), they are always dependencies
            # because the mutation reads from the current value
            if name in extractor.mutations:
                true_reads.add(name)
            elif read_line <= write_line:
                # Read occurs on the same line or before write — upstream dependency
                # Same line: df = df.dropna() → RHS evaluated first → dependency
                # Earlier line: read before any write → dependency
                true_reads.add(name)
            # else: write occurs on an earlier line — NOT an upstream dependency

    # Filter out Python builtins and common imports.
    # Use `import builtins` instead of `__builtins__` to avoid context-dependent
    # behavior: in __main__, __builtins__ is a dict and dir() returns dict methods
    # like 'values', 'keys', 'items' — incorrectly filtering user variables.
    import builtins as _builtins_mod
    _BUILTINS = set(dir(_builtins_mod))
    true_reads -= _BUILTINS
    true_reads -= {"__name__", "__file__", "__doc__"}

    return true_reads, all_writes


class ReactiveGraph:
    """Reactive dependency graph for notebook cells.

    Maintains a DAG of cell dependencies based on variable reads/writes.
    When a cell changes, computes which downstream cells become stale
    and the correct execution order.
    """

    def __init__(self):
        self._cells: dict[str, CellDependency] = {}
        self._var_producers: dict[str, str] = {}  # var_name -> cell_id that writes it

    @property
    def cells(self) -> dict[str, CellDependency]:
        """Get all cell dependencies."""
        return dict(self._cells)

    def update_cell(self, cell_id: str, source: str) -> set[str]:
        """Update dependency info for a cell and return IDs of stale downstream cells.

        Args:
            cell_id: Unique cell identifier.
            source: Python source code of the cell.

        Returns:
            Set of cell IDs that are now stale and need re-execution.
        """
        reads, writes = analyze_cell_dependencies(source)

        # Remove old producer mappings for this cell
        if cell_id in self._cells:
            old_writes = self._cells[cell_id].writes
            for var in old_writes:
                if self._var_producers.get(var) == cell_id:
                    del self._var_producers[var]

        # Create/update cell dependency info
        dep = CellDependency(cell_id=cell_id, reads=reads, writes=writes)
        self._cells[cell_id] = dep

        # Register as producer for written variables
        for var in writes:
            self._var_producers[var] = cell_id

        # Rebuild edges for ALL cells (since variable bindings may have changed)
        self._rebuild_edges()

        # Find all downstream cells that are now stale
        stale = self._find_downstream(cell_id)
        for stale_id in stale:
            if stale_id in self._cells:
                self._cells[stale_id].state = CellState.STALE

        return stale

    def remove_cell(self, cell_id: str) -> set[str]:
        """Remove a cell from the graph.

        Args:
            cell_id: Cell to remove.

        Returns:
            Set of cell IDs that are now stale.
        """
        if cell_id not in self._cells:
            return set()

        stale = self._find_downstream(cell_id)

        # Remove producer mappings
        for var in self._cells[cell_id].writes:
            if self._var_producers.get(var) == cell_id:
                del self._var_producers[var]

        del self._cells[cell_id]
        self._rebuild_edges()

        return stale

    def get_execution_order(self, cell_ids: set[str] | None = None) -> list[str]:
        """Get topological execution order for a set of cells.

        Args:
            cell_ids: Cells to order. If None, orders all cells.

        Returns:
            List of cell IDs in dependency-safe execution order.
        """
        target_ids = cell_ids or set(self._cells.keys())

        # Kahn's algorithm for topological sort
        in_degree: dict[str, int] = {cid: 0 for cid in target_ids}
        for cid in target_ids:
            if cid in self._cells:
                for upstream_id in self._cells[cid].upstream:
                    if upstream_id in target_ids:
                        in_degree[cid] = in_degree.get(cid, 0) + 1

        queue: list[str] = [cid for cid, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            # Sort for deterministic ordering
            queue.sort()
            cell_id = queue.pop(0)
            result.append(cell_id)

            if cell_id in self._cells:
                for downstream_id in self._cells[cell_id].downstream:
                    if downstream_id in in_degree:
                        in_degree[downstream_id] -= 1
                        if in_degree[downstream_id] == 0:
                            queue.append(downstream_id)

        # Handle cycles: add remaining cells at the end
        remaining = target_ids - set(result)
        if remaining:
            logger.warning(f"Circular dependency detected involving cells: {remaining}")
            result.extend(sorted(remaining))

        return result

    def get_stale_cells(self) -> set[str]:
        """Get all cells currently marked as stale."""
        return {cid for cid, dep in self._cells.items() if dep.state == CellState.STALE}

    def get_cell_state(self, cell_id: str) -> CellState:
        """Get the current state of a cell."""
        if cell_id in self._cells:
            return self._cells[cell_id].state
        return CellState.IDLE

    def set_cell_state(self, cell_id: str, state: CellState) -> None:
        """Set the state of a cell."""
        if cell_id in self._cells:
            self._cells[cell_id].state = state

    def get_upstream(self, cell_id: str) -> set[str]:
        """Get cell IDs that this cell depends on."""
        if cell_id in self._cells:
            return set(self._cells[cell_id].upstream)
        return set()

    def get_downstream(self, cell_id: str) -> set[str]:
        """Get cell IDs that depend on this cell."""
        if cell_id in self._cells:
            return set(self._cells[cell_id].downstream)
        return set()

    def _rebuild_edges(self) -> None:
        """Rebuild all upstream/downstream edges based on current variable mappings."""
        # Clear all edges
        for dep in self._cells.values():
            dep.upstream.clear()
            dep.downstream.clear()

        # Rebuild edges: if cell A reads var X and cell B writes var X, then A depends on B
        for cell_id, dep in self._cells.items():
            for var in dep.reads:
                producer_id = self._var_producers.get(var)
                if producer_id and producer_id != cell_id and producer_id in self._cells:
                    dep.upstream.add(producer_id)
                    self._cells[producer_id].downstream.add(cell_id)

    def _find_downstream(self, cell_id: str) -> set[str]:
        """Find all transitively downstream cells (BFS)."""
        visited: set[str] = set()
        queue = [cell_id]

        while queue:
            current = queue.pop(0)
            if current in self._cells:
                for downstream_id in self._cells[current].downstream:
                    if downstream_id not in visited:
                        visited.add(downstream_id)
                        queue.append(downstream_id)

        return visited

    def to_dict(self) -> dict:
        """Serialize the graph for API/WebSocket transmission."""
        return {
            "cells": {
                cid: {
                    "reads": sorted(dep.reads),
                    "writes": sorted(dep.writes),
                    "upstream": sorted(dep.upstream),
                    "downstream": sorted(dep.downstream),
                    "state": dep.state.value,
                }
                for cid, dep in self._cells.items()
            },
            "var_producers": dict(self._var_producers),
        }
