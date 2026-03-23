# :handshake: Collaboration

FlowyML Notebook uses **GitHub** as its collaboration backend. No proprietary cloud, no database, no account signup — just a shared Git repository that your team already knows how to use.

---

## Why GitHub?

!!! info "Design Philosophy"
    Most notebook platforms require a cloud database for collaboration. FlowyML Notebook takes a different approach: **your team's GitHub repository IS the collaboration backend**. This means:

    - **Zero infrastructure** — No servers to maintain, no databases to back up
    - **Native Git workflows** — Branch, merge, review, and resolve conflicts with tools you already know
    - **Full ownership** — Your notebooks, recipes, and metadata live in your own repository
    - **Offline-first** — Work locally, sync when you're ready

---

## Getting Started

### Step 1: Connect a Repository

Open the **Git** tab in the sidebar and enter your GitHub repository URL (HTTPS or SSH).

<figure markdown>
  ![GitHub Integration](screenshots/github.png){ width="50%" }
  <figcaption>Connect any GitHub repository — HTTPS or SSH — from the sidebar Git panel</figcaption>
</figure>

FlowyML will either **clone** the repository (if it's new) or **reuse** an existing local clone. The connection is stored locally at `~/.flowyml/github.json`.

```bash
# Or connect via CLI
fml-notebook start --server https://your-flowyml-instance.com
```

### Step 2: Start Collaborating

Once connected, FlowyML creates a `.flowyml-hub` directory inside the repository. This is the lightweight sync layer that powers all collaboration features:

```
your-repo/
├── .flowyml-hub/
│   ├── notebooks/              # Shared notebooks
│   │   └── {project}/
│   │       └── {experiment}/
│   │           ├── notebook.fml.json    # Full notebook data
│   │           └── metadata.json        # Version, author, cell count
│   ├── recipes/                # Shared recipe catalog
│   │   ├── catalog.json        # Recipe index
│   │   └── {category}/
│   │       └── {recipe-name}.json
│   └── config.json             # Hub settings (version, FlowyML server URL)
├── your-notebooks.py           # Your .py notebook files
└── ...
```

---

## Push & Pull Notebooks

### Push

Save your notebook to the shared repository:

1. Make your changes in the notebook editor
2. Open the **Git** panel in the sidebar
3. Click **Push** — this commits your notebook as `notebook.fml.json` with metadata and pushes to GitHub

Every push automatically tracks:

- **Version number** — Incrementing counter per notebook
- **Timestamp** — When the push occurred
- **Author** — The Git user who pushed
- **Cell count** — Number of cells in the notebook

### Pull

Get the latest version from your teammates:

1. Open the **Git** panel
2. Click **Pull** — this runs `git pull --rebase` and loads the latest notebook state

!!! tip "Conflict Resolution"
    Since notebooks are stored as JSON (and your `.py` files are pure Python), Git handles conflict resolution natively. No proprietary merge tools needed.

---

## Branching & Experiments

Use Git branches to isolate experiments — just like feature branches in software development.

### Create a Branch

From the notebook sidebar:

1. Open the **Git** panel
2. Click **New Branch** → Enter a name (e.g., `experiment/custom-loss`)
3. FlowyML switches to the new branch automatically

### Switch Branches

Toggle between branches to compare different experiment versions or switch contexts between team members' work.

### Merge Results

When your experiment succeeds, merge it back to `main` using your existing Git workflow (GitHub PRs, CLI, etc.).

```bash
# Example workflow
git checkout -b experiment/new-model
# ... work in FlowyML Notebook ...
git push origin experiment/new-model
# → Open a PR on GitHub → Review → Merge
```

---

## Version History & Snapshots

<figure markdown>
  ![History & Snapshots](screenshots/snapshots.png){ width="50%" }
  <figcaption>Browse notebook history with snapshot timestamps, cell counts, and restore options</figcaption>
</figure>

FlowyML saves **snapshots** of your notebook at key moments:

- **Manual snapshots** — Save a checkpoint whenever you want
- **Auto-save on push** — Every push creates a versioned snapshot
- **Cell-level diffs** — See exactly which cells changed between versions

### Browsing History

1. Open the **History** tab in the sidebar
2. Browse snapshots sorted by timestamp
3. Click any snapshot to see the notebook state at that point
4. **Restore** a previous version with one click

---

## Shared Recipes

Turn your best code patterns into **shared team recipes** — reusable templates that every teammate can access.

<figure markdown>
  ![Recipes Panel](screenshots/recipies.png){ width="60%" }
  <figcaption>39 built-in recipes plus your team's custom shared catalog</figcaption>
</figure>

### Push a Recipe

1. Write a cell with a useful pattern
2. Click **"Save as Recipe"** in the cell toolbar
3. Set a **Name**, **Category**, and **Description**
4. Toggle **"Share to Hub"** → The recipe is committed and pushed to your GitHub repository

Shared recipes appear in the **Shared** tab of the Recipes panel for all team members.

### Pull Team Recipes

When a teammate shares a recipe, just click **Pull** in the Git panel. The shared recipe catalog refreshes automatically:

```
.flowyml-hub/recipes/
├── catalog.json                 # Auto-generated index
├── core/
│   └── flowyml-step.json
├── ml/
│   └── xgboost-baseline.json
└── data/
    └── s3-data-loader.json
```

Each recipe in the catalog tracks:

| Field | Description |
|-------|------------|
| `name` | Recipe display name |
| `category` | Organizational category (Core, ML, Data, etc.) |
| `description` | What the recipe does |
| `tags` | Searchable tags |
| `shared_by` | Git user who shared it |
| `shared_at` | Timestamp of sharing |

---

## Comments & Review

<figure markdown>
  ![Comments](screenshots/comments.png){ width="100%" }
  <figcaption>Inline comments panel with threaded discussions, resolve/reply, and direct cell annotation</figcaption>
</figure>

Collaborate in context with **inline comments**:

- **Notebook-level comments** — General discussion about the analysis
- **Cell-level annotations** — Target specific code, outputs, or data
- **Threaded replies** — Keep conversations organized
- **Resolve** — Mark completed discussions to declutter

---

## Projects & Organization

FlowyML organizes shared notebooks into a **project → experiment** hierarchy:

```python
# Conceptual structure
.flowyml-hub/notebooks/
├── fraud-detection/
│   ├── baseline-xgboost/
│   ├── feature-engineering-v2/
│   └── production-model/
├── recommendation-engine/
│   ├── collaborative-filtering/
│   └── content-based/
└── data-quality/
    └── monthly-report/
```

### Listing Projects

The sidebar shows all projects and experiments from the shared repository, with metadata:

| Metadata | Description |
|----------|------------|
| **Experiment name** | Directory name in the hub |
| **Last updated** | Timestamp of most recent push |
| **Updated by** | Git username of last author |
| **Cell count** | Number of cells in the notebook |
| **Version** | Incrementing version counter |

---

## Complete Workflow Example

Here's a typical team collaboration workflow:

```mermaid
graph LR
    A[Create Notebook] --> B[Connect GitHub Repo]
    B --> C[Create Branch]
    C --> D[Develop & Experiment]
    D --> E[Push Notebook]
    E --> F[Share Recipes]
    F --> G[Open PR on GitHub]
    G --> H[Team Review]
    H --> I[Merge to Main]
    I --> J[Teammates Pull]
```

**Step-by-step:**

1. :pencil2: **Create** a new notebook in FlowyML
2. :link: **Connect** to your team's GitHub repository
3. :twisted_rightwards_arrows: **Branch** — Create `experiment/my-analysis`
4. :test_tube: **Develop** — Write, run, iterate with reactive execution
5. :arrow_up: **Push** — Commit notebook + metadata to GitHub
6. :cook: **Share** — Push useful patterns as shared recipes
7. :mag: **Review** — Open a PR on GitHub for team review
8. :white_check_mark: **Merge** — After approval, merge to `main`
9. :arrow_down: **Pull** — Teammates pull the latest notebooks and recipes

!!! info "No Git Knowledge Required"
    While power users can use Git directly, the sidebar UI handles all Git operations (push, pull, branch, switch) with one click. Your data scientists don't need to know Git internals.
