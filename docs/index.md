<div class="hero" markdown>

# FlowyML Notebook

### Your Analysis. One Reactive Engine.

**FlowyML Notebook** is a DAG-powered reactive notebook that replaces Jupyter for production ML. Write Python, get automatic dependency tracking, and ship to pipelines — without changing a single line of code.

No cloud lock-in. No JSON diffs. No stale state. Just pure Python notebooks that run, react, and deploy.

[:rocket: Get Started](getting-started.md){ .md-button .md-button--primary }
[:sparkles: Feature Tour](features.md){ .md-button }

</div>

<figure markdown>
  ![FlowyML Notebook Concept](assets/hero.png){ width="80%" .hero-image }
  <figcaption>Reactive DAG engine with integrated AI, data exploration, recipes, deployment, and collaboration</figcaption>
</figure>

---

## Your Notebook. Reimagined. :zap:

<figure markdown>
  ![Full Editor](screenshots/notebook.png){ width="100%" }
  <figcaption>FlowyML Notebook editor — reactive cells, rich outputs, and a professional toolbar</figcaption>
</figure>

---

## How It Works

<div class="grid cards" markdown>

-   :material-graph-outline:{ .lg .middle } **Reactive DAG**

    ---

    Every cell is a node in a dependency graph. Change a variable → only dependent cells re-execute. Automatically. Always consistent.

-   :material-language-python:{ .lg .middle } **Pure Python**

    ---

    Notebooks are standard `.py` files. Clean diffs, importable logic, full linting support. No more JSON noise.

-   :material-chart-box-outline:{ .lg .middle } **Rich Exploration**

    ---

    Every DataFrame gets automatic profiling — stats, charts, correlations, outlier detection, and ML-ready insights. Zero code.

-   :material-rocket-launch-outline:{ .lg .middle } **Ship to Production**

    ---

    One-click deploy as API, Docker, web app, or FlowyML pipeline. From notebook to production in seconds.

-   :material-robot-outline:{ .lg .middle } **AI Assistant**

    ---

    Generate code, debug errors, and explain data patterns — context-aware, powered by OpenAI or Google AI.

-   :material-source-branch:{ .lg .middle } **Git-Native**

    ---

    Full GitHub integration — branch, version, collaborate. No proprietary cloud. No database. Just Git.

</div>

---

## See It In Action

<figure markdown>
  ![Data Exploration](screenshots/pandas-display2.png){ width="100%" }
  <figcaption>Automatic chart generation for every column — histograms, distributions, and categorical breakdowns</figcaption>
</figure>

<figure markdown>
  ![Pipeline DAG](screenshots/dag.png){ width="60%" }
  <figcaption>Visual dependency graph: imports → data_generation → analysis → exploration → summary</figcaption>
</figure>

---

## Built For

<div class="grid cards" markdown>

-   :fontawesome-solid-flask:{ .lg .middle } **Data Scientists**

    ---

    Rich exploration, reactive execution, and ML insights — the notebook you wished Jupyter was.

-   :fontawesome-solid-gears:{ .lg .middle } **ML Engineers**

    ---

    Pipeline promotion, asset tracking, and deployment — ship models from your notebook to production.

-   :fontawesome-solid-users:{ .lg .middle } **Teams**

    ---

    GitHub collaboration, shared recipes, inline comments — work together without cloud vendor lock-in.

-   :fontawesome-solid-building:{ .lg .middle } **Enterprises**

    ---

    Self-hosted, API-driven, FlowyML ecosystem integration — production-grade infrastructure from day one.

</div>

---

## Why Switch From Jupyter?

| | Jupyter | **FlowyML Notebook** |
|---|:---:|:---:|
| Execution | Run cells in any order → stale state | Reactive DAG → always consistent |
| File format | `.ipynb` JSON → merge nightmare | `.py` files → clean Git diffs |
| Collaboration | None built-in | GitHub-native branching & versioning |
| Deployment | Copy-paste to scripts | One-click pipeline, API, or app |
| Data exploration | Raw text output | Rich profiling, charts, ML insights |
| Code reuse | Copy between notebooks | 39 built-in recipes + shared hub |

---

## Quick Start

```bash
pip install "flowyml-notebook[all]"
fml-notebook start
```

Your browser opens. Start building. :arrow_right: [Full Getting Started Guide](getting-started.md)

---

<div class="hero" markdown>

**Open Source.** Apache 2.0 Licensed. Self-hosted. No vendor lock-in.

[:fontawesome-brands-github: View on GitHub](https://github.com/UnicoLab/flowyml-notebook){ .md-button }
[:fontawesome-brands-python: PyPI Package](https://pypi.org/project/flowyml-notebook/){ .md-button }

</div>
