# ⚡ Getting Started

## Installation

FlowyML Notebook requires **Python 3.10+**.

```bash
# Core package
pip install flowyml-notebook

# With ML & AI extensions (Recommended)
pip install "flowyml-notebook[all]"
```

## Launching the Notebook

To start the local development server:

```bash
fml-notebook start
```

This will automatically open your default browser to `http://localhost:8880`.

## Your First Reactive Notebook

1.  Click **New Notebook** in the dashboard.
2.  Add a Python cell: `x = 10`.
3.  Add another cell: `print(x * 2)`.
4.  Change `x = 20` in the first cell.
5.  Watch the second cell automatically update!
