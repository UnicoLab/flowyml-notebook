"""Tests for the new killer features: snippets, cell_deps, search."""

import json

from flowyml_notebook.cell_deps import (
    CellDependency,
    CellDependencyAnalyzer,
)
from flowyml_notebook.cells import Cell, CellType
from flowyml_notebook.search import NotebookSearch, SearchResult
from flowyml_notebook.snippets import Snippet, SnippetLibrary

# ═══════════════════════════════════════════════════════════════════════
# TestSnippetLibrary
# ═══════════════════════════════════════════════════════════════════════


class TestSnippetLibrary:
    """Test the snippet library module."""

    def test_builtin_snippets_loaded(self):
        lib = SnippetLibrary()
        all_snippets = lib.search("")
        assert len(all_snippets) >= 30

    def test_get_categories(self):
        lib = SnippetLibrary()
        cats = lib.get_categories()
        assert len(cats) >= 14
        expected = {
            "Data Loading",
            "Data Cleaning",
            "EDA",
            "Feature Engineering",
            "ML Evaluation",
            "Modeling",
            "Utilities",
            "Visualization",
            "Production",
            "Deep Learning",
            "NLP",
            "Time Series",
            "Testing",
            "SQL & Databases",
        }
        assert expected.issubset(set(cats))

    def test_search_by_query(self):
        lib = SnippetLibrary()
        results = lib.search("pandas")
        assert len(results) > 0
        # At least one result should mention pandas in title, description, tags, or code
        for r in results:
            searchable = " ".join(
                [
                    r.title.lower(),
                    r.description.lower(),
                    r.code.lower(),
                    " ".join(r.tags),
                ]
            )
            assert "pandas" in searchable

    def test_search_by_category(self):
        lib = SnippetLibrary()
        results = lib.search("", category="Data Loading")
        assert len(results) > 0
        for r in results:
            assert r.category == "Data Loading"

    def test_search_empty_query(self):
        lib = SnippetLibrary()
        all_results = lib.search("")
        assert len(all_results) >= 30  # All snippets returned

    def test_get_snippet_by_id(self):
        lib = SnippetLibrary()
        snippet = lib.get_snippet("builtin-load-csv")
        assert snippet is not None
        assert snippet.id == "builtin-load-csv"
        assert snippet.title == "Load CSV File"

    def test_get_snippet_not_found(self):
        lib = SnippetLibrary()
        result = lib.get_snippet("nonexistent-id-xyz")
        assert result is None

    def test_add_custom_snippet(self):
        lib = SnippetLibrary()
        custom = Snippet(
            id="my-snippet",
            title="My Custom Snippet",
            description="A test snippet",
            code="print('hello')",
            category="Custom",
            tags=["test"],
        )
        returned = lib.add_custom(custom)
        assert returned.id == "my-snippet"

        retrieved = lib.get_snippet("my-snippet")
        assert retrieved is not None
        assert retrieved.title == "My Custom Snippet"

    def test_delete_custom_snippet(self):
        lib = SnippetLibrary()
        custom = Snippet(id="to-delete", title="Delete Me", code="pass")
        lib.add_custom(custom)
        assert lib.delete_custom("to-delete") is True
        assert lib.get_snippet("to-delete") is None

    def test_delete_nonexistent_snippet(self):
        lib = SnippetLibrary()
        assert lib.delete_custom("does-not-exist") is False

    def test_record_use(self):
        lib = SnippetLibrary()
        snippet = lib.get_snippet("builtin-load-csv")
        assert snippet is not None
        initial_uses = snippet.uses

        lib.record_use("builtin-load-csv")
        assert snippet.uses == initial_uses + 1

        lib.record_use("builtin-load-csv")
        assert snippet.uses == initial_uses + 2

    def test_snippet_to_dict(self):
        snippet = Snippet(
            id="test-1",
            title="Test",
            description="Desc",
            code="x = 1",
            category="Cat",
            tags=["a", "b"],
            language="python",
            difficulty="beginner",
            created_at="2024-01-01T00:00:00",
            uses=5,
        )
        d = snippet.to_dict()
        assert d["id"] == "test-1"
        assert d["title"] == "Test"
        assert d["description"] == "Desc"
        assert d["code"] == "x = 1"
        assert d["category"] == "Cat"
        assert d["tags"] == ["a", "b"]
        assert d["language"] == "python"
        assert d["difficulty"] == "beginner"
        assert d["created_at"] == "2024-01-01T00:00:00"
        assert d["uses"] == 5

    def test_snippet_to_dict_json_serializable(self):
        lib = SnippetLibrary()
        snippet = lib.get_snippet("builtin-load-csv")
        d = snippet.to_dict()
        # Must not raise
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["id"] == "builtin-load-csv"

    def test_search_case_insensitive(self):
        lib = SnippetLibrary()
        upper = lib.search("PANDAS")
        lower = lib.search("pandas")
        mixed = lib.search("Pandas")
        assert len(upper) == len(lower) == len(mixed)
        assert len(upper) > 0

    def test_search_by_tags(self):
        lib = SnippetLibrary()
        results = lib.search("", tags=["csv"])
        assert len(results) > 0
        for r in results:
            assert "csv" in [t.lower() for t in r.tags]


