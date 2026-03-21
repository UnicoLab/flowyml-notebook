# Contributing to FlowyML Notebook

Thank you for your interest in contributing to FlowyML Notebook! This guide will help you get started.

## Development Setup

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Git**

### Local Setup

```bash
# Clone the repository
git clone https://github.com/UnicoLab/flowyml-notebook.git
cd flowyml-notebook

# Full setup (Python package + frontend)
make setup

# Or step-by-step:
pip install -e ".[all]"
cd flowyml_notebook/frontend && npm install
```

### Running in Development

```bash
# Hot-reload dev mode (Vite + FastAPI)
make dev

# Run tests
make test

# Build frontend for production
make build
```

## Code Style

We use **Ruff** for linting and formatting:

- Line length: **100 characters**
- Target: Python 3.10+
- Rules: `E`, `F`, `I` (pycodestyle, pyflakes, isort)

```bash
# Check linting
make lint

# Auto-format
make format
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning via Semantic Release.

| Prefix | Purpose | Version Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `docs:` | Documentation only | None |
| `chore:` | Maintenance tasks | None |
| `refactor:` | Code refactoring | None |
| `perf:` | Performance improvements | Patch |
| `test:` | Adding or fixing tests | None |
| `BREAKING CHANGE:` | Breaking API change | Major |

**Examples:**
```
feat: add scatter plot to DataFrameExplorer
fix: correct pagination in large DataFrames
docs: expand getting-started guide
```

## Pull Request Workflow

1. **Fork** the repository and create a feature branch from `main`.
2. **Make your changes** following the code style guidelines.
3. **Write/update tests** for any new functionality.
4. **Run the test suite** locally: `make test`
5. **Commit** using Conventional Commits format.
6. **Open a Pull Request** against `main`.

### PR Checklist

- [ ] Tests pass (`make test`)
- [ ] Linter passes (`make lint`)
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow Conventional Commits

## Project Structure

```
flowyml-notebook/
├── flowyml_notebook/          # Python package
│   ├── core.py                # Notebook engine & reactive execution
│   ├── cells.py               # Cell model & serialization
│   ├── reactive.py            # DAG dependency graph
│   ├── cli.py                 # CLI entry point
│   ├── server.py              # FastAPI server
│   ├── kernel.py              # Python kernel
│   ├── connection.py          # FlowyML instance connector
│   ├── github_sync.py         # GitHub collaboration backend
│   ├── recipes_store.py       # Recipe management
│   ├── reporting.py           # HTML/PDF report generation
│   ├── deployer.py            # Pipeline export & Docker
│   ├── sql/                   # SQL cell engine
│   ├── ai/                    # AI assistant integration
│   ├── ui/                    # App mode & widgets
│   └── frontend/              # React frontend (Vite)
├── tests/                     # Test suite
├── docs/                      # MkDocs documentation
└── assets/                    # Logo and static assets
```

## Questions?

Open a [GitHub Discussion](https://github.com/UnicoLab/flowyml-notebook/discussions) or reach out to the team at **support@unicolab.ai**.
