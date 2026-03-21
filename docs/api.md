# 📚 API Reference

## CLI Reference

FlowyML Notebook provides six CLI commands via the `fml-notebook` entry point.

### `fml-notebook dev`

Launch in development mode with Vite hot reload and FastAPI backend.

```bash
fml-notebook dev [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--name` | `untitled` | Notebook name |
| `--server` | — | FlowyML server URL |
| `--file` | — | Load notebook from `.py` file |
| `--frontend-port` | `3000` | Vite dev server port |
| `--backend-port` | `8888` | API server port |
| `--no-browser` | `false` | Don't auto-open browser |

### `fml-notebook start`

Launch with production-built frontend (single port).

```bash
fml-notebook start [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--name` | `untitled` | Notebook name |
| `--server` | — | FlowyML server URL |
| `--port` | `8888` | Server port |
| `--file` | — | Load notebook from `.py` file |
| `--no-browser` | `false` | Don't auto-open browser |

### `fml-notebook run`

Execute a notebook headlessly (no GUI).

```bash
fml-notebook run <file> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--server` | — | FlowyML server URL for remote execution |

### `fml-notebook export`

Export a notebook to various formats.

```bash
fml-notebook export <file> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--format` | `pipeline` | Export format: `pipeline`, `html`, `pdf`, `docker` |
| `--output`, `-o` | — | Output file path |

### `fml-notebook app`

Deploy a notebook as a standalone web application.

```bash
fml-notebook app <file> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--port` | `8501` | App server port |
| `--layout` | `linear` | Layout: `linear`, `grid`, `tabs`, `sidebar`, `dashboard` |

### `fml-notebook list`

List notebooks on a remote FlowyML server.

```bash
fml-notebook list --server <URL>
```

---

## Python API

### Core Classes

#### `Notebook`

The main execution engine. Manages cells, the reactive graph, and execution.

```python
from flowyml_notebook import Notebook

nb = Notebook(file_path="my_notebook.py")
nb.connect("https://flowyml.example.com")  # Optional
results = nb.run()
```

::: flowyml_notebook.core.Notebook
    options:
      show_source: false
      members: false

#### `Cell`

Represents a single execution unit in the notebook.

```python
from flowyml_notebook import Cell, CellType

cell = Cell(
    id="load_data",
    cell_type=CellType.PYTHON,
    source="import pandas as pd\ndf = pd.read_csv('data.csv')",
)
```

::: flowyml_notebook.cells.Cell
    options:
      show_source: false
      members: false

#### `ReactiveGraph`

The DAG engine that tracks dependencies between cells.

```python
from flowyml_notebook import ReactiveGraph

graph = ReactiveGraph()
graph.update_cell("cell_1", reads=set(), writes={"x"})
graph.update_cell("cell_2", reads={"x"}, writes={"y"})

# Get execution order
order = graph.topological_sort()
```

::: flowyml_notebook.reactive.ReactiveGraph
    options:
      show_source: false
      members: false

#### `NotebookSession`

Manages the kernel, namespace, and execution state for a live session.

::: flowyml_notebook.core.NotebookSession
    options:
      show_source: false
      members: false

---

### Supporting Modules

| Module | Purpose |
|---|---|
| `flowyml_notebook.cli` | CLI entry point and command handlers |
| `flowyml_notebook.server` | FastAPI server with WebSocket support |
| `flowyml_notebook.kernel` | Python kernel for cell execution |
| `flowyml_notebook.connection` | FlowyML instance connector |
| `flowyml_notebook.github_sync` | GitHub collaboration backend |
| `flowyml_notebook.recipes_store` | Recipe management |
| `flowyml_notebook.reporting` | HTML/PDF report generation |
| `flowyml_notebook.deployer` | Pipeline export and Docker generation |
| `flowyml_notebook.sql` | SQL cell engine (DuckDB, SQLAlchemy) |
| `flowyml_notebook.ai` | AI assistant integration |
| `flowyml_notebook.ui` | App mode and widget system |
