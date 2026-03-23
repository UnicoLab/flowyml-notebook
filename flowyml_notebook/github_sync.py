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
    ├── comments/
    │   └── {notebook-hash}.json
    ├── reviews/
    │   └── {notebook-hash}.json
    ├── presence.json
    └── config.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import uuid as _uuid
from datetime import datetime, timedelta
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
COMMENTS_DIR = "comments"
REVIEWS_DIR = "reviews"
CATALOG_FILE = "catalog.json"
CONFIG_FILE = "config.json"
PRESENCE_FILE = "presence.json"


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


def _notebook_hash(project: str, experiment: str) -> str:
    """Generate a stable hash for a notebook path (used as comment/review filename)."""
    key = f"{project}/{experiment}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class GitHubSync:
    """Manages synchronization between local notebooks and a GitHub repository.

    Provides:
    - Notebook push/pull with metadata tracking
    - Git-persisted comments & reviews
    - Merge conflict detection and resolution
    - Team activity feed
    - Collaborative presence indicators
    - Recipe ratings, forking, and version history

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

        # Create hub structure (including new dirs)
        hub = local / HUB_DIR
        for subdir in [NOTEBOOKS_DIR, RECIPES_DIR, COMMENTS_DIR, REVIEWS_DIR]:
            (hub / subdir).mkdir(parents=True, exist_ok=True)

        # Create repo-level config
        config_file = hub / CONFIG_FILE
        if not config_file.exists():
            repo_config = {
                "version": "2.0",
                "created_at": datetime.now().isoformat(),
                "flowyml_server": flowyml_url or "",
                "default_branch": "main",
                "features": {
                    "comments": True,
                    "reviews": True,
                    "presence": True,
                    "recipe_ratings": True,
                },
            }
            config_file.write_text(json.dumps(repo_config, indent=2), encoding="utf-8")

        # Create initial recipe catalog
        catalog_file = hub / RECIPES_DIR / CATALOG_FILE
        if not catalog_file.exists():
            catalog_file.write_text(
                json.dumps({"recipes": [], "updated_at": datetime.now().isoformat()}, indent=2),
                encoding="utf-8",
            )

        # Initialize presence file
        presence_file = hub / PRESENCE_FILE
        if not presence_file.exists():
            presence_file.write_text(
                json.dumps({"editors": [], "updated_at": datetime.now().isoformat()}, indent=2),
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

    def delete_branch(self, name: str, force: bool = False) -> dict[str, Any]:
        """Delete a local branch."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            flag = "-D" if force else "-d"
            _run_cmd(["git", "branch", flag, name], cwd=str(rp))
            return {"deleted": name}
        except Exception as e:
            return {"error": str(e)}

    # ── Merge Conflict Detection & Resolution ──────────────────────────

    def check_merge_status(self) -> dict[str, Any]:
        """Check for upstream changes before push.

        Returns ahead/behind counts and whether a merge is needed.
        """
        rp = self.repo_path
        if not rp or not rp.exists():
            return {"error": "No repository configured"}

        try:
            # Fetch updates without merging
            _run_cmd(["git", "fetch", "origin"], cwd=str(rp), check=False)

            branch = _run_cmd(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(rp)
            ).stdout.strip()

            # Count ahead/behind
            result = _run_cmd(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{branch}"],
                cwd=str(rp),
                check=False,
            )

            ahead = 0
            behind = 0
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])

            status = "up-to-date"
            if ahead > 0 and behind > 0:
                status = "diverged"
            elif ahead > 0:
                status = "ahead"
            elif behind > 0:
                status = "behind"

            return {
                "branch": branch,
                "ahead": ahead,
                "behind": behind,
                "status": status,
                "needs_pull": behind > 0,
                "can_push": behind == 0 and ahead > 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def pull_with_rebase(self) -> dict[str, Any]:
        """Pull with rebase — safer for collaboration."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            result = _run_cmd(["git", "pull", "--rebase"], cwd=str(rp), check=False)
            if result.returncode != 0:
                # Check if there's a conflict
                if "CONFLICT" in (result.stdout + result.stderr):
                    return {
                        "success": False,
                        "conflict": True,
                        "message": "Merge conflict detected. Resolve manually or abort.",
                        "details": result.stderr,
                    }
                return {"success": False, "error": result.stderr}
            return {"success": True, "message": "Pulled and rebased successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stash_changes(self, message: str | None = None) -> dict[str, Any]:
        """Stash local changes (work-in-progress)."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            args = ["git", "stash", "push"]
            if message:
                args.extend(["-m", message])
            result = _run_cmd(args, cwd=str(rp), check=False)
            stashed = "No local changes to save" not in result.stdout
            return {"stashed": stashed, "message": result.stdout.strip()}
        except Exception as e:
            return {"error": str(e)}

    def pop_stash(self) -> dict[str, Any]:
        """Pop the most recent stash."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            result = _run_cmd(["git", "stash", "pop"], cwd=str(rp), check=False)
            if result.returncode != 0:
                return {"success": False, "error": result.stderr}
            return {"success": True, "message": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_stashes(self) -> list[dict[str, str]]:
        """List all stashes."""
        rp = self.repo_path
        if not rp:
            return []

        try:
            result = _run_cmd(
                ["git", "stash", "list", "--format=%gd|%gs|%ci"],
                cwd=str(rp), check=False,
            )
            stashes = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                stashes.append({
                    "ref": parts[0] if len(parts) > 0 else "",
                    "message": parts[1] if len(parts) > 1 else "",
                    "date": parts[2] if len(parts) > 2 else "",
                })
            return stashes
        except Exception:
            return []

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

    # ── Git-Persisted Comments ─────────────────────────────────────────

    def _comments_file(self, project: str, experiment: str) -> Path | None:
        """Get the comments JSON file path for a notebook."""
        hub = self.hub_path
        if not hub:
            return None
        comments_dir = hub / COMMENTS_DIR
        comments_dir.mkdir(parents=True, exist_ok=True)
        nb_hash = _notebook_hash(project, experiment)
        return comments_dir / f"{nb_hash}.json"

    def push_comments(
        self,
        project: str,
        experiment: str,
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist comments to git and push."""
        cf = self._comments_file(project, experiment)
        if not cf:
            return {"error": "No repository configured"}

        data = {
            "notebook": f"{project}/{experiment}",
            "comments": comments,
            "updated_at": datetime.now().isoformat(),
        }
        cf.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Commit
        rp = str(self.repo_path)
        try:
            _run_cmd(["git", "add", str(cf)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Update comments for {project}/{experiment}"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)
            return {"synced": True, "count": len(comments)}
        except Exception as e:
            return {"synced": False, "error": str(e)}

    def pull_comments(
        self, project: str, experiment: str
    ) -> list[dict[str, Any]]:
        """Pull comments from the repo for a notebook."""
        cf = self._comments_file(project, experiment)
        if not cf:
            return []

        # Pull latest
        rp = str(self.repo_path)
        _run_cmd(["git", "pull", "--rebase"], cwd=rp, check=False)

        if not cf.exists():
            return []

        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            return data.get("comments", [])
        except Exception:
            return []

    def merge_comments(
        self,
        local: list[dict[str, Any]],
        remote: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge local and remote comments by ID (union merge)."""
        merged: dict[str, dict] = {}
        for c in remote:
            if c.get("id"):
                merged[c["id"]] = c
        for c in local:
            cid = c.get("id")
            if not cid:
                continue
            if cid in merged:
                # Local takes priority for edits; merge replies
                remote_c = merged[cid]
                local_replies = set(json.dumps(r) for r in c.get("replies", []))
                remote_replies = set(json.dumps(r) for r in remote_c.get("replies", []))
                all_replies = local_replies | remote_replies
                c["replies"] = [json.loads(r) for r in sorted(all_replies)]
                merged[cid] = c
            else:
                merged[cid] = c

        # Sort by created_at
        result = list(merged.values())
        result.sort(key=lambda x: x.get("created_at", ""))
        return result

    # ── Git-Persisted Reviews ──────────────────────────────────────────

    def _reviews_file(self, project: str, experiment: str) -> Path | None:
        """Get the reviews JSON file path for a notebook."""
        hub = self.hub_path
        if not hub:
            return None
        reviews_dir = hub / REVIEWS_DIR
        reviews_dir.mkdir(parents=True, exist_ok=True)
        nb_hash = _notebook_hash(project, experiment)
        return reviews_dir / f"{nb_hash}.json"

    def push_review(
        self,
        project: str,
        experiment: str,
        review: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist a review request to git and push."""
        rf = self._reviews_file(project, experiment)
        if not rf:
            return {"error": "No repository configured"}

        # Load existing reviews
        existing: list[dict] = []
        if rf.exists():
            try:
                data = json.loads(rf.read_text(encoding="utf-8"))
                existing = data.get("reviews", [])
            except Exception:
                pass

        # Add ID if missing
        if not review.get("id"):
            review["id"] = str(_uuid.uuid4())[:8]
        review.setdefault("created_at", datetime.now().isoformat())
        review.setdefault("status", "pending")

        # Update or append
        found = False
        for i, r in enumerate(existing):
            if r.get("id") == review["id"]:
                existing[i] = review
                found = True
                break
        if not found:
            existing.append(review)

        data = {
            "notebook": f"{project}/{experiment}",
            "reviews": existing,
            "updated_at": datetime.now().isoformat(),
        }
        rf.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Commit
        rp = str(self.repo_path)
        try:
            _run_cmd(["git", "add", str(rf)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Update review for {project}/{experiment}"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)
            return {"synced": True, "review_id": review["id"]}
        except Exception as e:
            return {"synced": False, "error": str(e)}

    def pull_reviews(
        self, project: str, experiment: str
    ) -> list[dict[str, Any]]:
        """Pull reviews from the repo for a notebook."""
        rf = self._reviews_file(project, experiment)
        if not rf:
            return []

        rp = str(self.repo_path)
        _run_cmd(["git", "pull", "--rebase"], cwd=rp, check=False)

        if not rf.exists():
            return []

        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            return data.get("reviews", [])
        except Exception:
            return []

    def update_review_status(
        self,
        project: str,
        experiment: str,
        review_id: str,
        status: str,
        reviewer_comment: str = "",
    ) -> dict[str, Any]:
        """Update review status (approved/changes_requested/rejected)."""
        rf = self._reviews_file(project, experiment)
        if not rf or not rf.exists():
            return {"error": "Review file not found"}

        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            reviews = data.get("reviews", [])
            for r in reviews:
                if r.get("id") == review_id:
                    r["status"] = status
                    r["reviewed_at"] = datetime.now().isoformat()
                    r["reviewer"] = self.config.get("user", {})
                    if reviewer_comment:
                        r["reviewer_comment"] = reviewer_comment
                    break

            data["reviews"] = reviews
            data["updated_at"] = datetime.now().isoformat()
            rf.write_text(json.dumps(data, indent=2), encoding="utf-8")

            # Commit
            rp = str(self.repo_path)
            _run_cmd(["git", "add", str(rf)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Review {status}: {project}/{experiment}"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)
            return {"updated": True, "status": status}
        except Exception as e:
            return {"error": str(e)}

    # ── Rich Commit History ────────────────────────────────────────────

    def get_commit_log(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get decorated commit history with author info and stats."""
        rp = self.repo_path
        if not rp or not rp.exists():
            return []

        try:
            result = _run_cmd(
                [
                    "git", "log", f"-{limit}",
                    "--format=%H|%h|%s|%ai|%an|%ae|%P",
                ],
                cwd=str(rp),
                check=False,
            )
            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 6)
                if len(parts) < 6:
                    continue

                sha_full = parts[0]
                author_name = parts[4]
                author_email = parts[5]
                parents = parts[6].split() if len(parts) > 6 else []

                # Generate consistent avatar hue from name
                hue = sum(ord(c) for c in author_name) * 37 % 360

                # Get file stats (insertions/deletions)
                stat_result = _run_cmd(
                    ["git", "diff", "--shortstat", f"{sha_full}~1", sha_full],
                    cwd=str(rp),
                    check=False,
                )
                insertions = 0
                deletions = 0
                files_changed = 0
                if stat_result.returncode == 0 and stat_result.stdout.strip():
                    stat_text = stat_result.stdout.strip()
                    import re
                    m = re.search(r"(\d+) file", stat_text)
                    if m:
                        files_changed = int(m.group(1))
                    m = re.search(r"(\d+) insertion", stat_text)
                    if m:
                        insertions = int(m.group(1))
                    m = re.search(r"(\d+) deletion", stat_text)
                    if m:
                        deletions = int(m.group(1))

                commits.append({
                    "sha": sha_full,
                    "sha_short": parts[1],
                    "message": parts[2],
                    "date": parts[3],
                    "author": {
                        "name": author_name,
                        "email": author_email,
                        "avatar_hue": hue,
                        "initials": author_name[0].upper() if author_name else "?",
                    },
                    "is_merge": len(parents) > 1,
                    "files_changed": files_changed,
                    "insertions": insertions,
                    "deletions": deletions,
                })

            return commits
        except Exception:
            return []

    def get_commit_diff_summary(self, commit_sha: str) -> dict[str, Any]:
        """Get cell-level change summary for a specific commit."""
        rp = self.repo_path
        if not rp:
            return {"error": "No repository configured"}

        try:
            # Get file list changed in commit
            result = _run_cmd(
                ["git", "diff-tree", "--no-commit-id", "-r", "--name-status", commit_sha],
                cwd=str(rp),
                check=False,
            )
            files = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    files.append({"status": parts[0], "file": parts[1]})

            return {
                "sha": commit_sha,
                "files": files,
                "cell_changes": [
                    f for f in files
                    if f["file"].endswith((".fml.json", ".json"))
                    and ".flowyml-hub" in f["file"]
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Team Activity Feed ─────────────────────────────────────────────

    def get_activity_feed(self, limit: int = 50) -> list[dict[str, Any]]:
        """Build a unified activity feed from commits, comments, and reviews."""
        feed: list[dict[str, Any]] = []

        # 1. Recent commits
        commits = self.get_commit_log(limit=limit)
        for c in commits:
            feed.append({
                "type": "commit",
                "timestamp": c["date"],
                "user": c["author"],
                "message": c["message"],
                "details": {
                    "sha": c["sha_short"],
                    "insertions": c["insertions"],
                    "deletions": c["deletions"],
                    "is_merge": c["is_merge"],
                },
            })

        # 2. Comment events from all comment files
        hub = self.hub_path
        if hub:
            comments_dir = hub / COMMENTS_DIR
            if comments_dir.exists():
                for cf in comments_dir.glob("*.json"):
                    try:
                        data = json.loads(cf.read_text(encoding="utf-8"))
                        nb = data.get("notebook", "unknown")
                        for comment in data.get("comments", []):
                            feed.append({
                                "type": "comment",
                                "timestamp": comment.get("created_at", ""),
                                "user": comment.get("author", {}),
                                "message": comment.get("text", "")[:100],
                                "details": {
                                    "notebook": nb,
                                    "cell_id": comment.get("cell_id"),
                                    "resolved": comment.get("resolved", False),
                                    "reply_count": len(comment.get("replies", [])),
                                },
                            })
                    except Exception:
                        continue

            # 3. Review events
            reviews_dir = hub / REVIEWS_DIR
            if reviews_dir.exists():
                for rf in reviews_dir.glob("*.json"):
                    try:
                        data = json.loads(rf.read_text(encoding="utf-8"))
                        nb = data.get("notebook", "unknown")
                        for review in data.get("reviews", []):
                            feed.append({
                                "type": "review",
                                "timestamp": review.get("created_at", ""),
                                "user": review.get("requested_by", {}),
                                "message": f"Review {review.get('status', 'pending')}",
                                "details": {
                                    "notebook": nb,
                                    "status": review.get("status", "pending"),
                                    "reviewers": review.get("reviewers", []),
                                },
                            })
                    except Exception:
                        continue

        # Sort by timestamp descending
        feed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return feed[:limit]

    # ── Collaborative Presence ─────────────────────────────────────────

    def set_editing_status(
        self,
        notebook_path: str,
        is_editing: bool = True,
    ) -> dict[str, Any]:
        """Update presence status for the current user."""
        hub = self.hub_path
        if not hub:
            return {"error": "No repository configured"}

        presence_file = hub / PRESENCE_FILE
        presence: dict[str, Any] = {"editors": [], "updated_at": ""}
        if presence_file.exists():
            try:
                presence = json.loads(presence_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        user = self.config.get("user", {})
        user_name = user.get("name", "unknown")

        # Remove stale entries (> 5 minutes old)
        now = datetime.now()
        cutoff = (now - timedelta(minutes=5)).isoformat()
        editors = [
            e for e in presence.get("editors", [])
            if e.get("last_seen", "") > cutoff and e.get("name") != user_name
        ]

        if is_editing:
            hue = sum(ord(c) for c in user_name) * 37 % 360
            editors.append({
                "name": user_name,
                "email": user.get("email", ""),
                "notebook": notebook_path,
                "last_seen": now.isoformat(),
                "avatar_hue": hue,
                "initials": user_name[0].upper() if user_name else "?",
            })

        presence["editors"] = editors
        presence["updated_at"] = now.isoformat()
        presence_file.write_text(json.dumps(presence, indent=2), encoding="utf-8")

        # Best-effort push (don't block on failure)
        rp = str(self.repo_path)
        try:
            _run_cmd(["git", "add", str(presence_file)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", "Update presence"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)
        except Exception:
            pass

        return {"editors": editors}

    def get_active_editors(self) -> list[dict[str, Any]]:
        """Get list of active editors (from the presence file)."""
        hub = self.hub_path
        if not hub:
            return []

        # Pull latest presence info
        rp = str(self.repo_path)
        _run_cmd(["git", "pull", "--rebase"], cwd=rp, check=False)

        presence_file = hub / PRESENCE_FILE
        if not presence_file.exists():
            return []

        try:
            data = json.loads(presence_file.read_text(encoding="utf-8"))
            editors = data.get("editors", [])

            # Filter stale entries (> 5 minutes)
            cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
            return [e for e in editors if e.get("last_seen", "") > cutoff]
        except Exception:
            return []

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

        # Preserve history
        history: list[dict] = []
        if recipe_file.exists():
            try:
                existing = json.loads(recipe_file.read_text(encoding="utf-8"))
                history = existing.get("version_history", [])
                # Snapshot current version
                history.append({
                    "version": existing.get("version", 1),
                    "updated_at": existing.get("shared_at", ""),
                    "updated_by": existing.get("shared_by", ""),
                })
            except Exception:
                pass

        recipe_data = {
            **recipe,
            "shared": True,
            "shared_by": self.config.get("user", {}).get("name", "unknown"),
            "shared_at": datetime.now().isoformat(),
            "version": len(history) + 1,
            "version_history": history,
            "ratings": recipe.get("ratings", {}),
            "fork_count": recipe.get("fork_count", 0),
            "forked_from": recipe.get("forked_from"),
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
            "version": recipe_data["version"],
            "avg_rating": _compute_avg_rating(recipe_data.get("ratings", {})),
            "fork_count": recipe_data.get("fork_count", 0),
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

    # ── Recipe Ratings & Forking ───────────────────────────────────────

    def rate_recipe(
        self, recipe_id: str, rating: int, category: str = "custom"
    ) -> dict[str, Any]:
        """Rate a shared recipe (1-5 stars).

        Ratings are stored per-user in the recipe file.
        """
        hub = self.hub_path
        if not hub:
            return {"error": "No repository configured"}

        # Find recipe file
        recipe_file = self._find_recipe_file(recipe_id)
        if not recipe_file:
            return {"error": f"Recipe {recipe_id} not found"}

        try:
            recipe = json.loads(recipe_file.read_text(encoding="utf-8"))
            user_name = self.config.get("user", {}).get("name", "anonymous")

            ratings = recipe.get("ratings", {})
            ratings[user_name] = {
                "score": max(1, min(5, rating)),
                "rated_at": datetime.now().isoformat(),
            }
            recipe["ratings"] = ratings

            recipe_file.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

            # Update catalog avg rating
            self._update_catalog_rating(recipe.get("id"), ratings)

            # Commit
            rp = str(self.repo_path)
            _run_cmd(["git", "add", str(recipe_file)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Rate recipe: {recipe.get('name', recipe_id)} ({rating}★)"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)

            return {
                "rated": True,
                "recipe_id": recipe_id,
                "rating": rating,
                "avg_rating": _compute_avg_rating(ratings),
                "total_ratings": len(ratings),
            }
        except Exception as e:
            return {"error": str(e)}

    def fork_recipe(
        self, recipe_id: str, new_name: str | None = None
    ) -> dict[str, Any]:
        """Fork a shared recipe to create a variant with attribution."""
        hub = self.hub_path
        if not hub:
            return {"error": "No repository configured"}

        recipe_file = self._find_recipe_file(recipe_id)
        if not recipe_file:
            return {"error": f"Recipe {recipe_id} not found"}

        try:
            original = json.loads(recipe_file.read_text(encoding="utf-8"))
            user_name = self.config.get("user", {}).get("name", "unknown")

            # Create forked recipe
            fork_id = f"fork-{recipe_id}-{str(_uuid.uuid4())[:6]}"
            forked = {
                **original,
                "id": fork_id,
                "name": new_name or f"{original.get('name', 'Recipe')} (fork)",
                "forked_from": {
                    "id": recipe_id,
                    "name": original.get("name"),
                    "author": original.get("shared_by"),
                },
                "shared_by": user_name,
                "shared_at": datetime.now().isoformat(),
                "version": 1,
                "version_history": [],
                "ratings": {},
                "fork_count": 0,
            }

            # Increment fork count on original
            original["fork_count"] = original.get("fork_count", 0) + 1
            recipe_file.write_text(json.dumps(original, indent=2), encoding="utf-8")

            # Save forked recipe
            category = _safe_name(forked.get("category", "custom"))
            fork_dir = hub / RECIPES_DIR / category
            fork_dir.mkdir(parents=True, exist_ok=True)
            fork_file = fork_dir / f"{_safe_name(fork_id)}.json"
            fork_file.write_text(json.dumps(forked, indent=2), encoding="utf-8")

            # Commit
            rp = str(self.repo_path)
            _run_cmd(["git", "add", str(hub / RECIPES_DIR)], cwd=rp)
            _run_cmd(
                ["git", "commit", "-m", f"Fork recipe: {original.get('name', '')} → {forked['name']}"],
                cwd=rp, check=False,
            )
            _run_cmd(["git", "push"], cwd=rp, check=False)

            return {
                "forked": True,
                "fork_id": fork_id,
                "original_id": recipe_id,
                "name": forked["name"],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_recipe_leaderboard(self) -> dict[str, Any]:
        """Get top-rated and most-used recipes."""
        hub = self.hub_path
        if not hub:
            return {"top_rated": [], "most_forked": []}

        catalog = self.get_recipe_catalog()
        recipes = catalog.get("recipes", [])

        # Sort by avg_rating
        top_rated = sorted(
            [r for r in recipes if r.get("avg_rating", 0) > 0],
            key=lambda r: r.get("avg_rating", 0),
            reverse=True,
        )[:10]

        # Sort by fork_count
        most_forked = sorted(
            [r for r in recipes if r.get("fork_count", 0) > 0],
            key=lambda r: r.get("fork_count", 0),
            reverse=True,
        )[:10]

        return {
            "top_rated": top_rated,
            "most_forked": most_forked,
            "total_shared": len(recipes),
        }

    def get_recipe_history(self, recipe_id: str) -> list[dict[str, Any]]:
        """Get version history for a recipe."""
        recipe_file = self._find_recipe_file(recipe_id)
        if not recipe_file or not recipe_file.exists():
            return []

        try:
            recipe = json.loads(recipe_file.read_text(encoding="utf-8"))
            history = recipe.get("version_history", [])
            # Add current version at the end
            history.append({
                "version": recipe.get("version", 1),
                "updated_at": recipe.get("shared_at", ""),
                "updated_by": recipe.get("shared_by", ""),
                "current": True,
            })
            return history
        except Exception:
            return []

    # ── Helpers ─────────────────────────────────────────────────────────

    def _find_recipe_file(self, recipe_id: str) -> Path | None:
        """Find a recipe file by ID across all categories."""
        hub = self.hub_path
        if not hub:
            return None
        recipes_root = hub / RECIPES_DIR
        if not recipes_root.exists():
            return None

        safe_id = _safe_name(recipe_id)
        for category_dir in recipes_root.iterdir():
            if not category_dir.is_dir():
                continue
            candidate = category_dir / f"{safe_id}.json"
            if candidate.exists():
                return candidate
            # Also check by loading and matching ID
            for rf in category_dir.glob("*.json"):
                try:
                    data = json.loads(rf.read_text(encoding="utf-8"))
                    if data.get("id") == recipe_id:
                        return rf
                except Exception:
                    continue
        return None

    def _update_catalog_rating(self, recipe_id: str, ratings: dict) -> None:
        """Update the avg_rating in the catalog for a recipe."""
        hub = self.hub_path
        if not hub:
            return

        catalog_file = hub / RECIPES_DIR / CATALOG_FILE
        if not catalog_file.exists():
            return

        try:
            catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
            for r in catalog.get("recipes", []):
                if r.get("id") == recipe_id:
                    r["avg_rating"] = _compute_avg_rating(ratings)
                    break
            catalog_file.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        except Exception:
            pass

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


# ── Module-Level Helpers ───────────────────────────────────────────────


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


def _compute_avg_rating(ratings: dict[str, Any]) -> float:
    """Compute average rating from a ratings dict ({user: {score, rated_at}})."""
    scores = []
    for v in ratings.values():
        if isinstance(v, dict):
            scores.append(v.get("score", 0))
        elif isinstance(v, (int, float)):
            scores.append(v)
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)
