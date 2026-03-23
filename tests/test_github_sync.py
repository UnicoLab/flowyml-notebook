"""Tests for the enhanced GitHubSync collaboration features.

Tests cover:
- Configuration management
- Notebook push/pull
- Git-persisted comments & reviews
- Merge conflict detection
- Stash management
- Activity feed
- Presence tracking
- Recipe ratings, forking, and leaderboard
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flowyml_notebook.github_sync import GitHubSync, _safe_name, _compute_avg_rating, _notebook_hash


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test isolation."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sync(tmp_dir):
    """Create a GitHubSync instance with a temp config path."""
    config_path = tmp_dir / "github.json"
    return GitHubSync(config_path=config_path)


@pytest.fixture
def sync_with_repo(tmp_dir, sync):
    """GitHubSync with a simulated repo directory."""
    repo_dir = tmp_dir / "test-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    hub = repo_dir / ".flowyml-hub"
    for sub in ["notebooks", "recipes", "comments", "reviews"]:
        (hub / sub).mkdir(parents=True)

    # Write catalog
    catalog = hub / "recipes" / "catalog.json"
    catalog.write_text(json.dumps({"recipes": [], "updated_at": ""}), encoding="utf-8")

    # Write presence
    presence = hub / "presence.json"
    presence.write_text(json.dumps({"editors": [], "updated_at": ""}), encoding="utf-8")

    # Configure sync
    sync.config = {
        "repos": {"test-repo": {"url": "https://github.com/test/test-repo", "local_path": str(repo_dir)}},
        "default_repo": "test-repo",
        "user": {"name": "Test User", "email": "test@example.com"},
    }
    sync._save_config()
    return sync


# ─── Utility Tests ────────────────────────────────────────────────


class TestUtilities:
    def test_safe_name(self):
        assert _safe_name("My Project") == "my-project"
        assert _safe_name("hello/world") == "hello-world"
        assert _safe_name("test.name") == "test-name"
        assert _safe_name("  spaces  ") == "spaces"

    def test_compute_avg_rating_empty(self):
        assert _compute_avg_rating({}) == 0.0

    def test_compute_avg_rating_scores(self):
        ratings = {
            "user1": {"score": 5, "rated_at": ""},
            "user2": {"score": 3, "rated_at": ""},
        }
        assert _compute_avg_rating(ratings) == 4.0

    def test_compute_avg_rating_plain_ints(self):
        ratings = {"user1": 4, "user2": 2}
        assert _compute_avg_rating(ratings) == 3.0

    def test_notebook_hash_deterministic(self):
        hash1 = _notebook_hash("proj", "exp")
        hash2 = _notebook_hash("proj", "exp")
        assert hash1 == hash2
        assert len(hash1) == 12

    def test_notebook_hash_different(self):
        assert _notebook_hash("a", "b") != _notebook_hash("c", "d")


# ─── Configuration Tests ─────────────────────────────────────────


class TestConfiguration:
    def test_new_config_defaults(self, sync):
        assert sync.config["repos"] == {}
        assert sync.config["default_repo"] is None

    def test_save_and_load_config(self, sync):
        sync.config["user"] = {"name": "Alice", "email": "alice@test.com"}
        sync._save_config()

        loaded = GitHubSync(config_path=sync.config_path)
        assert loaded.config["user"]["name"] == "Alice"

    def test_repo_path_none_when_no_repo(self, sync):
        assert sync.repo_path is None
        assert sync.hub_path is None


# ─── Git-Persisted Comments ──────────────────────────────────────


class TestGitPersistedComments:
    def test_comments_file_path(self, sync_with_repo):
        cf = sync_with_repo._comments_file("proj", "exp")
        assert cf is not None
        assert str(cf).endswith(".json")
        assert "comments" in str(cf)

    def test_push_comments(self, sync_with_repo):
        comments = [
            {"id": "c1", "text": "Test comment", "author": {"name": "User1"}, "created_at": "", "replies": []}
        ]
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            result = sync_with_repo.push_comments("proj", "exp", comments)
            assert result["count"] == 1

    def test_pull_comments_empty(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            result = sync_with_repo.pull_comments("proj", "nonexistent")
            assert result == []

    def test_merge_comments_union(self, sync_with_repo):
        local = [
            {"id": "c1", "text": "Local", "created_at": "2024-01-01", "replies": []},
            {"id": "c2", "text": "Local only", "created_at": "2024-01-02", "replies": []},
        ]
        remote = [
            {"id": "c1", "text": "Remote", "created_at": "2024-01-01", "replies": []},
            {"id": "c3", "text": "Remote only", "created_at": "2024-01-03", "replies": []},
        ]
        merged = sync_with_repo.merge_comments(local, remote)
        ids = [c["id"] for c in merged]
        assert "c1" in ids  # Union
        assert "c2" in ids
        assert "c3" in ids
        assert len(merged) == 3

    def test_merge_comments_preserves_replies(self, sync_with_repo):
        local = [{"id": "c1", "text": "X", "created_at": "", "replies": [
            {"text": "local reply", "author": {}, "created_at": ""}
        ]}]
        remote = [{"id": "c1", "text": "X", "created_at": "", "replies": [
            {"text": "remote reply", "author": {}, "created_at": ""}
        ]}]
        merged = sync_with_repo.merge_comments(local, remote)
        assert len(merged) == 1
        assert len(merged[0]["replies"]) == 2  # Both replies present


# ─── Git-Persisted Reviews ───────────────────────────────────────


class TestGitPersistedReviews:
    def test_reviews_file_path(self, sync_with_repo):
        rf = sync_with_repo._reviews_file("proj", "exp")
        assert rf is not None
        assert "reviews" in str(rf)

    def test_push_review(self, sync_with_repo):
        review = {
            "title": "Review my notebook",
            "reviewers": ["Alice"],
            "requested_by": {"name": "Bob"},
        }
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            result = sync_with_repo.push_review("proj", "exp", review)
            assert "review_id" in result

    def test_pull_reviews_empty(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            result = sync_with_repo.pull_reviews("proj", "nonexistent")
            assert result == []


# ─── Merge Status ────────────────────────────────────────────────


class TestMergeStatus:
    def test_check_merge_status_no_repo(self, sync):
        result = sync.check_merge_status()
        assert "error" in result

    def test_stash_no_repo(self, sync):
        result = sync.stash_changes()
        assert "error" in result

    def test_pop_stash_no_repo(self, sync):
        result = sync.pop_stash()
        assert "error" in result

    def test_list_stashes_no_repo(self, sync):
        result = sync.list_stashes()
        assert result == []


# ─── Notebook Sync ───────────────────────────────────────────────


class TestNotebookSync:
    def test_push_notebook_no_repo(self, sync):
        result = sync.push_notebook("proj", "exp", {"cells": []})
        assert "error" in result

    def test_push_notebook_creates_files(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = sync_with_repo.push_notebook("my-project", "experiment-1", {"cells": [{"id": "c1"}]})

        hub = sync_with_repo.hub_path
        nb_file = hub / "notebooks" / "my-project" / "experiment-1" / "notebook.fml.json"
        meta_file = hub / "notebooks" / "my-project" / "experiment-1" / "metadata.json"

        assert nb_file.exists()
        assert meta_file.exists()

        data = json.loads(nb_file.read_text())
        assert len(data["cells"]) == 1

        meta = json.loads(meta_file.read_text())
        assert meta["version"] == 1
        assert meta["cell_count"] == 1

    def test_pull_notebook_not_found(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0)
            result = sync_with_repo.pull_notebook("nonexistent", "never")
        assert result is None

    def test_list_projects_empty(self, sync_with_repo):
        projects = sync_with_repo.list_projects()
        assert projects == []


# ─── Branches ────────────────────────────────────────────────────


class TestBranches:
    def test_list_branches_no_repo(self, sync):
        result = sync.list_branches()
        assert result["branches"] == []

    def test_create_branch_no_repo(self, sync):
        result = sync.create_branch("test")
        assert "error" in result

    def test_switch_branch_no_repo(self, sync):
        result = sync.switch_branch("main")
        assert "error" in result

    def test_delete_branch_no_repo(self, sync):
        result = sync.delete_branch("test")
        assert "error" in result


# ─── Presence ────────────────────────────────────────────────────


class TestPresence:
    def test_set_editing_status_no_repo(self, sync):
        result = sync.set_editing_status("nb1")
        assert "error" in result

    def test_get_active_editors_no_repo(self, sync):
        result = sync.get_active_editors()
        assert result == []


# ─── Recipes ─────────────────────────────────────────────────────


class TestRecipes:
    def test_push_recipe(self, sync_with_repo):
        recipe = {
            "id": "my-recipe",
            "name": "My Recipe",
            "category": "custom",
            "source": "print('hello')",
            "description": "Test recipe",
            "tags": ["test"],
        }
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = sync_with_repo.push_recipe(recipe)
            assert result.get("shared") is True

    def test_get_recipe_catalog(self, sync_with_repo):
        catalog = sync_with_repo.get_recipe_catalog()
        assert "recipes" in catalog

    def test_rate_recipe_not_found(self, sync_with_repo):
        result = sync_with_repo.rate_recipe("nonexistent", 5)
        assert "error" in result

    def test_fork_recipe_not_found(self, sync_with_repo):
        result = sync_with_repo.fork_recipe("nonexistent")
        assert "error" in result

    def test_get_recipe_leaderboard_empty(self, sync_with_repo):
        lb = sync_with_repo.get_recipe_leaderboard()
        assert lb["top_rated"] == []
        assert lb["most_forked"] == []

    def test_get_recipe_history_nonexistent(self, sync_with_repo):
        result = sync_with_repo.get_recipe_history("no-such-recipe")
        assert result == []


# ─── Activity Feed ───────────────────────────────────────────────


class TestActivityFeed:
    def test_activity_feed_empty(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0, stdout="")
            feed = sync_with_repo.get_activity_feed()
        assert isinstance(feed, list)

    def test_commit_log_empty(self, sync_with_repo):
        with patch("flowyml_notebook.github_sync._run_cmd") as mock_cmd:
            mock_cmd.return_value = MagicMock(returncode=0, stdout="")
            commits = sync_with_repo.get_commit_log()
        assert commits == []


# ─── Status ──────────────────────────────────────────────────────


class TestStatus:
    def test_status_no_repo(self, sync):
        status = sync.get_status()
        assert status["connected"] is False

    def test_get_config(self, sync):
        config = sync.get_config()
        assert config["connected"] is False
        assert "repos" in config
