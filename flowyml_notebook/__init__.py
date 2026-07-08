"""🌊 FlowyML Notebook — Production-grade reactive notebook for ML pipelines.

FlowyML Notebook replaces Jupyter with a reactive, browser-based notebook.
Works standalone for any Python/ML workflow, with optional deep integration
with the FlowyML ML pipeline framework (pip install 'flowyml-notebook[flowyml]').

Core features:
- Reactive execution: cells form a dependency DAG
- Pure Python file format: git-friendly, lintable, importable
- Interactive widgets: sliders, charts, ML-specific visualizations
- AI assistant: context-aware code generation
- SQL cells: mixed Python + SQL workflows
- Scheduling & deployment: production-ready from within the notebook

Killer features:
- Cell Profiler: CPU, memory, and function call profiling
- Cell Benchmark: statistical timing with regression detection
- Data Validator: automatic DataFrame quality scoring
- Data Lineage: transformation tracking across cells
- Code Analyzer: smart linting with auto-fix for data science
- Cell Dependencies: AST-based dependency graph & stale detection
- Notebook Search: full-text/fuzzy/regex search & replace
- Snippets Library: 35 built-in data science code snippets
- Execution History: time-travel debugging & run comparison
- Environment Manager: snapshots, package install, requirements export
- Jupyter Import/Export: seamless .ipynb ↔ .py conversion
- Notebook Diff: cell-level notebook comparison
- Package Installer: in-notebook pip management
"""

__version__ = "2.0.7"
__author__ = "UnicoLab"


def __getattr__(name):
    """Lazy imports to avoid pulling in heavy dependencies at import time."""
    if name == "Notebook":
        from flowyml_notebook.core import Notebook

        return Notebook
    if name == "NotebookSession":
        from flowyml_notebook.core import NotebookSession

        return NotebookSession
    if name == "Cell":
        from flowyml_notebook.cells import Cell

        return Cell
    if name == "CellType":
        from flowyml_notebook.cells import CellType

        return CellType
    if name == "NotebookFile":
        from flowyml_notebook.cells import NotebookFile

        return NotebookFile
    if name == "ReactiveGraph":
        from flowyml_notebook.reactive import ReactiveGraph

        return ReactiveGraph
    if name == "from_ipynb":
        from flowyml_notebook.ipynb_converter import from_ipynb

        return from_ipynb
    if name == "to_ipynb":
        from flowyml_notebook.ipynb_converter import to_ipynb

        return to_ipynb
    if name == "CellProfiler":
        from flowyml_notebook.profiler import CellProfiler

        return CellProfiler
    if name == "LineageTracker":
        from flowyml_notebook.lineage import LineageTracker

        return LineageTracker
    if name == "diff_notebooks":
        from flowyml_notebook.diff import diff_notebooks

        return diff_notebooks
    if name == "CellBenchmark":
        from flowyml_notebook.benchmark import CellBenchmark

        return CellBenchmark
    if name == "DataValidator":
        from flowyml_notebook.data_validator import DataValidator

        return DataValidator
    if name == "CodeAnalyzer":
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        return CodeAnalyzer
    if name == "ExecutionHistory":
        from flowyml_notebook.execution_history import ExecutionHistory

        return ExecutionHistory
    if name == "SnippetLibrary":
        from flowyml_notebook.snippets import SnippetLibrary

        return SnippetLibrary
    if name == "CellDependencyAnalyzer":
        from flowyml_notebook.cell_deps import CellDependencyAnalyzer

        return CellDependencyAnalyzer
    if name == "NotebookSearch":
        from flowyml_notebook.search import NotebookSearch

        return NotebookSearch
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Notebook",
    "NotebookSession",
    "Cell",
    "CellType",
    "NotebookFile",
    "ReactiveGraph",
    "from_ipynb",
    "to_ipynb",
    "CellProfiler",
    "LineageTracker",
    "diff_notebooks",
    "CellBenchmark",
    "DataValidator",
    "CodeAnalyzer",
    "ExecutionHistory",
    "SnippetLibrary",
    "CellDependencyAnalyzer",
    "NotebookSearch",
]
