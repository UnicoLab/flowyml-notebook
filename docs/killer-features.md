# :fire: Killer Features

FlowyML Notebook introduces **13 new modules** that transform your notebook from a scratchpad into a professional data-science workstation. Every feature is available via Python API, CLI, and GUI — zero configuration required.

!!! success "What's New"
    This release focuses on **observability**, **code intelligence**, and **interoperability** — the three pillars that separate a hobby notebook from a production-grade ML development environment.

| Category | Features | Modules |
|----------|----------|---------|
| :stopwatch: **Performance & Profiling** | Cell Profiler, Cell Benchmark | `profiler`, `benchmark` |
| :shield: **Data Quality & Lineage** | Data Validator, Lineage Tracker | `data_validator`, `lineage` |
| :brain: **Code Intelligence** | Code Analyzer, Cell Dependencies, Notebook Search | `code_analyzer`, `cell_deps`, `search` |
| :zap: **Productivity** | Execution History, Snippet Library, Environment Inspector | `execution_history`, `snippets`, `environment` |
| :handshake: **Interoperability** | Package Installer, Notebook Converter, Notebook Diff | `package_installer`, `ipynb_converter`, `diff` |

---

## :stopwatch: Performance & Profiling

### :mag: Cell Profiler

Profile any cell's wall-clock time, CPU time, memory allocation, and function call hotspots — powered by `cProfile` and `tracemalloc` under the hood.

#### How It Works

1. **tracemalloc** captures memory snapshots before and after execution
2. **cProfile** instruments every function call with cumulative timing
3. Results are assembled into a `ProfileResult` with the top 20 functions and allocations
4. Rich HTML output with color-coded performance badges is rendered inline

#### Python API

```python
from flowyml_notebook.profiler import CellProfiler

profiler = CellProfiler(max_history=1000)

result = profiler.profile(
    cell_id="load_data",
    source="import pandas as pd\ndf = pd.read_csv('data.csv')",
    namespace=globals(),
)

print(f"⏱ Wall: {result.wall_time_s:.4f}s")
print(f"🧠 CPU:  {result.cpu_time_s:.4f}s")
print(f"📦 Mem:  {result.memory_delta_mb:+.2f} MB (peak: {result.peak_memory_mb:.2f} MB)")
print(f"📞 Calls: {result.function_calls}")
```

#### Response Shape

```json
{
  "cell_id": "load_data",
  "wall_time_s": 0.234512,
  "cpu_time_s": 0.198743,
  "memory_delta_mb": 12.4531,
  "peak_memory_mb": 45.8721,
  "function_calls": 1847,
  "top_functions": [
    {
      "name": "pandas/io/parsers.py:42(read_csv)",
      "calls": 1,
      "total_time": 0.189432,
      "cumulative_time": 0.218765,
      "per_call": 0.218765
    }
  ],
  "top_allocations": [
    {
      "file": "pandas/core/frame.py",
      "line": 614,
      "size_kb": 4821.33
    }
  ],
  "line_times": [],
  "timestamp": "2026-06-02T14:30:00.000000"
}
```

#### History & Comparison

```python
# Get all profiling runs for a cell
history = profiler.get_history_for_cell("load_data")

# Compare performance over time
for run in history:
    print(f"  {run.timestamp}: {run.wall_time_s:.4f}s | {run.memory_delta_mb:+.2f}MB")

# Clear all stored results
profiler.clear_history()
```

!!! tip "Performance Badges"
    The GUI renders inline badges with color-coded thresholds:
    :green_circle: **Fast** (≤ 0.1s) · :yellow_circle: **Medium** (≤ 1.0s) · :red_circle: **Slow** (> 1.0s)

---

### :chart_with_upwards_trend: Cell Benchmark

Run cells multiple times with warmup iterations, get statistical analysis (mean, median, std, min, max), and detect performance regressions automatically.

#### Python API

```python
from flowyml_notebook.benchmark import CellBenchmark

bench = CellBenchmark()

result = bench.benchmark(
    cell_id="transform",
    source="df_clean = df.dropna().reset_index(drop=True)",
    namespace=globals(),
    runs=7,       # Number of timed iterations
    warmup=1,     # Untimed warmup runs
)

print(f"Mean: {result.mean_s*1000:.2f}ms ± {result.std_s*1000:.2f}ms")
print(f"Range: {result.min_s*1000:.2f}–{result.max_s*1000:.2f}ms")
```

