# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
