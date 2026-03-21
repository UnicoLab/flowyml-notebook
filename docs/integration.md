# 🔗 FlowyML Integration

FlowyML Notebook is deeply integrated with the centralized **FlowyML Service**, providing a "Single Pane of Glass" for ML engineering.

## Connecting to an Instance

Connect your local notebook to a remote FlowyML instance using an API token:

```bash
fml-notebook start --server https://flowyml.your-org.ai
```

Or configure it via the **Connection** panel in the GUI.

## Remote Execution & Scheduling

- **Server-Side Runs**: Submit your notebook to execute on remote compute nodes.
- **Cron Scheduling**: Schedule notebooks to run daily, weekly, or on custom intervals directly from the interface.
- **Pipeline Promotion**: Promote any notebook to a production-grade FlowyML pipeline with a single click.

## Asset Management

Access the centralized **Asset Catalog** directly within your cells:
- **Datasets**: Import versioned datasets with built-in lineage tracking.
- **Models**: Pull models from the Model Registry for evaluation or fine-tuning.
- **Metrics**: Log experiment metrics directly to the FlowyML dashboard.

## Deployment

Deploy models trained in your notebook to the FlowyML inference service:
```python
# In a notebook cell
nb.deploy(model_name="my_model", endpoint="fraud-detection-v1")
```
This automatically packages the model, sets up the endpoint, and provides a production-ready URL.