#### Response Shape

```json
{
  "cell_id": "transform",
  "runs": 7,
  "mean_s": 0.003421,
  "median_s": 0.003187,
  "std_s": 0.000543,
  "min_s": 0.002876,
  "max_s": 0.004512,
  "all_times": [0.004512, 0.003421, 0.003187, 0.003102, 0.002987, 0.002876, 0.003321],
  "timestamp": "2026-06-02T14:35:00.000000"
}
```

#### Regression Detection

```python
from flowyml_notebook.benchmark import CellBenchmark

bench = CellBenchmark()

# Run benchmark twice — the second time slower
bench.benchmark("etl", etl_code, ns, runs=5)
# ... make a code change ...
bench.benchmark("etl", etl_code_v2, ns, runs=5)

# Auto-detect regressions (default threshold: 25%)
regressions = bench.detect_regressions("etl", threshold_pct=25.0)

for r in regressions:
    print(f"⚠️  [{r.severity}] {r.message}")
    # ⚠️  [warning] Cell etl is 38% slower (0.0034s → 0.0047s)
```

!!! warning "Regression Severity Levels"
    | Change | Severity |
    |--------|----------|
    | 25–100% slower | `warning` |
    | > 100% slower | `critical` |

    The GUI renders inline sparkline bar charts for each run, colored green/yellow/red relative to the median.

---

## :shield: Data Quality & Lineage

### :white_check_mark: Data Validator

Automatic data quality scoring for every DataFrame in your notebook. Detects nulls, outliers, mixed types, infinite values, and duplicates — then assigns a per-column and overall quality score (0–100).

#### What It Detects

| Check | How | Penalty |
|-------|-----|---------|
| **Null values** | Per-column null count & percentage | –10 per 10% nulls |
| **Outliers** | IQR method on numeric columns | –5 per 5% outliers |
| **Mixed types** | Object columns with mixed Python types | –15 |
| **Infinite values** | `np.inf` / `np.nan` in numeric columns | –20 |
| **Duplicate rows** | Full-row deduplication check | –5 per 5% duplicates |
| **High cardinality** | Unique percentage > 95% in object columns | Warning |

#### Python API

```python
from flowyml_notebook.data_validator import DataValidator

validator = DataValidator()

report = validator.validate(
    var_name="df",
    cell_id="load_data",
    df=df,
)

print(f"📊 Overall Score: {report.overall_score}/100")
print(f"⚠️  Warnings: {len(report.warnings)}")
print(f"📦 Memory: {report.memory_mb:.2f} MB")
print(f"🔁 Duplicate rows: {report.duplicate_rows}")

for col in report.columns:
    if col.issues:
        print(f"  ❌ {col.column}: {', '.join(col.issues)} (score: {col.score})")
```

#### Response Shape

```json
{
  "var_name": "df",
  "cell_id": "load_data",
  "shape": [10000, 12],
  "overall_score": 78.5,
  "columns": [
    {
      "column": "revenue",
      "dtype": "float64",
      "null_count": 342,
      "null_pct": 3.42,
      "unique_count": 8976,
      "unique_pct": 89.76,
      "outlier_count": 127,
      "has_mixed_types": false,
      "has_infinite": false,
      "issues": ["3.42% null values", "1.27% outliers (IQR)"],
      "score": 85.2
    }
  ],
  "warnings": ["Column 'notes' has 95.2% unique values — possible ID column"],
  "duplicate_rows": 23,
  "memory_mb": 4.52,
  "timestamp": "2026-06-02T14:40:00.000000"
}
```

#### History Tracking

```python
# Get all reports for a variable
history = validator.get_reports("df")

# Compare quality over time
for r in history:
    print(f"  {r.timestamp}: score={r.overall_score} shape={r.shape}")
```

!!! info "Automatic Validation"
    The validator runs **transparently** after each cell execution. Any DataFrame in the kernel namespace is automatically validated and its quality score is displayed in the variable inspector.

---

### :dna: Lineage Tracker

Track how DataFrames evolve across cell executions. The lineage tracker captures structural snapshots (shape, columns, dtypes, null counts, memory, content hash) before and after each cell, computes diffs, and builds a full transformation graph.

#### How It Works

