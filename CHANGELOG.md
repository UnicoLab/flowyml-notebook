# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
