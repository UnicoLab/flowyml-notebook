# ✨ Key Features

FlowyML Notebook is a complete ML development environment. Here's a comprehensive overview of everything it offers.

## 🔄 Reactive Execution DAG

Unlike traditional Jupyter notebooks, FlowyML Notebook treats cells as nodes in a Directed Acyclic Graph. When a variable changes, only the downstream dependent cells are re-executed — no more stale state.

- Automatic dependency detection via AST analysis
- Visual DAG representation in the sidebar
- Parallel execution of independent branches
- Execution status tracking per cell

## 📄 Pure Python Storage

Notebooks are saved as standard `.py` files with special decorators:

- **Git Friendly**: Clean diffs, no JSON noise
- **Importable**: Use notebook logic directly in production scripts
- **Lintable**: Run `ruff`, `flake8`, or `mypy` on your notebooks

```python
# @cell(id="load_data")
import pandas as pd
df = pd.read_csv("data.csv")

# @cell(id="transform", depends=["load_data"])
df_clean = df.dropna()
```

## 🎛️ Interactive UI Widgets

Bind Python variables to professional-grade UI controls:

```python
@fml.input
def learning_rate(value=0.001):
    return value
```

Supports sliders, text inputs, dropdowns, toggles, date pickers, and color pickers.

## 🤖 AI Contextual Assistant

The integrated AI assistant understands the full FlowyML SDK and your notebook context:

- Generate entire pipeline segments from natural language
- Debug execution errors with context-aware suggestions
- Explain complex data patterns from DataFrame outputs

## 📊 SQL First-Class Support

Mix Python and SQL seamlessly. SQL results are automatically converted to Polars/Pandas DataFrames:

```sql
-- @cell(type="sql")
SELECT * FROM df_clean WHERE age > 30
```

See [Data Exploration](exploration.md) for how SQL results are displayed.

## 📈 Rich Data Exploration

Every DataFrame output gets an interactive data profile. See [Data Exploration](exploration.md) for full details:

- Bento-grid summary deck (rows, columns, nulls, memory)
- Automated histograms with animated visualizations
- Correlation heatmaps and scatter plots
- ML insights (feature types, outlier detection, algorithm suggestions)

## 🧾 Recipes

Reusable cell templates for common ML tasks. See [Recipes](recipes.md) for details:

- Built-in recipes for data loading, preprocessing, training, and evaluation
- Create custom recipes from any cell
- Share recipes via GitHub Hub

## 🤝 Team Collaboration

Full Git-based collaboration without a database. See [Collaboration](collaboration.md):

- GitHub-backed `.flowyml-hub` repository
- Branch-based workflows
- Recipe sharing and versioning

## 🔗 FlowyML Integration

Connect to centralized FlowyML instances. See [Integration](integration.md):

- Remote execution and scheduling
- Asset management and model registry
- One-click pipeline promotion

## 🚀 Deployment & Export

Turn notebooks into production artifacts:

| Format | Command | Use Case |
|---|---|---|
| FlowyML Pipeline | `fml-notebook export --format pipeline` | Production ML pipelines |
| HTML Report | `fml-notebook export --format html` | Shareable dashboards |
| PDF Report | `fml-notebook export --format pdf` | Documentation |
| Docker Image | `fml-notebook export --format docker` | Containerized deployment |
| Web App | `fml-notebook app notebook.py` | Interactive applications |

## 📊 Reporting

Generate rich HTML dashboards and PDF reports with embedded visualizations, charts, and DataFrame insights. Reports include:

- Interactive charts and tables
- ML observability metrics
- Executive summaries
