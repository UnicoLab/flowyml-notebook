# 📚 API Reference

## CLI Reference

FlowyML Notebook provides eight CLI commands via the `fml-notebook` entry point.

!!! tip "Short Alias"
    All commands work with the `fmln` alias: `fmln dev`, `fmln start`, `fmln convert`, etc.

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

### `fml-notebook convert`

Convert between `.ipynb` and `.py` notebook formats.

```bash
fml-notebook convert <file> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--output`, `-o` | — | Output file path (auto-detected from input extension) |

### `fml-notebook diff`

Compare two notebooks and display cell-level differences.

```bash
fml-notebook diff <file_a> <file_b> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--html` | `false` | Output diff as HTML instead of terminal text |

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

### REST API — Data Intelligence (v1.2)

#### SmartPrep Advisor

```
GET /api/smartprep/{var_name}?target={target_col}
```

Analyzes a DataFrame variable and returns severity-ranked preprocessing suggestions with ready-to-run code.

**Response:**

```json
{
  "variable": "df",
  "rows": 1000,
  "columns": 12,
  "total_issues": 5,
  "suggestions": [
    {
      "type": "impute_numeric",
      "severity": "medium",
      "column": "age",
      "title": "Impute 'age' — 3.2% missing",
      "reason": "Numeric column with 32 missing values...",
      "code": "df['age'] = df['age'].fillna(df['age'].median())"
    }
  ]
}
```

#### Algorithm Matchmaker

```
GET /api/algorithm-match/{var_name}?target={target_col}
```

Detects task type and returns ranked ML algorithm recommendations with pipeline code.

**Response:**

```json
{
  "variable": "df",
  "task_type": "classification",
  "data_characteristics": {"n_samples": 5000, "n_features": 12},
  "recommendations": [
    {
      "name": "XGBoost",
      "score": 95,
      "speed": "medium",
      "interpretability": "medium",
      "reasons": ["State-of-the-art for tabular data", "..."],
      "code": "from xgboost import XGBClassifier\n..."
    }
  ]
}
```

#### Analysis Patterns

```
GET    /api/patterns                    # List all patterns
POST   /api/patterns                    # Save a new pattern
DELETE /api/patterns/{pattern_id}       # Delete a pattern
POST   /api/patterns/{pattern_id}/apply # Apply pattern (insert cells)
POST   /api/patterns/search             # Search by query, tags, type
```

**Create pattern body:**

```json
{
  "name": "EDA Starter",
  "description": "Basic exploratory data analysis",
  "tags": ["eda", "pandas"],
  "cells": [{"source": "import pandas as pd", "cell_type": "code"}],
  "problem_type": "eda",
  "data_type": "tabular"
}
```

### REST API — Killer Features

See the comprehensive [Killer Features](killer-features.md) page for full API documentation covering all 13 built-in tools (profiler, benchmark, data validator, code analyzer, execution history, lineage, environment, package installer, Jupyter converter, notebook diff, snippets, cell dependencies, and search).

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
| `flowyml_notebook.profiler` | Cell CPU/memory profiling |
| `flowyml_notebook.benchmark` | Statistical cell benchmarking |
| `flowyml_notebook.data_validator` | DataFrame quality scoring |
| `flowyml_notebook.code_analyzer` | Smart linting and auto-fix |
| `flowyml_notebook.execution_history` | Time-travel debugging |
| `flowyml_notebook.lineage` | Data transformation tracking |
| `flowyml_notebook.environment` | Environment snapshots |
| `flowyml_notebook.package_installer` | In-notebook package management |
| `flowyml_notebook.ipynb_converter` | Jupyter .ipynb conversion |
| `flowyml_notebook.diff` | Notebook comparison |
| `flowyml_notebook.snippets` | Code snippet library |
| `flowyml_notebook.cell_deps` | Cell dependency analysis |
| `flowyml_notebook.search` | Full-text notebook search |