```
Cell A: df = pd.read_csv(...)          → Snapshot #1: (1000, 10)
Cell B: df = df.dropna()               → Snapshot #2: (  950, 10) — 50 rows removed
Cell C: df["new_col"] = df.a + df.b    → Snapshot #3: (  950, 11) — 1 column added
```

#### Python API

```python
from flowyml_notebook.lineage import LineageTracker

tracker = LineageTracker()

# Before cell execution
tracker.snapshot_before(cell_id="transform", namespace=globals())

# ... execute the cell ...

# After cell execution — returns list of LineageEntry
entries = tracker.snapshot_after(cell_id="transform", namespace=globals())

for entry in entries:
    if entry.diff:
        d = entry.diff
        print(f"📊 {d.var_name}: "
              f"+{d.rows_added}/-{d.rows_removed} rows, "
              f"+{d.columns_added}/-{d.columns_removed} cols")
```

#### Lineage Query

```python
# Full history for a variable
history = tracker.get_lineage("df")
for entry in history:
    snap = entry["snapshot"]
    print(f"  Cell {snap['cell_id']}: {snap['shape']} → {snap['memory_bytes']} bytes")

# Full lineage graph (all variables)
graph = tracker.get_lineage_graph()
```

#### Diff Response Shape

```json
{
  "var_name": "df",
  "cell_id": "transform",
  "rows_added": 0,
  "rows_removed": 50,
  "columns_added": ["new_col"],
  "columns_removed": [],
  "columns_retyped": {
    "price": {"from": "object", "to": "float64"}
  },
  "nulls_changed": {
    "revenue": {"from": 342, "to": 0}
  },
  "content_changed": true
}
```

!!! tip "Content Hashing"
    The tracker computes an MD5 digest of the first 100 rows (as CSV) for each snapshot. This lets it detect content changes even when the shape stays the same — e.g., after an in-place sort or value replacement.

---

## :brain: Code Intelligence

### :microscope: Code Analyzer

Real-time linting with rules specifically tuned for data science workflows. Detects unused imports, pandas anti-patterns, performance bottlenecks, security risks, naming issues, magic numbers, and deprecated patterns — with auto-fix suggestions where possible.

#### Detection Rules

| Rule | Severity | Example |
|------|----------|---------|
| **Unused imports** | `warning` | `import os` never used |
| **Pandas anti-patterns** | `performance` | `df.iterrows()` → vectorized ops |
| **Performance hints** | `performance` | `for` loop over DataFrame rows |
| **Security risks** | `security` | `eval()`, hardcoded credentials |
| **Naming conventions** | `style` | `myVar` → `my_var` (PEP 8) |
| **Magic numbers** | `style` | `if x > 0.85` → named constant |
| **Deprecated patterns** | `warning` | `.append()` → `pd.concat()` |

#### Python API

```python
from flowyml_notebook.code_analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()

report = analyzer.analyze(
    cell_id="train",
    source="""
import pandas as pd
import os

df = pd.read_csv("data.csv")
for idx, row in df.iterrows():
    if row['score'] > 0.85:
        print(row['name'])
""",
)

print(f"💡 {len(report.suggestions)} suggestions ({report.auto_fixes_available} auto-fixable)")

for s in report.suggestions:
    icon = {"warning": "⚠️", "performance": "🐌", "security": "🔒", "style": "🎨"}.get(s.severity, "ℹ️")
    print(f"  {icon} [{s.rule}] Line {s.line}: {s.message}")
    if s.fix:
        print(f"     Fix: {s.fix}")
```

#### Response Shape

```json
{
  "cell_id": "train",
  "suggestions": [
    {
      "rule": "unused-import",
      "severity": "warning",
      "message": "Module 'os' is imported but never used",
      "line": 2,
      "fix": null,
      "original": "import os"
    },
    {
      "rule": "pandas-iterrows",
      "severity": "performance",
      "message": "df.iterrows() is slow — use vectorized operations or .apply()",
      "line": 5,
      "fix": "df[df['score'] > 0.85]['name']",
      "original": "for idx, row in df.iterrows():"
    }
  ],
  "auto_fixes_available": 1,
  "timestamp": "2026-06-02T14:45:00.000000"
}
```

---

### :link: Cell Dependencies

AST-powered dependency analysis that maps which variables each cell defines and consumes, builds a full dependency graph with topological ordering, and propagates stale-cell markers when upstream cells change.

#### Python API

