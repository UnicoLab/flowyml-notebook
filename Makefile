.PHONY: help setup dev start test build clean install docs docs-serve lint format

# ── Auto-detect Python (prefer poetry if in parent project, else system) ──
POETRY_CHECK := $(shell command -v poetry 2>/dev/null)
IN_POETRY := $(shell [ -f ../pyproject.toml ] && grep -q "tool.poetry" ../pyproject.toml 2>/dev/null && echo 1)

ifeq ($(IN_POETRY),1)
  PYTHON := poetry run python
  PIP := poetry run pip
else ifdef VIRTUAL_ENV
  PYTHON := python
  PIP := pip
else
  PYTHON := python3
  PIP := pip3
endif

FRONTEND_DIR := flowyml_notebook/frontend

# ── Default ──────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "  🌊 FlowyML Notebook"
	@echo "  ════════════════════════════════════════════════════"
	@echo ""
	@echo "  Quick start:"
	@echo "    make setup   → install everything"
	@echo "    make dev     → launch dev mode"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── 🔧 Setup ────────────────────────────────────────────────────────────────

setup: ## 🔧 Full setup (install package + frontend deps)
	@echo ""
	@echo "  🌊 Setting up FlowyML Notebook..."
	@echo "  ──────────────────────────────────"
	@echo ""
	@echo "  📦 Installing Python package (editable)..."
	$(PIP) install -e ".[all]"
	@echo ""
	@echo "  🎨 Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install --no-audit --no-fund
	@echo ""
	@echo "  ✅ Setup complete! Run 'make dev' to start."
	@echo ""

install: ## Install Python package only (editable mode)
	$(PIP) install -e ".[all]"

frontend-deps: ## Install frontend dependencies only
	cd $(FRONTEND_DIR) && npm install --no-audit --no-fund

# ── 🔥 Development ──────────────────────────────────────────────────────────

dev: ## 🔥 Launch dev mode (hot reload, auto-open browser)
	$(PYTHON) -m flowyml_notebook.cli dev

start: ## 🚀 Launch with production build (single port)
	$(PYTHON) -m flowyml_notebook.cli start

# ── 📦 Build ────────────────────────────────────────────────────────────────

build: ## Build frontend for distribution
	cd $(FRONTEND_DIR) && npm install --no-audit --no-fund && npm run build

# ── 🧪 Testing ──────────────────────────────────────────────────────────────

test: ## Run all tests
	$(PYTHON) tests/run_tests.py

test-pytest: ## Run tests with pytest
	$(PYTHON) -m pytest tests/ -v

# ── 🧹 Cleanup ──────────────────────────────────────────────────────────────

clean: ## Clean all build artifacts
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "  ✅ Cleaned"

# ── 📖 Documentation ────────────────────────────────────────────────────────

docs: ## Build documentation (MkDocs)
	$(PYTHON) -m mkdocs build --strict

docs-serve: ## Serve documentation locally (with live reload)
	$(PYTHON) -m mkdocs serve

# ── 🔍 Code Quality ─────────────────────────────────────────────────────────

lint: ## Run linter (Ruff)
	$(PYTHON) -m ruff check flowyml_notebook/ tests/

format: ## Auto-format code (Ruff)
	$(PYTHON) -m ruff format flowyml_notebook/ tests/
	$(PYTHON) -m ruff check --fix flowyml_notebook/ tests/

