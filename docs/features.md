# ✨ Features

FlowyML Notebook is a complete ML development environment. Here's everything it offers — with real screenshots from the application.

---

## :arrows_counterclockwise: Reactive DAG Engine

Every cell is a node in a **dependency graph**. When a variable changes, only dependent cells re-execute — no more stale state, no more "restart kernel and run all."

- Automatic dependency detection via AST analysis
- Visual DAG representation with cell status indicators
- Topological execution order for consistent results
- Parallel execution of independent branches

<figure markdown>
  ![Pipeline DAG View](screenshots/dag.png){ width="70%" }
  <figcaption>Pipeline DAG: imports → data_generation → analysis → exploration → summary</figcaption>
</figure>

---

## :page_facing_up: Pure Python Storage

Notebooks are saved as standard `.py` files. No JSON, no merge conflicts, no diffs you can't read.

- **Git Friendly** — Clean `git diff`, meaningful `git blame`
- **Importable** — `from my_notebook import df_clean`
- **Lintable** — Works with `ruff`, `flake8`, `mypy`

```python
# @cell(id="load_data")
import pandas as pd
df = pd.read_csv("data.csv")

# @cell(id="transform", depends=["load_data"])
df_clean = df.dropna()
```

---

## :bar_chart: Rich Data Exploration

Every DataFrame gets **automatic profiling** — zero extra code. Toggle between Table, Stats, Charts, Correlations, Quality, Insights, Compare, and AI views.

<figure markdown>
  ![Data Stats](screenshots/pandas-display.png){ width="100%" }
  <figcaption>Automatic DataFrame profiling with column statistics, type detection, and memory impact</figcaption>
</figure>

<figure markdown>
  ![Data Charts](screenshots/pandas-display2.png){ width="100%" }
  <figcaption>Interactive charts: histograms, bar charts, and distribution analysis for every column</figcaption>
</figure>

<figure markdown>
  ![Correlations](screenshots/pangas-display3.png){ width="100%" }
  <figcaption>Pearson correlation matrix with color-coded heatmap</figcaption>
</figure>

<figure markdown>
  ![ML Insights](screenshots/recommendations.png){ width="100%" }
  <figcaption>Automated ML insights: outlier detection, scaling recommendations, and target variable suggestions</figcaption>
</figure>

See [Data Exploration](exploration.md) for the full breakdown.

---

## :robot: AI Assistant

Integrated AI assistant (`⌘J`) with deep FlowyML ecosystem knowledge. The assistant is **context-aware** — it sees your notebook state, cell outputs, variable values, and error tracebacks.

- **Generate** — Create pipeline segments, data transformations, or visualizations from natural language
- **Explain** — Understand complex data patterns from outputs and profiling results
- **Debug** — Context-aware error resolution with stack trace analysis
- **Optimize** — Performance tuning, scaling recommendations, and ML hyperparameter suggestions

### Supported Providers

| Provider | Models | Setup |
|----------|--------|-------|
| **OpenAI** | GPT-4o, GPT-4o-mini | `OPENAI_API_KEY` env variable |
| **Google AI** | Gemini Pro, Gemini Ultra | `GOOGLE_API_KEY` env variable |

### Usage Examples

```
# In the AI chat panel:
> Load a CSV, clean missing values, and plot the distribution of 'revenue'
> Why did cell 3 fail with a KeyError?
> Optimize this XGBoost model for better F1 score
> Write a FlowyML pipeline step that processes this DataFrame
```

The AI assistant generates code that respects the reactive DAG — it understands which variables are available from upstream cells and avoids creating stale dependencies.

---

## :speech_balloon: Comments & Review

Collaborate directly in the notebook with **inline comments**. Add notebook-level or cell-level annotations for team discussions, with resolve/reply threading.

<figure markdown>
  ![Comments Panel](screenshots/comments.png){ width="100%" }
  <figcaption>Comments panel with threaded discussions alongside code and outputs</figcaption>
</figure>

---

## :cook: Recipes — Reusable Templates

**39 built-in recipes** across Core, Assets, Parallel, Observability, Evals, Data, ML, and Visualization categories. Drag into your notebook or click `+` to insert.

<figure markdown>
  ![Recipes Panel](screenshots/recipies.png){ width="60%" }
  <figcaption>Searchable recipe library with FlowyML Step, Pipeline, Conditional Branching, and more</figcaption>
</figure>

See [Recipes](recipes.md) for the full cookbook.

---

## :page_with_curl: Reports

Generate beautiful **dark-themed HTML reports** from your notebook with one click. Reports include styled tables with inline SVG histograms, correlation badges, and formatted outputs.

<figure markdown>
  ![Generate Report](screenshots/reports.png){ width="50%" }
  <figcaption>One-click report generation with HTML/PDF format, code inclusion, and browser preview</figcaption>
</figure>

### Report Features

- **Dark-themed** — Premium dark UI with Inter + JetBrains Mono fonts
- **DataFrame rendering** — Auto-generated stat cards, SVG histograms, and categorical bar charts inline
- **Code toggle** — Optionally include source code alongside outputs
- **Markdown cells** — Rendered as formatted headings, lists, and paragraphs
- **CLI export** — `fml-notebook export notebook.py --format html --output report.html`

### Via Python API

```python
from flowyml_notebook.reporting import generate_report

generate_report(
    notebook=nb,
    format="html",         # or "pdf"
    include_code=False,    # Show outputs only
    title="Monthly Fraud Analysis",
    output_path="report.html",
)
```

---

## :globe_with_meridians: Publish as App

Turn any notebook into an **interactive web application** with one click. Choose your layout, toggle cell visibility, and deploy:

<figure markdown>
  ![Publish as App](screenshots/apps.png){ width="50%" }
  <figcaption>App publishing with layout options, dark/light theme, and per-cell visibility control</figcaption>