```python
from flowyml_notebook.cell_deps import CellDependencyAnalyzer

dep_analyzer = CellDependencyAnalyzer()

# Analyze all cells
cells = [
    ("cell_1", "import pandas as pd\ndf = pd.read_csv('data.csv')"),
    ("cell_2", "df_clean = df.dropna()"),
    ("cell_3", "summary = df_clean.describe()"),
]

for cell_id, source in cells:
    dep_analyzer.analyze_cell(cell_id, source)

# Get the full dependency graph
graph = dep_analyzer.get_graph()

print(f"Execution order: {graph.execution_order}")
print(f"Stale cells: {graph.stale_cells}")

for cell in graph.cells:
    print(f"  {cell.cell_id}: defines={cell.defines}, uses={cell.uses}")
```

#### Response Shape

```json
{
  "cells": [
    {
      "cell_id": "cell_1",
      "defines": ["pd", "df"],
      "uses": [],
      "imports": ["pandas"],
      "functions_defined": [],
      "classes_defined": []
    },
    {
      "cell_id": "cell_2",
      "defines": ["df_clean"],
      "uses": ["df"],
      "imports": [],
      "functions_defined": [],
      "classes_defined": []
    }
  ],
  "edges": [
    {"from": "cell_1", "to": "cell_2", "variable": "df"},
    {"from": "cell_2", "to": "cell_3", "variable": "df_clean"}
  ],
  "execution_order": ["cell_1", "cell_2", "cell_3"],
  "stale_cells": []
}
```

!!! info "How Stale Detection Works"
    When you edit `cell_1`, the dependency analyzer marks `cell_2` and `cell_3` as **stale** because they transitively depend on variables defined in `cell_1`. The GUI highlights stale cells with a yellow border and a "Re-run" badge.

---

### :mag_right: Notebook Search Engine

Full-text search across all notebook cells with **exact**, **fuzzy** (Levenshtein distance), and **regex** matching. Searches cell source code *and* outputs, finds variable/function definitions, and detects duplicate cells.

#### Python API

```python
from flowyml_notebook.search import NotebookSearch

search = NotebookSearch()

# Index your notebook cells
for cell in notebook.cells:
    search.index_cell(cell)

# Search with different modes
results = search.search(
    query="read_csv",
    mode="fuzzy",         # "exact", "fuzzy", or "regex"
    include_outputs=True,
    max_results=20,
)

for r in results:
    print(f"  Cell {r.cell_index} (line {r.line_number}): "
          f"[{r.match_type}] score={r.score:.2f}")
    print(f"    {r.context}")
```

#### Search Features

=== "Exact Match"

    ```python
    results = search.search("pd.read_csv", mode="exact")
    ```

=== "Fuzzy Match"

    ```python
    # Finds "read_csv" even if you search "readcsv" or "red_csv"
    results = search.search("red_csv", mode="fuzzy")
    ```

=== "Regex Match"

    ```python
    # Find all model.fit() calls with any arguments
    results = search.search(r"model\.\w+\.fit\(", mode="regex")
    ```

=== "Find Definitions"

    ```python
    # Find where a variable or function is defined
    defs = search.find_definitions("df_clean")
    ```

=== "Duplicate Detection"

    ```python
    # Find cells with similar content
    duplicates = search.find_duplicates(threshold=0.85)
    ```

#### Response Shape

```json
{
  "cell_id": "cell_2",
  "cell_index": 1,
  "cell_type": "code",
  "line_number": 3,
  "match_text": "pd.read_csv",
  "context": "df = pd.read_csv('data.csv', parse_dates=['date'])",
  "score": 1.0,
  "match_type": "exact"
}
```

---

## :zap: Productivity

### :clock3: Execution History — Time-Travel Debugging

A complete execution log for every cell. Inspect what a cell produced at any point, compare outputs across runs, and detect when behavior changed.

#### Python API

```python
from flowyml_notebook.execution_history import ExecutionHistory

history = ExecutionHistory(max_snapshots=50)

# Record after each cell execution
history.record(
    cell_id="train",
    source="model.fit(X_train, y_train)",
    outputs=cell.outputs,
    variables_changed={"model": "RandomForestClassifier"},
    success=True,
    duration_s=2.341,
    execution_count=5,
)

# Get the full timeline for a cell
timeline = history.get_timeline("train")
print(f"Total executions: {timeline['total_executions']}")
print(f"First run: {timeline['first_executed']}")
print(f"Last run:  {timeline['last_executed']}")
```

