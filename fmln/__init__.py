"""fmln — Short alias for flowyml_notebook.

This module re-exports the entire flowyml_notebook public API
so users can write:

    import fmln
    nb = fmln.Notebook("my_analysis")

instead of:

    import flowyml_notebook
    nb = flowyml_notebook.Notebook("my_analysis")
"""

from flowyml_notebook import (
    __version__,
    __all__,
)

# Re-export via lazy __getattr__ — same pattern as parent package
def __getattr__(name):
    """Lazy imports delegating to flowyml_notebook."""
    import flowyml_notebook
    return getattr(flowyml_notebook, name)
