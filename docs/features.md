# ✨ Key Features

FlowyML Notebook is designed for production ML workflows, focusing on stability, observability, and ease of use.

## 🔄 Reactive Execution DAG
Unlike traditional Jupyter notebooks, FlowyML Notebook treats cells as nodes in a Directed Acyclic Graph. When a variable changes, only the downstream dependent cells are re-executed.

## 📄 Pure Python Storage
Notebooks are saved as standard `.py` files with special decorators. 
- **Git Friendly**: No more complex JSON diffs.
- **Importable**: Use your notebook logic directly in other Python scripts.
- **Lintable**: Run `ruff` or `flake8` on your notebooks.

## 🎛️ Interactive UI Widgets
Easily bind variables to UI components:
```python
@fml.input
def learning_rate(value=0.001):
    return value
```
The notebook automatically renders a slider/input for `learning_rate`.

## 🤖 AI Contextual Assistant
The integrated AI assistant is trained on the FlowyML SDK and can help you generate entire pipeline segments or debug execution errors.

## 📊 SQL first-class support
Mix Python and SQL seamlessly. SQL results are automatically converted to Polars/Pandas DataFrames for immediate analysis.
