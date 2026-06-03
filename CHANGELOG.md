# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] — 2026-06-02

### Added

- **Cell Snippets Library** (`snippets.py`): Built-in library of **35 reusable data science code snippets** across 8 categories (Data Loading, Data Cleaning, EDA, Feature Engineering, Modeling, Visualization, ML Evaluation, Utilities). Search, filter, add custom snippets, and track usage — new API endpoints: `GET /api/snippets`, `GET /api/snippets/categories`, `POST /api/snippets`, `POST /api/snippets/{id}/use`.
- **Smart Cell Dependencies** (`cell_deps.py`): AST-based dependency analysis between notebook cells — detects variable definitions, uses, imports, function/class definitions across cells. Builds a full dependency graph with topological sort (Kahn's algorithm), stale cell detection via BFS, and optimal execution order. Handles tuple unpacking, comprehension scoping, for/with vars, and builtin filtering — new API endpoints: `GET /api/cells/dependencies`, `GET /api/cells/{id}/dependencies`, `GET /api/cells/{id}/stale`, `GET /api/cells/execution-order`.
- **Notebook Search Engine** (`search.py`): Full-text search with exact, fuzzy (Levenshtein), and regex matching. Search & replace across all cells, find all variable/function definitions (AST-based), and duplicate code detection (Levenshtein + Jaccard similarity). Zero external dependencies — new API endpoints: `POST /api/search`, `POST /api/search/replace`, `GET /api/search/variables`, `GET /api/search/functions`, `GET /api/search/duplicates`.
- **Unified Package Management** endpoint (`POST /api/environment/packages`): Single endpoint for the ToolsPanel frontend to install/uninstall packages with automatic message generation.
- **New Tests**: 40+ new pytest tests for all 3 new modules (`test_new_killer_features.py`) — total test suite now at 260+ tests.
- **CLI `list` command implemented**: `fml-notebook list --server <URL>` now actually queries the remote server's `/api/notebooks` endpoint and displays results with cell counts and timestamps.
- **Production classifier**: Upgraded from `Development Status :: 4 - Beta` to `5 - Production/Stable`.
- **Semantic release version sync**: Added `__init__.py` to `version_variables` to prevent version drift.

### Fixed

- **EnvironmentSnapshot serialization**: Added `to_dict()` method — previously crashed `/api/environment/snapshot` with `AttributeError`.
- **`export_requirements()` missing parameter**: Fixed `TypeError` in `/api/environment/requirements` — `output_path` was required but not provided.
- **Benchmark history double-serialization**: Fixed crash in `/api/benchmark/history/{id}` calling `.to_dict()` on already-serialized dicts.
- **Profile tab response mismatch**: Backend returns `wall_time_s` but frontend expected `wall_time` — added response mapping layer.
- **Benchmark tab response mismatch**: Backend returns `mean_s`/`all_times` but frontend expected `mean`/`run_times` — fixed extraction.
- **Quality tab response mismatch**: Backend returns `overall_score`/`columns` but frontend expected `score`/`column_issues` — fixed mapping.
- **Lint tab response extraction**: Frontend wasn't extracting `.report` from response — code analysis appeared empty.
- **Auto-fix field name**: Backend returns `fixed_source` but frontend checked `source` — now checks both.
- **History tab field names**: `success_rate_pct` (0–100) misread as 0–1 ratio, `total_time_s` → `total_time`, `snapshots` → `executions`.
- **Environment snapshot format**: Backend `os_name` → frontend `os`, packages dict converted to `[{name, version}]` array for frontend consumption.
- **Missing packages endpoint**: Frontend called `POST /api/environment/packages` which didn't exist — added unified endpoint.

### Changed

- **Total API endpoints**: 157 (up from 143 in v1.4.0).
- **Total Python LOC**: ~20,000 across 13 killer feature modules.
- **ToolsPanel.jsx**: All 6 tabs now have correct response mapping — Profile, Benchmark, Quality, Lint, History, Environment.

## [1.4.0] — 2026-03-29

### Added

- **Position-Aware Reactive DAG**: Order-aware dependency analysis that correctly distinguishes `x = 1; y = x + 1` (x is NOT upstream) from `df = df.dropna()` (df IS upstream). Uses AST position tracking to determine true evaluation order.
- **Save As / Open Workflows**: Full Save As and Open notebook workflows for improved file management.
- **Smart Kernel Detection**: Automatic kernel detection for seamless notebook startup.
- **Cell Folding**: Collapsible cell sections for better notebook organization.
- **Undo / Redo**: Full undo/redo support for cell operations.
- **Edge Case Tests**: 9 new pytest tests for reactive engine position-aware analysis.

### Fixed

- **Same-Line Assignment Bug**: Fixed critical bug where `df = df.dropna()` was not detected as an upstream dependency — Python evaluates RHS before LHS store, but column offsets gave a misleading order.
- **Builtins Filter Bug**: Fixed `__builtins__` context-dependent behavior that incorrectly filtered user variables named `values`, `keys`, `items`, etc. when running in `__main__` context.
- **Version Sync**: Aligned `__init__.py` version with `pyproject.toml`.

## [1.3.0] — 2026-03-24

### Added

- **UnicoLab Ecosystem Integration**: Native adapter layer for Keras-centric ML workflows using [KDP](https://github.com/UnicoLab/keras-data-processor), [KerasFactory](https://github.com/UnicoLab/KerasFactory), and [MLPotion](https://github.com/UnicoLab/MLPotion). All packages are optional — adapters gracefully degrade when not installed.
- **KDP Adapter (SmartPrep)**: Auto-detects DataFrame feature types and generates ready-to-use `PreprocessingModel` code with distribution-aware encoding and tabular attention. Surfaces as a top-priority "recommended" suggestion in the SmartPrep Advisor panel.
- **KerasFactory Adapter (Algorithm Matchmaker)**: Generates `BaseFeedForwardModel` and advanced `GatedResidualNetwork` + `TabularAttention` model recommendations for classification, regression, and unsupervised anomaly detection tasks.
- **MLPotion Adapter (Algorithm Matchmaker)**: Generates managed `ModelTrainer` + `ModelTrainingConfig` training pipelines with adaptive hyperparameters based on dataset size.
- **End-to-End Pipeline Recommendation**: When all three ecosystem packages are installed, the Algorithm Matchmaker surfaces a flagship "KDP → KerasFactory → MLPotion" unified pipeline recommendation.
- **Ecosystem Status API**: New `GET /api/ecosystem/status` endpoint reporting installed packages, versions, install commands, and documentation links.
- **Builtin Ecosystem Recipes**: 4 new multi-cell recipes — KDP Smart Preprocessing, KerasFactory Quick Model, MLPotion Training Pipeline, and the UnicoLab End-to-End Pipeline.
- **`[keras]` extras group**: New optional dependency group (`pip install 'flowyml-notebook[keras]'`) that installs `mlpotion`, `kerasfactory`, and `kdp`.
- **New Tests**: 28 additional tests for the integration module (`test_integrations.py`) — adapters, recipes, and ecosystem detection.

## [1.2.0] — 2026-03-23

### Added

- **SmartPrep Advisor**: Automated DataFrame quality analysis with actionable preprocessing suggestions — missing values, skew correction, outlier clipping, high-cardinality encoding, class imbalance detection, and feature scaling. Backend (`/api/smartprep/{var_name}`) and integrated `SmartPrepPanel` UI tab.
- **Algorithm Matchmaker**: Intelligent ML algorithm recommendations based on data characteristics — auto-detects task type (classification/regression/clustering), ranks algorithms with reasoning, caveats, speed and interpretability metrics, and generates ready-to-run sklearn pipeline code. Backend (`/api/algorithm-match/{var_name}`) and `AlgorithmMatchPanel` UI tab.
- **Live Interactive Dashboards**: Enhanced `AppPublisher` with interactive widget configuration (auto-detected filters, sliders, dropdowns), auto-refresh intervals, shareable URLs with embedded state, and email snapshot capability.
- **Collaborative Analysis Patterns**: Full pattern management system for bookmarking and reusing cell sequences — CRUD API (`/api/patterns`), search/filter by tags, data type, and problem type, usage tracking, and dedicated `AnalysisPatternsPanel` right panel.
- **New Tests**: 22 additional tests for all new features (`test_server_features.py`) — total test suite now at 130 tests.

## [0.1.0] — 2026-03-21

### Added

- **Reactive Execution Engine**: DAG-based cell execution with automatic dependency tracking.
- **Pure Python Storage**: Notebooks saved as `.py` files for Git compatibility and linting.
- **Interactive UI**: Browser-based notebook with React frontend and real-time WebSocket updates.
- **SQL Cells**: First-class SQL support with automatic DataFrame conversion (DuckDB, SQLAlchemy).
- **AI Assistant**: Context-aware code generation integrated into the notebook UI.
- **Recipes**: Reusable cell templates with creation, sharing, and usage tracking.
- **GitHub Collaboration**: Team workflows using `.flowyml-hub` Git-based architecture (branching, versioning, sync).
- **FlowyML Integration**: Connect to FlowyML instances for remote execution, scheduling, and asset management.
- **Rich Data Exploration**: Automated DataFrame profiling with histograms, statistics, correlations, ML insights, and scatter plots.
- **One-Click Deploy**: Export notebooks as FlowyML pipelines, HTML reports, or Docker containers.
- **App Mode**: Turn notebooks into standalone web applications with configurable layouts.
- **CLI**: Full command-line interface (`dev`, `start`, `run`, `export`, `app`, `list`).
- **MkDocs Documentation**: Comprehensive documentation with Material theme.
- **CI/CD**: GitHub Actions for testing, semantic releases, and documentation deployment.
