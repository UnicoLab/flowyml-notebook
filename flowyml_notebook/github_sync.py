"""GitHub-based collaboration backend for FlowyML Notebook.

Uses git/gh CLI commands to manage a standardized repository structure
that serves as the backend for team collaboration, versioning, and
shared recipe catalogs — no database required.

Repository structure:
    .flowyml-hub/
    ├── notebooks/{project}/{experiment}/
    │   ├── notebook.fml.json
    │   └── metadata.json
    ├── recipes/
    │   ├── catalog.json
    │   └── {category}/{recipe-name}.json
    └── config.json
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default local config location
CONFIG_DIR = Path.home() / ".flowyml"
GITHUB_CONFIG_FILE = CONFIG_DIR / "github.json"

# Repo-level directory names
HUB_DIR = ".flowyml-hub"
NOTEBOOKS_DIR = "notebooks"
RECIPES_DIR = "recipes"
CATALOG_FILE = "catalog.json"
CONFIG_FILE = "config.json"


def _run_cmd(
    args: list[str],
    cwd: str | None = None,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command, raising on failure if check=True."""
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=check,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"Command not found: {args[0]}. "
            "Ensure git (and optionally gh) are installed."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out: {' '.join(args)}")


class GitHubSync:
    """Manages synchronization between local notebooks and a GitHub repository.

    Usage:
        sync = GitHubSync()
        sync.init_repo("https://github.com/team/flowyml-notebooks")
        sync.push_notebook("my-project", "experiment-1", notebook_data)
        sync.pull_notebook("my-project", "experiment-1")
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else GITHUB_CONFIG_FILE
        self.config: dict[str, Any] = self._load_config()

    # ── Configuration ──────────────────────────────────────────────────

    def _load_config(self) -> dict[str, Any]:
        """Load local GitHub sync configuration."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"repos": {}, "default_repo": None, "user": None}

    def _save_config(self) -> None:
        """Persist configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2), encoding="utf-8"
        )

    @property
    def repo_path(self) -> Path | None:
        """Get the local clone path of the default repository."""
        default = self.config.get("default_repo")
        if default and default in self.config.get("repos", {}):
            return Path(self.config["repos"][default]["local_path"])
        return None

    @property
    def hub_path(self) -> Path | None:
        """Get the .flowyml-hub directory inside the repo."""
        rp = self.repo_path
        return rp / HUB_DIR if rp else None

    # ── Repository Initialization ──────────────────────────────────────

    def init_repo(
        self,
        repo_url: str,
        local_path: str | None = None,
        flowyml_url: str | None = None,
    ) -> dict[str, Any]:
        """Initialize or connect to a GitHub repository.

        If the repo already exists locally, it will be reused.
        If not, it will be cloned. Missing hub structure is created.

        Args:
            repo_url: GitHub repository URL (HTTPS or SSH).
            local_path: Where to clone locally. Defaults to ~/.flowyml/repos/<name>.
            flowyml_url: Optional FlowyML server URL to store in repo config.

        Returns:
            Dict with repo info.
        """
        # Derive repo name
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        if not local_path:
            local_path = str(CONFIG_DIR / "repos" / repo_name)

        local = Path(local_path)

        # Clone or verify existing
        if not local.exists():
            logger.info(f"Cloning {repo_url} → {local}")
            _run_cmd(["git", "clone", repo_url, str(local)])
        elif not (local / ".git").exists():
            # Directory exists but isn't a git repo — init it
            _run_cmd(["git", "init"], cwd=str(local))
            _run_cmd(["git", "remote", "add", "origin", repo_url], cwd=str(local))
        else:
            logger.info(f"Repository already exists at {local}")

        # Create hub structure
        hub = local / HUB_DIR
        for subdir in [NOTEBOOKS_DIR, RECIPES_DIR]:
            (hub / subdir).mkdir(parents=True, exist_ok=True)

        # Create repo-level config
        config_file = hub / CONFIG_FILE
        if not config_file.exists():
            repo_config = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "flowyml_server": flowyml_url or "",
                "default_branch": "main",
            }
            config_file.write_text(json.dumps(repo_config, indent=2), encoding="utf-8")

        # Create initial recipe catalog
        catalog_file = hub / RECIPES_DIR / CATALOG_FILE
        if not catalog_file.exists():
            catalog_file.write_text(
                json.dumps({"recipes": [], "updated_at": datetime.now().isoformat()}, indent=2),
                encoding="utf-8",
            )

        # Detect current user
        user = self._get_git_user(str(local))

        # Save to local config
        self.config.setdefault("repos", {})[repo_name] = {
            "url": repo_url,
            "local_path": str(local),
            "flowyml_url": flowyml_url or "",
        }
        self.config["default_repo"] = repo_name
        self.config["user"] = user
        self._save_config()

        return {
            "repo": repo_name,
            "url": repo_url,
            "local_path": str(local),
            "user": user,
            "hub_created": True,
        }

    # ── Status & Branches ──────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get git status for the current repository."""
        rp = self.repo_path
        if not rp or not rp.exists():
            return {"connected": False, "error": "No repository configured"}

        try:
            # Current branch
            branch_result = _run_cmd(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(rp),
            )
            branch = branch_result.stdout.strip()

            # Status (porcelain for machine-readable)
            status_result = _run_cmd(["git", "status", "--porcelain"], cwd=str(rp))
            changes = []
            for line in status_result.stdout.strip().split("\n"):
                if line.strip():
                    status_code = line[:2].strip()
                    filepath = line[3:].strip()
                    changes.append({"status": status_code, "file": filepath})

            # Last commit
            log_result = _run_cmd(
                ["git", "log", "-1", "--format=%H|%s|%ai|%an"],
                cwd=str(rp),
                check=False,
            )
            last_commit = None
            if log_result.returncode == 0 and log_result.stdout.strip():
                parts = log_result.stdout.strip().split("|", 3)
                if len(parts) >= 4:
                    last_commit = {
                        "sha": parts[0][:8],
                        "message": parts[1],
                        "date": parts[2],
                        "author": parts[3],
                    }

            return {
                "connected": True,
                "branch": branch,
                "changes": changes,
                "has_changes": len(changes) > 0,
                "last_commit": last_commit,
                "repo": self.config.get("default_repo"),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def list_branches(self) -> dict[str, Any]:
        """List all branches (local + remote)."""
        rp = self.repo_path
        if not rp or not rp.exists():
            return {"branches": [], "current": None}

        try:
            result = _run_cmd(["git", "branch", "-a", "--format=%(refname:short)"], cwd=str(rp))
            branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]

            current = _run_cmd(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(rp)
            ).stdout.strip()

            return {"branches": branches, "current": current}
        except Exception as e:
            return {"branches": [], "current": None, "error": str(e)}

    def create_branch(self, name: str, checkout: bool = True) -> dict[str, Any]:
        """Create a new branch and optionally switch to it."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            if checkout:
                _run_cmd(["git", "checkout", "-b", name], cwd=str(rp))
            else:
                _run_cmd(["git", "branch", name], cwd=str(rp))
            return {"branch": name, "checked_out": checkout}
        except Exception as e:
            return {"error": str(e)}

    def switch_branch(self, name: str) -> dict[str, Any]:
        """Switch to an existing branch."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            _run_cmd(["git", "checkout", name], cwd=str(rp))
            return {"branch": name, "switched": True}
        except Exception as e:
            return {"error": str(e)}

    # ── Notebook Sync ──────────────────────────────────────────────────

    def push_notebook(
        self,
        project: str,
        experiment: str,
        notebook_data: dict[str, Any],
        message: str | None = None,
    ) -> dict[str, Any]:
        """Save and push a notebook to the GitHub repository.

        Args:
            project: Project name (directory level 1).
            experiment: Experiment name (directory level 2).
            notebook_data: Full notebook JSON data.
            message: Commit message.

        Returns:
            Push result info.
        """
        hub = self.hub_path
        if not hub:
            return {"error": "No repository configured"}

        # Create directory structure
        nb_dir = hub / NOTEBOOKS_DIR / _safe_name(project) / _safe_name(experiment)
        nb_dir.mkdir(parents=True, exist_ok=True)

        # Write notebook file
        nb_file = nb_dir / "notebook.fml.json"
        nb_file.write_text(json.dumps(notebook_data, indent=2), encoding="utf-8")

        # Write metadata
        meta_file = nb_dir / "metadata.json"
        meta = {
            "project": project,
            "experiment": experiment,
            "updated_at": datetime.now().isoformat(),
            "updated_by": self.config.get("user", {}).get("name", "unknown"),
            "cell_count": len(notebook_data.get("cells", [])),
        }
        if meta_file.exists():
            try:
                existing = json.loads(meta_file.read_text(encoding="utf-8"))
                meta["created_at"] = existing.get("created_at", meta["updated_at"])
                meta["version"] = existing.get("version", 0) + 1
            except Exception:
                meta["created_at"] = meta["updated_at"]
                meta["version"] = 1
        else:
            meta["created_at"] = meta["updated_at"]
            meta["version"] = 1

        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # Git add + commit + push
        rp = str(self.repo_path)
        commit_msg = message or f"Update {project}/{experiment} notebook"
        try:
            _run_cmd(["git", "add", str(nb_dir)], cwd=rp)
            _run_cmd(["git", "commit", "-m", commit_msg], cwd=rp, check=False)
            push_result = _run_cmd(["git", "push"], cwd=rp, check=False)

            return {
                "pushed": push_result.returncode == 0,
                "project": project,
                "experiment": experiment,
                "version": meta["version"],
                "message": commit_msg,
                "error": push_result.stderr if push_result.returncode != 0 else None,
            }
        except Exception as e:
            return {"pushed": False, "error": str(e)}

    def pull_notebook(
        self, project: str, experiment: str
    ) -> dict[str, Any] | None:
        """Pull and load a notebook from the GitHub repository.

        Returns:
            Notebook data dict, or None if not found.
        """
        hub = self.hub_path
        if not hub:
            return None

        # Pull latest
        rp = str(self.repo_path)
        _run_cmd(["git", "pull", "--rebase"], cwd=rp, check=False)

        nb_file = hub / NOTEBOOKS_DIR / _safe_name(project) / _safe_name(experiment) / "notebook.fml.json"
        if not nb_file.exists():
            return None

        try:
            data = json.loads(nb_file.read_text(encoding="utf-8"))
            return data
        except Exception:
            return None

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in the repository."""
        hub = self.hub_path
        if not hub:
            return []

        nb_root = hub / NOTEBOOKS_DIR
        if not nb_root.exists():
            return []

        projects = []
        for project_dir in sorted(nb_root.iterdir()):
            if not project_dir.is_dir():
                continue
            experiments = []
            for exp_dir in sorted(project_dir.iterdir()):
                if not exp_dir.is_dir():
                    continue
                meta_file = exp_dir / "metadata.json"
                meta = {}
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                experiments.append({
                    "name": exp_dir.name,
                    "updated_at": meta.get("updated_at"),
                    "updated_by": meta.get("updated_by"),
                    "cell_count": meta.get("cell_count", 0),
                    "version": meta.get("version", 1),
                })
            projects.append({
                "name": project_dir.name,
                "experiments": experiments,
                "count": len(experiments),
            })

        return projects

    # ── Recipe Sync ────────────────────────────────────────────────────

    def push_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """Push a recipe to the shared catalog.

        Args:
            recipe: Recipe dict with id, name, category, source, etc.

        Returns:
            Result info.
        """
        hub = self.hub_path
        if not hub:
            return {"error": "No repository configured"}

        category = _safe_name(recipe.get("category", "custom"))
        recipe_dir = hub / RECIPES_DIR / category
        recipe_dir.mkdir(parents=True, exist_ok=True)

        # Save recipe file
        recipe_id = _safe_name(recipe.get("id", recipe.get("name", "untitled")))
        recipe_file = recipe_dir / f"{recipe_id}.json"
        recipe_data = {
            **recipe,
            "shared": True,
            "shared_by": self.config.get("user", {}).get("name", "unknown"),
            "shared_at": datetime.now().isoformat(),
        }
        recipe_file.write_text(json.dumps(recipe_data, indent=2), encoding="utf-8")

        # Update catalog index
        catalog_file = hub / RECIPES_DIR / CATALOG_FILE
        catalog = {"recipes": [], "updated_at": datetime.now().isoformat()}
        if catalog_file.exists():
            try:
                catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Update or add entry
        existing = [r for r in catalog["recipes"] if r.get("id") != recipe.get("id")]
        existing.append({
            "id": recipe.get("id"),
            "name": recipe.get("name"),
            "category": recipe.get("category"),
            "description": recipe.get("description", ""),
            "tags": recipe.get("tags", []),
            "shared_by": recipe_data["shared_by"],
            "shared_at": recipe_data["shared_at"],
        })
        catalog["recipes"] = existing
        catalog["updated_at"] = datetime.now().isoformat()
        catalog_file.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

        # Commit + push
        rp = str(self.repo_path)
        try:
            _run_cmd(["git", "add", str(hub / RECIPES_DIR)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Share recipe: {recipe.get('name', 'untitled')}"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)
            return {"shared": True, "recipe_id": recipe.get("id")}
        except Exception as e:
            return {"shared": False, "error": str(e)}

    def pull_recipes(self) -> list[dict[str, Any]]:
        """Pull shared recipes from the repository.

        Returns:
            List of recipe dicts.
        """
        hub = self.hub_path
        if not hub:
            return []

        # Pull latest
        rp = str(self.repo_path)
        _run_cmd(["git", "pull", "--rebase"], cwd=rp, check=False)

        recipes = []
        recipes_root = hub / RECIPES_DIR
        if not recipes_root.exists():
            return []

        for category_dir in recipes_root.iterdir():
            if not category_dir.is_dir():
                continue
            for recipe_file in category_dir.glob("*.json"):
                try:
                    recipe = json.loads(recipe_file.read_text(encoding="utf-8"))
                    recipe["shared"] = True
                    recipes.append(recipe)
                except Exception:
                    continue

        return recipes

    def get_recipe_catalog(self) -> dict[str, Any]:
        """Get the shared recipe catalog (index only, no full source)."""
        hub = self.hub_path
        if not hub:
            return {"recipes": []}

        catalog_file = hub / RECIPES_DIR / CATALOG_FILE
        if not catalog_file.exists():
            return {"recipes": []}

        try:
            return json.loads(catalog_file.read_text(encoding="utf-8"))
        except Exception:
            return {"recipes": []}

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _get_git_user(repo_path: str) -> dict[str, str]:
        """Get current git user info."""
        name = ""
        email = ""
        try:
            r = _run_cmd(["git", "config", "user.name"], cwd=repo_path, check=False)
            name = r.stdout.strip()
        except Exception:
            pass
        try:
            r = _run_cmd(["git", "config", "user.email"], cwd=repo_path, check=False)
            email = r.stdout.strip()
        except Exception:
            pass
        return {"name": name, "email": email}

    def get_config(self) -> dict[str, Any]:
        """Get the current sync configuration."""
        return {
            "repos": self.config.get("repos", {}),
            "default_repo": self.config.get("default_repo"),
            "user": self.config.get("user"),
            "connected": self.repo_path is not None and self.repo_path.exists(),
        }


def _safe_name(name: str) -> str:
    """Sanitize a name for use as a directory/file name."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(".", "-")
        .strip("-")
    )
