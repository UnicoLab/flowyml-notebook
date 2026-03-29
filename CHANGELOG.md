# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