# ═══════════════════════════════════════════════════════════════════════
# TestCellDependencyAnalyzer
# ═══════════════════════════════════════════════════════════════════════


class TestCellDependencyAnalyzer:
    """Test the cell dependency analysis module."""

    def test_analyze_simple_assignment(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "x = 42")
        assert "x" in dep.defines

    def test_analyze_imports(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "import pandas as pd\nfrom os import path")
        assert "pd" in dep.defines
        assert "path" in dep.defines
        assert "pandas" in dep.imports
        assert "os.path" in dep.imports

    def test_analyze_function_def(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "def my_func(x):\n    return x + 1")
        assert "my_func" in dep.defines
        assert "my_func" in dep.functions_defined

    def test_analyze_class_def(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "class MyClass:\n    pass")
        assert "MyClass" in dep.defines
        assert "MyClass" in dep.classes_defined

    def test_analyze_tuple_unpacking(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "a, b = 1, 2")
        assert "a" in dep.defines
        assert "b" in dep.defines

    def test_analyze_uses(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "y = x + 1")
        assert "y" in dep.defines
        assert "x" in dep.uses

    def test_analyze_for_loop_var(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "for i in range(10):\n    pass")
        assert "i" in dep.defines

    def test_analyze_with_as(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "with open('f') as fh:\n    data = fh.read()")
        assert "fh" in dep.defines
        assert "data" in dep.defines

    def test_analyze_comprehension_scope(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "result = [x for x in items]")
        assert "result" in dep.defines
        # Comprehension variable 'x' should NOT leak to cell-level defines
        assert "x" not in dep.defines
        # 'items' is used
        assert "items" in dep.uses

    def test_build_graph(self):
        analyzer = CellDependencyAnalyzer()
        cells = [
            ("c1", "x = 42"),
            ("c2", "y = x + 1"),
        ]
        graph = analyzer.build_graph(cells)
        assert len(graph.cells) == 2
        assert len(graph.edges) == 1
        edge = graph.edges[0]
        assert edge["from_cell"] == "c1"
        assert edge["to_cell"] == "c2"
        assert edge["via_variable"] == "x"

    def test_execution_order(self):
        analyzer = CellDependencyAnalyzer()
        cells = [
            ("c1", "x = 42"),
            ("c2", "y = x + 1"),
            ("c3", "z = y * 2"),
        ]
        order = analyzer.get_execution_order(cells)
        assert order.index("c1") < order.index("c2")
        assert order.index("c2") < order.index("c3")

    def test_find_stale_cells(self):
        analyzer = CellDependencyAnalyzer()
        cells = [
            ("c1", "x = 42"),
            ("c2", "y = x + 1"),
            ("c3", "z = y * 2"),
        ]
        stale = analyzer.find_stale_cells("c1", cells)
        # c2 depends on c1, c3 depends on c2 → both should be stale
        assert "c2" in stale
        assert "c3" in stale
        # c1 itself is not stale, it's the modified cell
        assert "c1" not in stale

    def test_graph_to_dict(self):
        analyzer = CellDependencyAnalyzer()
        cells = [
            ("c1", "x = 42"),
            ("c2", "y = x + 1"),
        ]
        graph = analyzer.build_graph(cells)
        d = graph.to_dict()
        assert "cells" in d
        assert "edges" in d
        assert "execution_order" in d
        assert "stale_cells" in d
        assert isinstance(d["cells"], list)
        assert isinstance(d["edges"], list)

    def test_dependency_to_dict(self):
        dep = CellDependency(
            cell_id="c1",
            defines=["x", "y"],
            uses=["z"],
            imports=["os"],
            functions_defined=["foo"],
            classes_defined=["Bar"],
        )
        d = dep.to_dict()
        assert d["cell_id"] == "c1"
        assert d["defines"] == ["x", "y"]
        assert d["uses"] == ["z"]
        assert d["imports"] == ["os"]
        assert d["functions_defined"] == ["foo"]
        assert d["classes_defined"] == ["Bar"]

    def test_empty_cell(self):
        analyzer = CellDependencyAnalyzer()
        dep = analyzer.analyze_cell("c1", "")
        assert dep.defines == []
        assert dep.uses == []
        assert dep.imports == []
        assert dep.functions_defined == []
        assert dep.classes_defined == []

        dep2 = analyzer.analyze_cell("c2", "   \n  ")
        assert dep2.defines == []


