"""Tests for the reactive dependency graph."""

import pytest
from flowyml_notebook.reactive import (
    ReactiveGraph,
    CellState,
    CellDependency,
    analyze_cell_dependencies,
)


class TestAnalyzeCellDependencies:
    """Test AST-based variable analysis."""

    def test_simple_assignment(self):
        reads, writes = analyze_cell_dependencies("x = 42")
        assert "x" in writes
        assert "x" not in reads

    def test_read_variable(self):
        reads, writes = analyze_cell_dependencies("y = x + 1")
        assert "x" in reads
        assert "y" in writes

    def test_import(self):
        reads, writes = analyze_cell_dependencies("import pandas as pd")
        assert "pd" in writes

    def test_from_import(self):
        reads, writes = analyze_cell_dependencies("from os.path import join")
        assert "join" in writes

    def test_function_def(self):
        reads, writes = analyze_cell_dependencies("def train(data):\n    return data * 2")
        assert "train" in writes

    def test_class_def(self):
        reads, writes = analyze_cell_dependencies("class Model:\n    pass")
        assert "Model" in writes

    def test_for_loop(self):
        reads, writes = analyze_cell_dependencies("for i in range(10):\n    print(i)")
        assert "i" in writes
        assert "range" not in reads  # builtin

    def test_self_reference_excluded(self):
        reads, writes = analyze_cell_dependencies("x = 1\ny = x + 1")
        assert "x" in writes
        assert "y" in writes
        # x is both read and written in same cell — read should be excluded
        assert "x" not in reads

    def test_syntax_error_graceful(self):
        reads, writes = analyze_cell_dependencies("def broken(")
        assert reads == set()
        assert writes == set()

    def test_multi_assignment(self):
        reads, writes = analyze_cell_dependencies("a, b = 1, 2")
        assert "a" in writes
        assert "b" in writes

    def test_augmented_assignment_reads(self):
        reads, writes = analyze_cell_dependencies("total += x")
        assert "x" in reads

    def test_list_comprehension(self):
        reads, writes = analyze_cell_dependencies("result = [f(x) for x in data]")
        assert "result" in writes
        assert "data" in reads
        assert "f" in reads

    def test_with_statement(self):
        reads, writes = analyze_cell_dependencies("with open('f') as fp:\n    text = fp.read()")
        assert "fp" in writes
        assert "text" in writes


class TestReactiveGraph:
    """Test the reactive dependency graph."""

    def test_empty_graph(self):
        g = ReactiveGraph()
        assert g.cells == {}
        assert g.get_execution_order() == []

    def test_single_cell(self):
        g = ReactiveGraph()
        stale = g.update_cell("c1", "x = 42")
        assert stale == set()
        assert "c1" in g.cells

    def test_dependency_detection(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 42")
        g.update_cell("c2", "y = x + 1")

        assert "c1" in g.get_upstream("c2")
        assert "c2" in g.get_downstream("c1")

    def test_stale_detection(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 42")
        g.update_cell("c2", "y = x + 1")
        g.set_cell_state("c2", CellState.SUCCESS)

        # Modify c1 → c2 should become stale
        stale = g.update_cell("c1", "x = 100")
        assert "c2" in stale

    def test_transitive_stale(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = x + 1")
        g.update_cell("c3", "z = y * 2")

        stale = g.update_cell("c1", "x = 2")
        assert "c2" in stale
        assert "c3" in stale

    def test_execution_order(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = x + 1")
        g.update_cell("c3", "z = y * 2")

        order = g.get_execution_order()
        assert order.index("c1") < order.index("c2")
        assert order.index("c2") < order.index("c3")

    def test_independent_cells(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = 2")

        # Neither cell depends on the other
        assert g.get_upstream("c1") == set()
        assert g.get_upstream("c2") == set()

    def test_remove_cell(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = x + 1")

        stale = g.remove_cell("c1")
        assert "c1" not in g.cells
        assert "c2" in stale  # c2 loses its dependency

    def test_diamond_dependency(self):
        """A → B, A → C, B+C → D"""
        g = ReactiveGraph()
        g.update_cell("a", "x = 1")
        g.update_cell("b", "y = x + 1")
        g.update_cell("c", "z = x + 2")
        g.update_cell("d", "w = y + z")

        order = g.get_execution_order()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_to_dict(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = x + 1")

        d = g.to_dict()
        assert "cells" in d
        assert "var_producers" in d
        assert "c1" in d["cells"]
        assert "c2" in d["cells"]
        assert d["var_producers"]["x"] == "c1"

    def test_get_stale_cells(self):
        g = ReactiveGraph()
        g.update_cell("c1", "x = 1")
        g.update_cell("c2", "y = x + 1")
        g.set_cell_state("c2", CellState.STALE)

        stale = g.get_stale_cells()
        assert "c2" in stale


class TestCellState:
    """Test cell state enum."""

    def test_state_values(self):
        assert CellState.IDLE.value == "idle"
        assert CellState.SUCCESS.value == "success"
        assert CellState.ERROR.value == "error"
        assert CellState.STALE.value == "stale"
        assert CellState.RUNNING.value == "running"
