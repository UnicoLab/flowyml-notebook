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

Traditional notebooks are great for exploration but terrible for production. FlowyML Notebook bridges this gap:

| Feature | Jupyter | Deepnote | Marimo | **FlowyML Notebook** |
|---|:---:|:---:|:---:|:---:|
| Reactive execution (DAG) | ❌ | ❌ | ✅ | ✅ |
| Pure `.py` file storage | ❌ | ❌ | ✅ | ✅ |
| Git-native collaboration | ❌ | ⚠️ Cloud | ❌ | ✅ GitHub |
| ML pipeline integration | ❌ | ❌ | ❌ | ✅ FlowyML |
| Reusable recipes | ❌ | ❌ | ❌ | ✅ |
| One-click deploy | ❌ | ⚠️ Cloud | ❌ | ✅ |
| SQL first-class | ❌ | ✅ | ✅ | ✅ |
| AI assistant | ❌ | ✅ | ❌ | ✅ |
| Rich data explorer | ❌ | ✅ | ✅ | ✅ |
| App mode | ❌ | ❌ | ✅ | ✅ |
| Self-hosted | ✅ | ❌ | ✅ | ✅ |

### Core Highlights

- **🔄 Reactive Execution** — Cells are nodes in a DAG. Changing a variable automatically triggers re-execution of only dependent cells.
- **📄 Git-Native** — Notebooks are stored as human-readable `.py` files. No more JSON diff nightmares.
- **🎛️ Interactive Instruments** — Professional-grade UI widgets bound directly to Python variables.
- **🤖 AI Intelligence** — Integrated assistant with deep knowledge of the FlowyML ecosystem.
- **📊 SQL First-Class** — Seamless Python ↔ SQL with automatic DataFrame conversion.
- **🚀 One-Click Deploy** — Turn any notebook into a pipeline, dashboard, Docker container, or web app.
- **🤝 Git Collaboration** — Full branching and versioning using GitHub as a backend. No database required.
- **🧾 Optimized Recipes** — Create and share reusable code templates for common ML tasks.
- **📈 Rich Exploration** — Automated data profiling with histograms, statistics, ML insights, and scatter plots.

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

### Your First Reactive Notebook

```python
# Cell 1
x = 10

# Cell 2 (auto-executes when x changes!)
result = x * 2
print(f"Result: {result}")  # → Result: 20
```

---

## 🛠️ CLI Reference

| Command | Description |
|---|---|
| `fml-notebook dev` | 🔥 Launch with Vite hot reload |
| `fml-notebook start` | 🚀 Launch with production build |
| `fml-notebook run <file>` | ▶️ Execute a notebook headlessly |
| `fml-notebook export <file>` | 📦 Export as pipeline/HTML/PDF/Docker |
| `fml-notebook app <file>` | 🌐 Deploy as interactive web app |
| `fml-notebook list --server <URL>` | 📚 List notebooks on a server |

---

## 📚 Documentation

Detailed documentation is available at [docs.flowyml.ai/notebook](https://docs.flowyml.ai/notebook).

| Section | Description |
|---|---|
| [Getting Started](https://docs.flowyml.ai/notebook/getting-started) | Install, launch, configure |
| [Key Features](https://docs.flowyml.ai/notebook/features) | Complete feature inventory |
| [Architecture](https://docs.flowyml.ai/notebook/architecture) | System design & reactive engine |
| [Recipes](https://docs.flowyml.ai/notebook/recipes) | Reusable cell templates |
| [Collaboration](https://docs.flowyml.ai/notebook/collaboration) | GitHub-based team workflows |
| [Integration](https://docs.flowyml.ai/notebook/integration) | FlowyML instance connections |
| [Data Exploration](https://docs.flowyml.ai/notebook/exploration) | Rich DataFrame profiling |
| [API Reference](https://docs.flowyml.ai/notebook/api) | CLI & Python API docs |

---

## 🛠️ Development

We use `hatch` for package management and `npm` for the frontend.

```bash
git clone https://github.com/UnicoLab/flowyml-notebook.git
cd flowyml-notebook
make setup
make dev
```

| Target | Description |
|---|---|
| `make setup` | Install Python package + frontend deps |
| `make dev` | Launch dev mode with hot reload |
| `make test` | Run all tests |
| `make lint` | Run Ruff linter |
| `make format` | Auto-format code |
| `make docs` | Build MkDocs documentation |
| `make docs-serve` | Preview docs locally |
| `make build` | Build frontend for production |
| `make clean` | Remove all build artifacts |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## 🤝 Community

- 📖 [Documentation](https://docs.flowyml.ai/notebook)
- 🐛 [Bug Reports](https://github.com/UnicoLab/FlowyML-Notebook/issues)
- 💬 [Discussions](https://github.com/UnicoLab/FlowyML-Notebook/discussions)
- 📋 [Contributing Guide](CONTRIBUTING.md)
- 📜 [Changelog](CHANGELOG.md)
- 🔒 [Security Policy](SECURITY.md)
- 📝 [Code of Conduct](CODE_OF_CONDUCT.md)

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).

<p align="center">
  <strong>Built with ❤️ by <a href="https://unicolab.ai">UnicoLab</a></strong>
</p>
