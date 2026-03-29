"""🌊 FlowyML Notebook — Production-grade reactive notebook for ML pipelines.

FlowyML Notebook replaces Jupyter with a reactive, browser-based notebook
deeply integrated with the FlowyML ML pipeline framework.

Key features:
- Reactive execution: cells form a dependency DAG
- Pure Python file format: git-friendly, lintable, importable
- Interactive widgets: sliders, charts, ML-specific visualizations
- AI assistant: context-aware code generation
- SQL cells: mixed Python + SQL workflows
- Scheduling & deployment: production-ready from within the notebook
"""

__version__ = "1.4.0"
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Notebook",
    "NotebookSession",
    "Cell",
    "CellType",
    "NotebookFile",
    "ReactiveGraph",
]
