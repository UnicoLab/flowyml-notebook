# 🌊 FlowyML Notebook

Welcome to the official documentation for **FlowyML Notebook** — the production-grade reactive notebook for ML pipelines.

FlowyML Notebook replaces traditional Jupyter environments with a robust, pure-Python execution engine that treats cells as a Directed Acyclic Graph (DAG). Every variable change automatically propagates through the graph, ensuring your results are always consistent.

## Why FlowyML Notebook?

- **Reactivity by Default**: No more "out-of-order execution" headaches.
- **Git Perfection**: Notebooks are saved as standard `.py` files — no JSON diffs.
- **Production Ready**: One-click deployment as a standalone app or scheduled job.
- **Deep Integration**: Built specifically for the FlowyML ecosystem.
- **Team Collaboration**: GitHub-based workflows with branching, versioning, and recipe sharing.

## Documentation Overview

| Section | Description |
|---|---|
| [Getting Started](getting-started.md) | Install, launch, and create your first notebook |
| [Key Features](features.md) | Complete feature inventory |
| [Architecture](architecture.md) | System design, DAG engine, and file format |
| [Recipes](recipes.md) | Create, share, and manage reusable cell templates |
| [Collaboration](collaboration.md) | GitHub-based team workflows |
| [FlowyML Integration](integration.md) | Connect to FlowyML instances for remote execution |
| [Data Exploration](exploration.md) | Rich DataFrame profiling and ML insights |
| [API Reference](api.md) | CLI commands and Python API |

## Quick Start

```bash
pip install "flowyml-notebook[all]"
fml-notebook start
```

Your browser opens to `http://localhost:8880` — start building reactive notebooks immediately.