#### Time-Travel Comparison

```python
# Compare the last two runs of a cell
diff = history.compare_runs("train", run_a=-2, run_b=-1)

print(f"Source changed:  {diff['source_changed']}")
print(f"Outputs changed: {diff['outputs_changed']}")
print(f"Duration delta:  {diff['duration_delta_s']:+.4f}s ({diff['duration_change_pct']:+.1f}%)")
```

#### Response Shape

```json
{
  "cell_id": "train",
  "run_a": {
    "index": -2,
    "source": "model.fit(X_train, y_train)",
    "variables_changed": {"model": "RandomForestClassifier"},
    "success": true,
    "duration_s": 2.341,
    "timestamp": "2026-06-02T14:50:00"
  },
  "run_b": {
    "index": -1,
    "source": "model.fit(X_train, y_train)",
    "variables_changed": {"model": "RandomForestClassifier"},
    "success": true,
    "duration_s": 2.187,
    "timestamp": "2026-06-02T14:55:00"
  },
  "source_changed": false,
  "outputs_changed": true,
  "success_changed": false,
  "duration_delta_s": -0.154,
  "duration_change_pct": -6.6
}
```

#### Global Execution Log

```python
# See the last 50 executions across ALL cells
log = history.get_global_log(limit=50)

# Get timelines for every cell at once
all_timelines = history.get_all_timelines()
```

---

### :bookmark_tabs: Snippet Library

**30+ built-in code snippets** across 7 categories, plus the ability to add your own custom snippets. Search by text, category, tags, or difficulty level.

#### Built-in Categories

| Category | Snippets | Examples |
|----------|----------|---------|
| **Data Loading** | 5 | CSV, Excel, SQL, API, Sample Data |
| **Data Cleaning** | 5 | Missing Values, Duplicates, Outliers, Type Conversion, Column Rename |
| **Visualization** | 5 | Histogram, Scatter, Heatmap, Box Plot, Time Series |
| **Feature Engineering** | 4 | Encoding, Scaling, Date Features, Text Features |
| **ML Evaluation** | 4 | Confusion Matrix, ROC Curve, Classification Report, Learning Curve |
| **Utilities** | 4 | Timer Decorator, Progress Bar, Memory Report, Random Seeds |
| **Data Exploration** | 3 | Quick EDA, Correlation, Value Counts |

#### Python API

```python
from flowyml_notebook.snippets import SnippetLibrary, Snippet

library = SnippetLibrary()

# Browse categories
print(library.get_categories())
# ['Data Cleaning', 'Data Exploration', 'Data Loading', 'Feature Engineering',
#  'ML Evaluation', 'Utilities', 'Visualization']

# Search snippets
results = library.search("confusion matrix", category="ML Evaluation")
for s in results:
    print(f"  [{s.difficulty}] {s.title}: {s.description}")

# Get a specific snippet by ID
snippet = library.get_snippet("builtin-eval-confusion")
print(snippet.code)

# Get all snippets in a category
viz_snippets = library.get_by_category("Visualization")
```

#### Custom Snippets

```python
# Add your own reusable snippets (session-scoped)
my_snippet = library.add_custom(Snippet(
    title="My Custom EDA",
    description="Quick EDA template for new datasets",
    category="Data Exploration",
    tags=["eda", "pandas", "custom"],
    difficulty="beginner",
    code=(
        "print(df.shape)\n"
        "print(df.dtypes)\n"
        "print(df.describe())\n"
        "print(df.isnull().sum())\n"
    ),
))

# Track snippet usage
library.record_use(my_snippet.id)

# Delete a custom snippet
library.delete_custom(my_snippet.id)
```

!!! tip "Snippet Difficulty Levels"
    Each snippet has a difficulty tag — `beginner`, `intermediate`, or `advanced` — so you can filter based on your experience level.

---

### :package: Environment Inspector

Capture a complete snapshot of your runtime environment — Python version, OS, architecture, all installed packages with versions, GPU availability (NVIDIA + Apple Silicon MPS), and CPU metadata.

#### Python API