# ═══════════════════════════════════════════════════════════════════════
# TestNotebookSearch
# ═══════════════════════════════════════════════════════════════════════


def _make_cells(sources: list[str], cell_type: CellType = CellType.CODE) -> list[Cell]:
    """Helper to create a list of Cell objects with sequential IDs."""
    return [Cell(id=f"c{i}", source=src, cell_type=cell_type) for i, src in enumerate(sources)]


class TestNotebookSearch:
    """Test the notebook search module."""

    def test_exact_search(self):
        search = NotebookSearch()
        cells = _make_cells(["import pandas as pd", "x = 42", "import numpy as np"])
        results = search.search(cells, "pandas")
        assert len(results) >= 1
        assert any(r.cell_id == "c0" for r in results)

    def test_case_insensitive_search(self):
        search = NotebookSearch()
        cells = _make_cells(["import Pandas as pd"])
        results = search.search(cells, "pandas", case_sensitive=False)
        assert len(results) >= 1

    def test_case_sensitive_search(self):
        search = NotebookSearch()
        cells = _make_cells(["import Pandas as pd"])
        results = search.search(cells, "pandas", case_sensitive=True)
        # "pandas" (lowercase) should NOT match "Pandas" (titlecase)
        exact = [r for r in results if r.match_type == "exact"]
        assert len(exact) == 0

    def test_regex_search(self):
        search = NotebookSearch()
        cells = _make_cells(["x = 42", "y = 100", "z = 7"])
        results = search.search(cells, r"\d{2,}", regex=True)
        assert len(results) >= 2  # matches 42 and 100
        for r in results:
            assert r.match_type == "regex"

    def test_fuzzy_search(self):
        search = NotebookSearch()
        cells = _make_cells(["import pandas as pd"])
        # 'panda' is close to 'pandas' — should get a fuzzy match
        results = search.search(cells, "panda", fuzzy_threshold=0.6)
        assert len(results) >= 1

    def test_search_no_results(self):
        search = NotebookSearch()
        cells = _make_cells(["x = 42", "y = 100"])
        results = search.search(cells, "zzzznotfound_xyzxyz")
        assert len(results) == 0

    def test_search_and_replace(self):
        search = NotebookSearch()
        cells = _make_cells(["x = old_value", "y = old_value + 1"])
        changes = search.search_and_replace(cells, "old_value", "new_value")
        assert len(changes) >= 2
        # Verify replacement happened in-place
        assert "new_value" in cells[0].source
        assert "new_value" in cells[1].source
        assert "old_value" not in cells[0].source

    def test_find_all_variables(self):
        search = NotebookSearch()
        cells = _make_cells(["x = 42\ny = 10", "z = x + y"])
        var_map = search.find_all_variables(cells)
        assert "x" in var_map
        assert "y" in var_map
        assert "z" in var_map
        assert "c0" in var_map["x"]
        assert "c1" in var_map["z"]

    def test_find_all_functions(self):
        search = NotebookSearch()
        cells = _make_cells(
            [
                "def foo():\n    pass",
                "class Bar:\n    pass",
            ]
        )
        func_map = search.find_all_functions(cells)
        assert "foo" in func_map
        assert "Bar" in func_map
        assert "c0" in func_map["foo"]
        assert "c1" in func_map["Bar"]

    def test_find_duplicates(self):
        search = NotebookSearch()
        cells = _make_cells(
            [
                "x = 42\nprint(x)",
                "x = 42\nprint(x)",
                "y = 100",
            ]
        )
        dups = search.find_duplicates(cells)
        assert len(dups) >= 1
        dup = dups[0]
        assert dup["similarity"] >= 0.85
        assert "c0" in dup["cell_ids"]
        assert "c1" in dup["cell_ids"]

    def test_result_to_dict(self):
        result = SearchResult(
            cell_id="c1",
            cell_index=0,
            cell_type="code",
            line_number=1,
            match_text="pandas",
            context="import pandas as pd",
            score=1.0,
            match_type="exact",
        )
        d = result.to_dict()
        assert d["cell_id"] == "c1"
        assert d["cell_index"] == 0
        assert d["cell_type"] == "code"
        assert d["line_number"] == 1
        assert d["match_text"] == "pandas"
        assert d["context"] == "import pandas as pd"
        assert d["score"] == 1.0
        assert d["match_type"] == "exact"
        # Verify JSON serializable
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_max_results_limit(self):
        search = NotebookSearch()
        # Create many cells each containing the query
        cells = _make_cells([f"x_{i} = pandas" for i in range(100)])
        results = search.search(cells, "pandas", max_results=5)
        assert len(results) <= 5
