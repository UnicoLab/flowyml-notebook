# FlowyML Notebook — Local Build & Test Tutorial

Complete guide to build, run, and validate the package locally before releasing.

---

## Prerequisites

| Tool | Min version | Check |
|------|------------|-------|
| Python | 3.10 | `python3 --version` |
| Node.js | 18 | `node --version` |
| npm | 9 | `npm --version` |
| git | any | `git --version` |

---

## 1. Clone & enter the repo

```bash
git clone https://github.com/UnicoLab/flowyml-notebook.git
cd flowyml-notebook
```

---

## 2. Create the Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
```

---

## 3. Install the package in editable mode

Editable mode (`-e`) means every Python change is live — no reinstall needed.

```bash
# Core + dev tools + optional extras
pip install -e ".[dev,sql,ai,exploration]"
```

Available extras: `flowyml`, `ai`, `sql`, `exploration`, `keras`, `dev`, `docs`.

---

## 4. Build the frontend

```bash
cd flowyml_notebook/frontend
npm install          # first time only
npm run build        # outputs to flowyml_notebook/frontend/dist/
cd ../..
```

The `dist/` folder is force-included in the wheel even though it is listed in
`.gitignore`. Always rebuild before packaging.

---

## 5. Run the test suite

```bash
# Fast standalone suite (no heavy deps)
python tests/run_tests.py

# Full pytest suite (262 tests)
python -m pytest tests/ -v --tb=short

# Quiet summary only
python -m pytest tests/ -q
```

All 262 tests must pass with 0 warnings before release.

---

## 6. Start the server (two modes)

### 6a. Production mode — single port, serves built frontend

```bash
python -m flowyml_notebook.cli start
# or via the CLI entry point (after pip install):
fml-notebook start
```

Opens at **http://localhost:8899** by default.

Options:

```bash
fml-notebook start \
  --port 8899 \
  --file path/to/notebook.py \   # optional: load an existing notebook
  --no-browser                   # skip auto-open
```

### 6b. Dev mode — hot reload (Vite on 3000, API on 8899)

Requires Node.js to be available. The CLI launches both servers automatically.

```bash
fml-notebook dev
# or
fml-notebook dev --frontend-port 3000 --backend-port 8899
```

Point browser to **http://localhost:3000** (Vite proxies API calls to 8899).

---

## 7. Smoke-test the running server

With the server running, verify the key API endpoints:

```bash
BASE=http://localhost:8899

# Health check
curl -s $BASE/api/health | python3 -m json.tool

# List notebooks
curl -s $BASE/api/notebooks | python3 -m json.tool

# Recipes
curl -s $BASE/api/recipes | python3 -m json.tool

# Snippet categories
curl -s $BASE/api/snippets | python3 -m json.tool
```

Expected: all return `200 OK` with valid JSON.

---

## 8. Build the distributable wheel

```bash
pip install build            # one-time
python -m build --wheel
```

Output: `dist/flowyml_notebook-<version>-py3-none-any.whl`

Test the wheel in a clean environment:

```bash
python3 -m venv /tmp/test-fml
/tmp/test-fml/bin/pip install dist/flowyml_notebook-*.whl
/tmp/test-fml/bin/fml-notebook start --no-browser
```

---

## 9. Full pre-release checklist

```bash
# 1. Fix any issues, then:
source .venv/bin/activate

# 2. Build frontend
cd flowyml_notebook/frontend && npm run build && cd ../..

# 3. All tests green, zero warnings
python -m pytest tests/ -q

# 4. Build wheel
python -m build --wheel

# 5. Commit & push
git add -A
git commit -m "chore: pre-release build"
git push
```

---

## 10. Makefile shortcuts

The `Makefile` wraps the above steps:

| Command | What it does |
|---------|-------------|
| `make setup` | Install Python package + frontend deps |
| `make build` | Build frontend only |
| `make test` | Run standalone test script |
| `make test-pytest` | Run full pytest suite |
| `make dev` | Launch dev server (hot reload) |
| `make start` | Launch production server |
| `make clean` | Delete `dist/` build artifacts |

Example:

```bash
make setup    # once
make build    # after any JSX/CSS change
make test     # before every commit
make start    # to test the full stack
```

---

## Project structure quick-reference

```
flowyml_notebook/
├── cli.py              ← CLI entry point (fml-notebook command)
├── server.py           ← FastAPI backend (all /api/* routes)
├── reporting.py        ← HTML/PDF report generation
├── cells.py            ← Notebook data model
├── reactive.py         ← DAG & dependency engine
├── kernel.py           ← Python execution kernel
├── frontend/
│   ├── src/            ← React source (JSX + CSS)
│   ├── dist/           ← Built bundle (committed via force-include)
│   ├── package.json
│   └── vite.config.js
tests/
├── run_tests.py        ← Standalone fast tests
├── test_cells.py
├── test_core.py
├── test_reactive.py
└── ...                 ← 262 tests total
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | `pip install -e ".[dev,sql,ai,exploration]"` |
| `ReferenceError: X is not defined` (browser) | Rebuild frontend: `cd flowyml_notebook/frontend && npm run build` |
| `AttributeError: 'CellOutput' has no .get()` | Update `reporting.py` — use `getattr(o, "output_type", "")` |
| Pandas `Pandas4Warning` on `select_dtypes` | Add `"str"` to include list: `["object", "str", "category"]` |
| Port 8899 already in use | `fml-notebook start --port 9000` |
| Tests fail after dependency update | `pip install -e ".[dev]" --upgrade` |
