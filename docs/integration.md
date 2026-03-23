# :electric_plug: FlowyML Integration

FlowyML Notebook integrates with the centralized **FlowyML Platform** — giving you production deployment, experiment tracking, pipeline management, and scheduling directly from your notebook.

---

## Connection Modes

<figure markdown>
  ![Environment Panel](screenshots/flowy-connection.png){ width="50%" }
  <figcaption>Local/Remote connection mode with runtime details and auto-connect option</figcaption>
</figure>

| Mode | How It Works | Best For |
|------|-------------|----------|
| :orange_circle: **Local** | Standalone — no server needed | Solo development, exploration |
| :globe_with_meridians: **Remote** | Connected to a FlowyML instance | Team deployment, experiment tracking |

### Connecting to FlowyML

=== "CLI"

    ```bash
    fml-notebook start --server https://flowyml.your-org.ai
    ```

=== "Environment Variable"

    ```bash
    export FLOWYML_API_TOKEN="your-api-token"
    fml-notebook start --server https://flowyml.your-org.ai
    ```

=== "Python API"

    ```python
    from flowyml_notebook import FlowyMLConnection

    conn = FlowyMLConnection(
        server_url="https://flowyml.your-org.ai",
        token="your-api-token",
    )
    conn.connect()
    # → Connected to FlowyML server (version: 1.8.0)
    ```

=== "GUI"

    Open **Env** panel → Switch to **Remote** → Enter server URL → **Test Connection** → **Save**

!!! tip "Context Manager"
    Use `FlowyMLConnection` as a context manager for automatic cleanup:
    ```python
    with FlowyMLConnection("https://flowyml.your-org.ai") as conn:
        pipelines = conn.list_pipelines()
    ```

---

## Production Pipelines

Promote any notebook to a production-grade Python pipeline with one click.

<figure markdown>
  ![Pipelines Panel](screenshots/pipelines.png){ width="50%" }
  <figcaption>Quick actions (Export, Run All, View DAG, Report) and "Promote Notebook → Pipeline"</figcaption>
</figure>

### How Pipeline Promotion Works

When you promote a notebook, FlowyML:

1. **Extracts** all code cells in topological (DAG) order
2. **Hoists imports** to the top of the file
3. **Converts markdown** cells to docstrings and comments
4. **Adds** a `__main__` guard for standalone execution
5. **Generates** a clean, linted `.py` file

```python
# Generated output: my_analysis_pipeline.py
"""Production pipeline: my_analysis

Auto-generated from FlowyML Notebook.
Generated at: 2026-03-23T15:00:00
"""

import numpy as np
import pandas as pd

# Data loading
df = pd.read_csv("data.csv")

# Feature engineering
df["ratio"] = df["revenue"] / df["cost"]

if __name__ == "__main__":
    print("Running pipeline: my_analysis")
```

### Via CLI

```bash
fml-notebook export my_notebook.py --format pipeline --output production.py
```

!!! info "Export Formats"
    | Format | Output |
    |--------|--------|
    | `pipeline` | Clean `.py` file with hoisted imports |
    | `html` | Rich HTML report (dark theme, styled tables) |
    | `docker` | Dockerfile + pipeline + requirements.txt |

---

## Model Deployment

Deploy trained models directly from your notebook to FlowyML Serving:

<figure markdown>
  ![Deploy Panel](screenshots/deploy.png){ width="50%" }
  <figcaption>Deploy as API (recommended), Docker Container, or Batch Pipeline</figcaption>
</figure>

### Deploy as API

```python
from flowyml_notebook.deployer import deploy_model

# Train your model in the notebook
model = train_xgboost(df)

# Deploy to FlowyML serving
result = deploy_model(
    model=model,
    endpoint="fraud-detection-v2",
    connection=conn,
)
# → {"model_name": "xgboost_fraud", "endpoint": "fraud-detection-v2", "status": "deployed"}
```

### Deploy as Docker Container

Generate a production-ready Dockerfile from your notebook:

```python
from flowyml_notebook.deployer import generate_dockerfile

generate_dockerfile(
    notebook=nb,
    output_path="Dockerfile",
    base_image="python:3.11-slim",
)
```

This generates:
- `Dockerfile` — Multi-stage build with your pipeline
- `requirements.txt` — Auto-detected dependencies
- `{name}_pipeline.py` — Extracted production code

---

## Asset Management

Track kernel assets (DataFrames, models, artifacts) with metadata — size, shape, and type tags.

<figure markdown>
  ![Assets Panel](screenshots/assets.png){ width="50%" }
  <figcaption>Kernel assets: df (23 KB, 100×11), top_experiments (3.8 KB, 16×11), summary (657 B, 5×5)</figcaption>
</figure>

### Remote Asset Catalog

When connected to FlowyML, query the centralized asset catalog:

```python
# List all tracked assets
assets = conn.list_assets(asset_type="model")

# Get asset details including lineage
model_info = conn.get_asset("fraud-model-v2")
```

---

## Experiment Tracking

Track experiments across notebooks with the FlowyML experiment API:

```python
# List all experiments
experiments = conn.list_experiments()

# Get specific experiment details (metrics, params, artifacts)
exp = conn.get_experiment("experiment-id")
```

---

## Scheduling

Schedule notebooks for periodic execution:

```python
# Create a daily schedule
conn.create_schedule({
    "name": "daily-fraud-report",
    "pipeline_name": "fraud_detection",
    "cron": "0 8 * * *",   # Every day at 8am
    "enabled": True,
})

# List all schedules
schedules = conn.list_schedules()

# Delete a schedule
conn.delete_schedule("daily-fraud-report")
```

---

## Remote Execution

Submit notebooks for execution on remote compute nodes:

```python
# Submit a pipeline for remote execution
result = conn.submit_pipeline({
    "pipeline_data": notebook_data,
    "compute": "gpu-large",
})

# Check execution status
status = conn.get_execution_status(result["execution_id"])
```

---

## Full API Reference

For the complete `FlowyMLConnection` API, see the [API Reference](api.md).

| Category | Endpoints |
|----------|----------|
| **Pipelines** | `list_pipelines()`, `get_pipeline(id)` |
| **Runs** | `list_runs()`, `get_run(id)` |
| **Assets** | `list_assets()`, `get_asset(id)` |
| **Experiments** | `list_experiments()`, `get_experiment(id)` |
| **Schedules** | `create_schedule()`, `list_schedules()`, `delete_schedule()` |
| **Deployments** | `create_deployment()`, `list_deployments()` |
| **Execution** | `submit_pipeline()`, `get_execution_status(id)` |
| **Metrics** | `get_metrics()` |
| **Config** | `get_config()` |
