<p align="center">
  <img src="assets/logo.png" alt="FlowyML Notebook Logo" width="300">
</p>

# 🌊 FlowyML Notebook

<p align="center">
  <strong>The Production-Grade Reactive Notebook for ML Pipelines</strong>
</p>

<p align="center">
  <a href="https://github.com/UnicoLab/flowyml-notebook/actions/workflows/tests.yml"><img src="https://github.com/UnicoLab/flowyml-notebook/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://docs.flowyml.ai/notebook"><img src="https://img.shields.io/badge/docs-MkDocs-blue.svg" alt="Documentation"></a>
  <a href="https://pypi.org/project/flowyml-notebook/"><img src="https://img.shields.io/pypi/v/flowyml-notebook" alt="PyPI Version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
</p>

---

**FlowyML Notebook** is a high-fidelity, reactive execution environment built specifically for machine learning engineering. It replaces traditional Jupyter notebooks with a pure-Python, DAG-based engine that ensures your code is always production-ready.

## ✨ Why FlowyML?

Traditional notebooks are great for exploration but terrible for production. FlowyML Notebook bridges this gap by offering:

- **🔄 Reactive Execution** — Cells are nodes in a Directed Acyclic Graph (DAG). Changing a variable automatically triggers re-execution of only dependent cells.
- **📄 Git-Native** — Notebooks are stored as human-readable `.py` files. No more JSON diff nightmares or hidden state.
- **🎛️ Interactive Instruments** — Professional-grade UI widgets (sliders, plots, inputs) bound directly to Python variables.
- **🤖 AI Intelligence** — Integrated assistant with deep knowledge of the Flowml ecosystem.
- **📊 SQL First-Class** — Transition seamlessly between Python and SQL with automatic DataFrame conversion.
- **🚀 One-Click Deploy** — Turn any notebook into a scheduled job or a standalone dashboard app instantly.

---

## ⚡ Quick Start

### Installation

```bash
# Install the core package
pip install flowyml-notebook

# Recommended: Install with all ML & AI extensions
pip install "flowyml-notebook[all]"
```

### Launch

```bash
fml-notebook start
```

Your browser will automatically open to the FlowyML dashboard.

---

## 📚 Documentation

Detailed documentation is available at [docs.flowyml.ai/notebook](https://docs.flowyml.ai/notebook).

- [Getting Started](https://docs.flowyml.ai/notebook/getting-started)
- [Key Features](https://docs.flowyml.ai/notebook/features)
- [API Reference](https://docs.flowyml.ai/notebook/api)

---

## 🛠️ Development

We use `hatch` for package management and `npm` for the frontend.

```bash
git clone https://github.com/UnicoLab/flowyml-notebook.git
cd flowyml-notebook
make setup
make dev
```

---

<p align="center">
  <strong>Built with ❤️ by <a href="https://unicolab.ai">UnicoLab</a></strong>
</p>

