# 🏗️ Architecture

FlowyML Notebook is a full-stack application with a Python backend, React frontend, and a reactive execution engine at its core.

<figure markdown>
  ![Pipeline DAG View](screenshots/dag.png){ width="60%" }
  <figcaption>Live DAG visualization of cell dependencies with execution state indicators</figcaption>
</figure>

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Editor   │  │ Sidebar  │  │ DataFrame   │  │ DAG View    │  │
│  │ (Monaco) │  │ & Nav    │  │ Explorer    │  │ (ReactFlow) │  │
│  └──────────┘  └──────────┘  └─────────────┘  └─────────────┘  │
│                      React + Vite                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ WebSocket + REST API
┌─────────────────────────┴───────────────────────────────────────┐
│                      FastAPI Server                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Cell Mgmt    │  │ File I/O     │  │ GitHub Sync        │    │
│  │ API          │  │ (notebooks)  │  │ (Collaboration)    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ AI Assistant │  │ Recipes      │  │ FlowyML Connector  │    │
│  │ API          │  │ Store        │  │ (Remote Exec)      │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Core Engine                                │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │  Python Kernel   │  │  Reactive Graph (DAG)            │    │
│  │  (IPython-based) │  │  ┌─────┐  ┌─────┐  ┌─────┐     │    │
│  │                  │  │  │ A   │──│ B   │──│ C   │     │    │
│  │  - Cell exec     │  │  └─────┘  └──┬──┘  └─────┘     │    │
│  │  - Namespace     │  │              │                   │    │
│  │  - Auto-imports  │  │  ┌─────┐  ┌──┴──┐               │    │
│  │  - SQL engine    │  │  │ D   │──│ E   │               │    │
│  │                  │  │  └─────┘  └─────┘               │    │
│  └──────────────────┘  └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Reactive Execution Engine

The heart of FlowyML Notebook is the **ReactiveGraph** — a DAG that tracks which cells read and write which variables.

### How It Works

1. **Parse**: When a cell is created or modified, the engine performs AST analysis on the source code to detect variable reads and writes.
2. **Graph Update**: The dependency graph is updated with the new read/write sets.
3. **Propagate**: When a cell is executed, the engine identifies all downstream dependents via topological sort.
4. **Execute**: Dependent cells are re-executed in dependency order, skipping any cells whose inputs haven't changed.

### Execution States

| State | Meaning |
|---|---|
| `idle` | Cell is up-to-date |
| `stale` | An upstream dependency has changed; needs re-execution |
| `running` | Cell is currently executing |
| `error` | Last execution produced an error |
| `disabled` | Cell is excluded from the reactive graph |

## File Format

Notebooks are stored as standard Python files (`.py`) with metadata encoded in decorators and comments:

```python
# FlowyML Notebook: my_analysis
# Version: 1
# Created: 2026-03-21

# @cell(id="imports", name="Setup")
import pandas as pd
import numpy as np

# @cell(id="load", name="Load Data", depends=["imports"])
df = pd.read_csv("data.csv")
print(f"Loaded {len(df)} rows")

# @cell(id="clean", name="Clean Data", depends=["load"])
df_clean = df.dropna()
```

### Benefits

- **Version Control**: Clean `git diff` output
- **Importable**: `from my_notebook import df_clean`
- **Lintable**: Works with `ruff`, `flake8`, `mypy`
- **IDE Support**: Full syntax highlighting and autocompletion

## Frontend Architecture

The frontend is a React application built with Vite:

| Component | Purpose |
|---|---|
| `App.jsx` | Main layout with resizable panels |
| `CellEditor` | Monaco-based code editor per cell |
| `CellOutput` | Renders all output types (text, charts, DataFrames) |
| `DataFrameExplorer` | Interactive data profiling with tabs |
| `PipelineDAG` | ReactFlow-based dependency visualization |
| `Sidebar` | Navigation, file tree, recipes, settings |
| `ConnectionConfig` | FlowyML instance connection UI |

### Key Dependencies

| Library | Purpose |
|---|---|
| React 18 | UI framework |
| Vite | Build tool with HMR |
| ReactFlow | DAG visualization |
| Recharts | Chart rendering |
| Framer Motion | Animations |
| Lucide React | Icon system |

## Extension Points

### Custom Cell Types

In addition to Python and SQL, the cell system can be extended with new types by implementing the `CellType` enum and registering a handler in the kernel.

### Recipe Plugins

Custom recipes can be added to the `recipes_store` to provide domain-specific templates (e.g., NLP preprocessing, time series, computer vision).

### AI Providers

The AI assistant supports multiple backends (OpenAI, Google Generative AI) and can be extended with custom providers.