</figure>

### Layout Options

| Layout | Description |
|--------|------------|
| **Linear** | Cells stacked vertically — classic report layout |
| **Grid** | Responsive grid — cells arranged in columns |
| **Tabs** | Each cell is a tab — ideal for dashboards |
| **Sidebar** | Input controls in sidebar, outputs in main area |
| **Dashboard** | Full dashboard mode with widgets and charts |

### Via CLI

```bash
fml-notebook app my_notebook.py --layout dashboard --port 8501
```

Widgets (sliders, dropdowns, toggles) become interactive controls in the deployed app — users can tweak parameters and see results update in real time.

---

## :rocket: Production — Pipelines, Deploy & Assets

Ship notebooks directly to production:

=== "Pipelines"

    Promote notebooks to production FlowyML pipelines with `@step` decorators.

    <figure markdown>
      ![Pipelines Panel](screenshots/pipelines.png){ width="50%" }
      <figcaption>Pipeline promotion with quick actions: Export, Run All, View DAG, HTML Report</figcaption>
    </figure>

=== "Deploy"

    Deploy as REST API, Docker Container, or Batch Pipeline — with full FlowyML infrastructure stack integration.

    <figure markdown>
      ![Deploy Panel](screenshots/deploy.png){ width="50%" }
      <figcaption>Production deployment: API (recommended), Docker, Batch Pipeline, plus infrastructure stacks</figcaption>
    </figure>

=== "Assets"

    Track kernel assets (DataFrames, models) with size, shape, and type metadata.

    <figure markdown>
      ![Assets Panel](screenshots/assets.png){ width="50%" }
      <figcaption>Kernel assets: tracked DataFrames with size, rows × cols, and type tags</figcaption>
    </figure>

---

## :handshake: Git & Version Control

Full **GitHub integration** as the collaboration backend. No proprietary cloud, no database — just Git.

<figure markdown>
  ![GitHub Integration](screenshots/github.png){ width="50%" }
  <figcaption>Connect GitHub repository for team collaboration, versioning, and shared recipes</figcaption>
</figure>

<figure markdown>
  ![History & Snapshots](screenshots/snapshots.png){ width="50%" }
  <figcaption>Save and browse notebook snapshots with cell-level diffs</figcaption>
</figure>

See [Collaboration](collaboration.md) for the full workflow.

---

## :gear: Environment & Connection

Run **standalone** in Local Mode or connect to a **remote FlowyML server** for experiment tracking, pipeline export, and deployment.

<figure markdown>
  ![Environment Panel](screenshots/flowy-connection.png){ width="50%" }
  <figcaption>Local/Remote connection, Python 3.12 runtime, IPython kernel, Reactive DAG engine</figcaption>
</figure>

See [Integration](integration.md) for connection details.

---

## :floppy_disk: SQL First-Class

Mix Python and SQL seamlessly in the same notebook. SQL cells are powered by **DuckDB** (in-memory, zero config) or **SQLAlchemy** (for external databases).

```sql
-- @cell(type="sql")
SELECT model, AVG(accuracy) as avg_acc, COUNT(*) as n
FROM df_experiments
WHERE accuracy > 0.85
GROUP BY model
ORDER BY avg_acc DESC
```

### How It Works

- SQL cells **query your Python DataFrames** directly — any variable holding a DataFrame is available as a table name
- Results are automatically converted to Pandas/Polars DataFrames
- The result DataFrame is assigned to a variable and participates in the reactive DAG
- Supports **DuckDB** (default, in-process) and **SQLAlchemy** (PostgreSQL, MySQL, SQLite, etc.)

### External Databases

```sql
-- @cell(type="sql", connection="postgresql://user:pass@host/db")
SELECT * FROM users WHERE created_at > '2026-01-01'
```

---

## :control_knobs: Interactive Widgets

Bind Python variables to **professional-grade UI controls** — sliders, dropdowns, toggles, date pickers, color pickers, text inputs, and more.

```python
import flowyml_notebook.ui as fml

# Slider with range and step
learning_rate = fml.slider("Learning Rate", min=0.0001, max=0.1, step=0.0001, default=0.001)

# Dropdown selection
model_type = fml.select("Model", options=["XGBoost", "LightGBM", "SVM", "Neural Net"])

# Toggle switch
use_augmentation = fml.toggle("Data Augmentation", default=True)

# Number input
n_estimators = fml.number("Trees", min=10, max=1000, default=100)
```

### Widget Reactivity

Widgets participate in the reactive DAG — when a user changes a slider value, all downstream cells automatically re-execute. This is what powers the **Publish as App** feature: your notebook becomes a live, interactive dashboard.

### Available Widgets

| Widget | Description | Code |
|--------|------------|------|
| **Slider** | Numeric range | `fml.slider(...)` |
| **Select** | Dropdown menu | `fml.select(...)` |
| **Toggle** | Boolean switch | `fml.toggle(...)` |
| **Number** | Numeric input | `fml.number(...)` |
| **Text** | Text input | `fml.text(...)` |
| **Date** | Date picker | `fml.date_picker(...)` |
| **Color** | Color picker | `fml.color(...)` |
| **File** | File upload | `fml.file_upload(...)` |

---

## Deployment & Export

| Format | Command | Use Case |
|---|---|---|
| FlowyML Pipeline | `fml-notebook export --format pipeline` | Production ML pipelines |
| HTML Report | `fml-notebook export --format html` | Shareable dashboards |
| PDF Report | `fml-notebook export --format pdf` | Documentation |
| Docker Image | `fml-notebook export --format docker` | Containerized deployment |
| Web App | `fml-notebook app notebook.py` | Interactive applications |
