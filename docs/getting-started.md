# ⚡ Getting Started

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10 | 3.12 |
| Node.js | 18 | 20+ |
| Git | 2.30+ | Latest |
| OS | macOS, Linux, Windows (WSL) | macOS / Linux |

## Installation

```bash
# Core package
pip install flowyml-notebook

# With all extensions (AI, SQL, Exploration) — Recommended
pip install "flowyml-notebook[all]"
```

### Optional Extras

| Extra | What It Adds |
|---|---|
| `ai` | OpenAI & Google Generative AI for the AI assistant |
| `sql` | DuckDB & SQLAlchemy for SQL cells |
| `exploration` | SciPy & Scikit-learn for advanced DataFrame profiling |
| `docs` | MkDocs & Material theme for building documentation |
| `all` | Everything above |

## Launching the Notebook

```bash
# Production mode (pre-built frontend)
fml-notebook start

# Development mode with hot reload
fml-notebook dev
```

This will automatically open your default browser to `http://localhost:8880`.

### CLI Options

```bash
fml-notebook start --port 9000          # Custom port
fml-notebook start --no-browser         # Don't auto-open
fml-notebook dev --backend-port 8888    # Custom API port
fml-notebook dev --frontend-port 3000   # Custom Vite port
```

## Your First Reactive Notebook

1. Click **New Notebook** in the dashboard.
2. Add a Python cell:
   ```python
   x = 10
   ```
3. Add a second cell:
   ```python
   result = x * 2
   print(f"Result: {result}")
   ```
4. Change `x = 20` in the first cell.
5. Watch the second cell **automatically re-execute** — that's reactivity!

## Project Structure

When you create a notebook, FlowyML saves it as a plain `.py` file:

```
my_project/
├── notebook.py          # Your notebook (Git-friendly!)
├── .flowyml-hub/        # Collaboration data (if using GitHub sync)
│   ├── recipes/         # Shared recipes
│   └── config.json      # Hub configuration
└── assets/              # Generated charts, reports
```

## Configuration

### Connecting to a FlowyML Instance

```bash
fml-notebook start --server https://your-flowyml-instance.com
```

Or configure within the notebook UI via the **Connection** panel in the sidebar.

## Troubleshooting

### Common Issues

| Problem | Solution |
|---|---|
| Port already in use | Use `--port <number>` to pick a different port |
| Frontend not loading | Run `make build` to rebuild the frontend |
| `ModuleNotFoundError: flowyml` | Install the FlowyML SDK: `pip install flowyml` |
| Permission denied | Ensure you're not running in a restricted directory |

### Getting Help

- 📖 [Documentation](https://docs.flowyml.ai/notebook)
- 🐛 [Bug Reports](https://github.com/UnicoLab/FlowyML-Notebook/issues)
- 💬 [Discussions](https://github.com/UnicoLab/FlowyML-Notebook/discussions)
