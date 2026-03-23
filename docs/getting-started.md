# ⚡ Getting Started

Get up and running with FlowyML Notebook in **under 60 seconds**. No Docker, no cloud signup, no configuration needed.

---

## Installation

=== "pip"

    ```bash
    # Recommended: install with all ML & AI extensions
    pip install "flowyml-notebook[all]"
    ```

=== "poetry"

    ```bash
    poetry add "flowyml-notebook[all]"
    ```

!!! tip "Minimal Install"
    Just need the core notebook? Run `pip install flowyml-notebook` — you can add extras later.

### What's Included

| Package | What You Get |
|---------|-------------|
| **Core** | Reactive DAG engine, editor, recipes, reports, app publishing |
| `[ai]` | :robot: AI assistant (OpenAI & Google Generative AI) |
| `[sql]` | :floppy_disk: SQL cells with DuckDB & SQLAlchemy |
| `[exploration]` | :mag: Advanced DataFrame profiling with ML insights |
| `[all]` | :package: Everything above — **recommended** |

---

## Launch

```bash
fml-notebook start
```

That's it. Your browser opens to `http://localhost:8880` and you're ready to build.

<figure markdown>
  ![FlowyML Notebook Editor](screenshots/notebook.png){ width="100%" }
  <figcaption>The FlowyML Notebook editor — reactive cells, variable explorer, and integrated toolbar</figcaption>
</figure>

### CLI Options

```bash
fml-notebook start --port 9000      # Custom port
fml-notebook start --no-browser     # Don't auto-open browser
fml-notebook dev                    # Hot-reload mode (for contributors)
```

---

## Your First Reactive Notebook

### 1. Start with Data

Click **Demo** in the toolbar to load a full end-to-end example, or add cells manually:

```python
# Cell 1 — Generate ML experiment data
import pandas as pd
import numpy as np

df = pd.DataFrame({
    'model': np.random.choice(['XGBoost', 'LightGBM', 'SVM', 'Neural Net'], 100),
    'accuracy': np.random.uniform(0.72, 0.98, 100).round(4),
    'f1_score': np.random.uniform(0.68, 0.96, 100).round(4),
    'training_time_s': np.random.exponential(30, 100).round(2),
})
df
```

### 2. Get Instant Insights

Every DataFrame automatically gets **rich profiling** — statistics, charts, correlations, and ML recommendations:

<figure markdown>
  ![Automatic Data Profiling](screenshots/pandas-display2.png){ width="100%" }
  <figcaption>Charts tab: histogram distributions for every column, automatically generated</figcaption>
</figure>

<figure markdown>
  ![ML Insights](screenshots/recommendations.png){ width="100%" }
  <figcaption>Insights tab: outlier detection, scaling recommendations, and target variable identification</figcaption>
</figure>

### 3. Experience Reactivity

```python
# Cell 2 — This re-executes automatically when Cell 1 changes!
summary = df.groupby('model').agg(
    avg_accuracy=('accuracy', 'mean'),
    avg_f1=('f1_score', 'mean'),
    count=('model', 'count'),
).round(4).sort_values('avg_accuracy', ascending=False)
summary
```

Change anything in Cell 1 → Cell 2 **automatically re-executes**. :zap:

That's the power of the reactive DAG engine. No stale state. No "restart and run all."

### 4. Visualize Dependencies

Open the **DAG** tab to see how your cells connect:

<figure markdown>
  ![DAG View](screenshots/dag.png){ width="60%" }
  <figcaption>Visual dependency graph: imports → data_generation → analysis → exploration → summary</figcaption>
</figure>

### 5. Ship to Production

When you're happy with your analysis:

- :page_facing_up: **Export Report** — Generate HTML/PDF with one click
- :globe_with_meridians: **Publish as App** — Turn it into an interactive web dashboard
- :rocket: **Promote to Pipeline** — Convert to a production FlowyML pipeline

<figure markdown>
  ![Publish as App](screenshots/apps.png){ width="50%" }
  <figcaption>Choose layout, theme, and cell visibility — then publish with one click</figcaption>
</figure>

---

## Connect to FlowyML (Optional)

For experiment tracking, model registry, and pipeline deployment, connect to a FlowyML instance:

<figure markdown>
  ![Environment](screenshots/flowy-connection.png){ width="50%" }
  <figcaption>Local mode works standalone — switch to Remote for full platform features</figcaption>
</figure>

```bash
fml-notebook start --server https://flowyml.your-org.ai
```

Or configure from the **Env** panel in the sidebar.

---

## What's Next?

| Explore | Description |
|---------|-------------|
| :sparkles: [Features](features.md) | Complete visual tour of every capability |
| :cook: [Recipes](recipes.md) | 39 built-in code templates for ML workflows |
| :handshake: [Collaboration](collaboration.md) | GitHub-powered team workflows |
| :electric_plug: [Integration](integration.md) | Pipelines, deploy, and asset management |
| :mag: [Data Exploration](exploration.md) | Deep dive into DataFrame profiling |

!!! info "Need Help?"
    - :bug: [Bug Reports](https://github.com/UnicoLab/flowyml-notebook/issues)
    - :speech_balloon: [Discussions](https://github.com/UnicoLab/flowyml-notebook/discussions)
