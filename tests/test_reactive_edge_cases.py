"""Edge case tests for the reactive engine position-aware dependency analysis."""

import pytest
from flowyml_notebook.reactive import analyze_cell_dependencies


class TestPositionAwareDependencies:
    """Tests for correct order-aware read/write analysis."""

    def test_write_before_read_not_upstream(self):
        """x = 1; y = x + 1 → x is NOT an upstream dependency (write-first)."""
        r, w = analyze_cell_dependencies("x = 1\ny = x + 1")
        assert "x" not in r, "x should NOT be upstream dependency (defined before used)"
        assert "y" in w

    def test_self_referencing_assignment_is_upstream(self):
        """df = df.dropna() → df IS an upstream dependency (RHS evaluated first)."""
        r, w = analyze_cell_dependencies("df = df.dropna()")
        assert "df" in r, "df should be upstream dependency (self-referencing assignment)"
        assert "df" in w

    def test_subscript_mutation_reads_value(self):
        """df['x'] = values → df is mutated, values is read."""
        r, w = analyze_cell_dependencies('df["x"] = values')
        assert "df" in r, "df should be read (accessed then mutated)"
        assert "values" in r, "values should be an upstream dependency"
        assert "df" in w, "df should be a write (mutation)"

    def test_list_append_mutation(self):
        """lst.append(1) → lst is both read and written (mutation)."""
        r, w = analyze_cell_dependencies("lst.append(1)")
        assert "lst" in r, "lst should be read (mutating method)"
        assert "lst" in w, "lst should be a write (mutation)"

    def test_augmented_assignment(self):
        """x += y → both x and y are upstream dependencies."""
        r, w = analyze_cell_dependencies("x += y")
        assert "x" in r, "x should be read (augmented assignment)"
        assert "y" in r, "y should be read"

    def test_import_is_write_only(self):
        """import pandas as pd → pd is written, not read."""
        r, w = analyze_cell_dependencies("import pandas as pd")
        assert "pd" not in r, "pd should not be a read"
        assert "pd" in w, "pd should be a write"

    def test_function_def_then_use_not_upstream(self):
        """def f then y = f(x) → f is NOT upstream (defined before used), x IS."""
        r, w = analyze_cell_dependencies("def f(a): return a*2\ny = f(x)")
        assert "f" not in r, "f should NOT be upstream (defined before used)"
        assert "x" in r, "x should be upstream dependency"

    def test_multiline_write_then_read(self):
        """Multi-line: write on line 1, read on line 2 → NOT upstream."""
        r, w = analyze_cell_dependencies("data = [1, 2, 3]\ntotal = sum(data)")
        assert "data" not in r, "data should NOT be upstream (written before read)"
        assert "data" in w

    def test_same_line_chained_transform(self):
        """result = df.groupby('a').mean() → df IS upstream."""
        r, w = analyze_cell_dependencies("result = df.groupby('a').mean()")
        assert "df" in r, "df should be upstream dependency"
        assert "result" in w