```python
from flowyml_notebook.environment import capture_environment

snapshot = capture_environment()

print(f"🐍 Python: {snapshot.python_version}")
print(f"💻 Platform: {snapshot.platform_info}")
print(f"🏗️  Arch: {snapshot.architecture}")
print(f"🧮 CPUs: {snapshot.cpu_count}")
print(f"📦 Packages: {len(snapshot.packages)}")

if snapshot.gpu_info:
    for gpu in snapshot.gpu_info:
        print(f"🎮 GPU: {gpu['name']} ({gpu.get('memory', 'N/A')})")
```

#### Auto-Generate Requirements

```python
from flowyml_notebook.environment import extract_imports, generate_requirements

# Extract imports used in your notebook
imports = extract_imports(notebook)
print(f"Notebook uses {len(imports)} packages")

# Generate requirements.txt with pinned versions
requirements_txt = generate_requirements(
    notebook,
    format="requirements",  # or "conda"
    pin_versions=True,
)

print(requirements_txt)
# pandas==2.2.1
# numpy==1.26.4
# scikit-learn==1.4.1
# matplotlib==3.8.3
```

#### Response Shape

```json
{
  "python_version": "3.11.4 (main, Jun 20 2026, 17:45:00) [Clang 14.0.3]",
  "platform_info": "macOS-14.4-arm64-arm-64bit",
  "os_name": "Darwin",
  "architecture": "arm64",
  "packages": {
    "pandas": "2.2.1",
    "numpy": "1.26.4",
    "scikit-learn": "1.4.1"
  },
  "gpu_info": [
    {"name": "Apple M2 Pro", "type": "mps"}
  ],
  "timestamp": "2026-06-02T15:00:00.000000",
  "cpu_count": 10
}
```

---

## :handshake: Interoperability

### :inbox_tray: Package Installer

Install, uninstall, and search PyPI packages directly from your notebook — with automatic environment detection (Conda, venv, system).

#### Python API

```python
from flowyml_notebook.package_installer import (
    detect_environment,
    install_package,
    uninstall_package,
    search_pypi,
    list_installed,
)

# Detect current environment
env = detect_environment()
print(f"📦 Environment: {env.env_type} ({env.env_name})")
print(f"🐍 Python: {env.python_path}")
print(f"📍 Pip: {env.pip_path}")

# Install a package
result = install_package("xgboost>=2.0")
if result.success:
    print(f"✅ Installed {result.package} {result.version}")
else:
    print(f"❌ Failed: {result.error}")

# Search PyPI
packages = search_pypi("gradient boosting")
for pkg in packages:
    print(f"  {pkg['name']} ({pkg['version']}): {pkg['summary']}")
```

#### Environment Detection

The installer auto-detects your environment type:

| Environment | Detection Method |
|-------------|-----------------|
| **Conda** | `CONDA_PREFIX` env variable |
| **venv** | `VIRTUAL_ENV` env variable or `sys.prefix != sys.base_prefix` |
| **System** | Fallback — uses system `pip` |

---

### :arrows_counterclockwise: Notebook Converter

Bidirectional conversion between Jupyter `.ipynb` (v4) and FlowyML `.py` notebook formats — no `nbformat` dependency required.

#### Python API

=== "Import from .ipynb"

    ```python
    from flowyml_notebook.ipynb_converter import from_ipynb

    # From file path
    notebook = from_ipynb("my_notebook.ipynb")

    # From dict (already parsed JSON)
    notebook = from_ipynb(ipynb_dict)

    print(f"Imported: {notebook.metadata.name}")
    print(f"Cells: {len(notebook.cells)}")
    ```

=== "Export to .ipynb"

    ```python
    from flowyml_notebook.ipynb_converter import to_ipynb

    ipynb_json = to_ipynb(notebook)

    # Save to file
    import json
    with open("exported.ipynb", "w") as f:
        json.dump(ipynb_json, f, indent=2)
    ```

=== "Auto-Detect Conversion"

    ```python
    from flowyml_notebook.ipynb_converter import convert_file

    # Automatically detects direction by file extension
    convert_file("notebook.ipynb", "notebook.py")   # .ipynb → .py
    convert_file("notebook.py", "notebook.ipynb")   # .py → .ipynb
    ```

#### What's Preserved

| Feature | Import (.ipynb → .py) | Export (.py → .ipynb) |
|---------|----------------------|----------------------|
| **Cell source** | ✅ | ✅ |
| **Cell type** (code/markdown) | ✅ | ✅ |
| **Cell outputs** | ✅ (text, HTML, images) | ✅ |
| **Execution count** | ✅ | ✅ |
| **Kernel metadata** | ✅ → description | ✅ |
| **Cell IDs** | Generated if missing | ✅ |

!!! info "nbformat Not Required"
    The converter implements a lightweight `.ipynb` v4 parser directly — no dependency on the `nbformat` package. Notebooks with `nbformat < 4` will raise a `ValueError` with a suggestion to open in Jupyter for auto-upgrade.

---

### :left_right_arrow: Notebook Diff

Structural comparison of two FlowyML notebooks. Detects added, removed, modified, moved, and unchanged cells — with unified diff output in both ANSI (terminal) and HTML formats.

#### Python API

```python
from flowyml_notebook.diff import diff_notebooks

result = diff_notebooks(notebook_a, notebook_b)

print(f"📊 Summary: {result.summary}")
print(f"  Added:     {result.added}")
print(f"  Removed:   {result.removed}")
print(f"  Modified:  {result.modified}")
print(f"  Moved:     {result.moved}")
print(f"  Unchanged: {result.unchanged}")

# Inspect individual cell diffs
for cell_diff in result.cells:
    if cell_diff.status == "modified":
        print(f"\n--- {cell_diff.name} ({cell_diff.cell_id}) ---")
        print(cell_diff.unified_diff)
```

#### Output Formats

=== "Terminal (ANSI)"

    ```python
    from flowyml_notebook.diff import render_diff_ansi

    ansi_output = render_diff_ansi(result)
    print(ansi_output)
    # Color-coded: green for added, red for removed, yellow for modified
    ```

=== "HTML"

    ```python
    from flowyml_notebook.diff import render_diff_html

    html_output = render_diff_html(result)
    # Rich HTML with side-by-side comparison, syntax highlighting
    ```

#### Response Shape

```json
{
  "cells": [
    {
      "status": "modified",
      "cell_id": "transform",
      "cell_type": "CODE",
      "name": "transform",
      "source_a": "df_clean = df.dropna()",
      "source_b": "df_clean = df.dropna().reset_index(drop=True)",
      "unified_diff": "--- a/transform\n+++ b/transform\n@@ -1 +1 @@\n-df_clean = df.dropna()\n+df_clean = df.dropna().reset_index(drop=True)",
      "index_a": 2,
      "index_b": 2
    }
  ],
  "metadata_changes": {
    "name": ["Notebook v1", "Notebook v2"]
  },
  "summary": {"added": 1, "removed": 0, "modified": 2, "moved": 0, "unchanged": 5}
}
```

---

## :rocket: Putting It All Together

These 13 features work together seamlessly. Here's a real-world workflow that touches all of them:

```python
from flowyml_notebook.profiler import CellProfiler
from flowyml_notebook.data_validator import DataValidator
from flowyml_notebook.lineage import LineageTracker
from flowyml_notebook.code_analyzer import CodeAnalyzer
from flowyml_notebook.execution_history import ExecutionHistory
from flowyml_notebook.environment import capture_environment

# 1. Capture environment for reproducibility
env = capture_environment()

# 2. Initialize trackers
profiler = CellProfiler()
validator = DataValidator()
tracker = LineageTracker()
analyzer = CodeAnalyzer()
history = ExecutionHistory()

# 3. Before cell execution
tracker.snapshot_before("load_data", globals())

# 4. Profile the cell
result = profiler.profile("load_data", "df = pd.read_csv('data.csv')", globals())

# 5. After cell execution
lineage = tracker.snapshot_after("load_data", globals())

# 6. Validate data quality
report = validator.validate("df", "load_data", df)

# 7. Analyze code quality
lint = analyzer.analyze("load_data", "df = pd.read_csv('data.csv')")

# 8. Record execution
history.record("load_data", "df = pd.read_csv('data.csv')",
               success=True, duration_s=result.wall_time_s)

print(f"⏱ Profile:  {result.wall_time_s:.4f}s | {result.memory_delta_mb:+.2f}MB")
print(f"📊 Quality:  {report.overall_score}/100")
print(f"💡 Lint:     {len(lint.suggestions)} suggestions")
print(f"🧬 Lineage:  {len(lineage)} variables tracked")
```

!!! success "All features are GUI-integrated"
    Every feature above is wired into the FlowyML Notebook GUI. You don't need to write any of this code manually — the notebook runs profiling, validation, lineage tracking, and code analysis automatically as you work. The APIs are exposed for power users who want programmatic access.
