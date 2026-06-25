"""Centralized application configuration paths.

All notebook config/data directory paths are defined here so they can be
changed in a single place. The default root is ``~/.flowyml/`` for backward
compatibility with existing installations.

Override the root via the ``FMLN_CONFIG_DIR`` environment variable::

    export FMLN_CONFIG_DIR=~/.my-notebook
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Root config directory ────────────────────────────────────────────────────

APP_CONFIG_DIR = Path(os.environ.get("FMLN_CONFIG_DIR", str(Path.home() / ".flowyml")))

# ── Individual config paths ──────────────────────────────────────────────────

AI_CONFIG_FILE = APP_CONFIG_DIR / "ai_config.json"
RECENT_FILES_FILE = APP_CONFIG_DIR / "recent_files.json"
HISTORY_DIR = APP_CONFIG_DIR / "history"
RECIPES_DIR = APP_CONFIG_DIR / "recipes"
RECIPES_USAGE_FILE = RECIPES_DIR / "usage.json"
NOTEBOOKS_DIR = APP_CONFIG_DIR / "notebooks"
SCHEDULED_SCRIPTS_DIR = APP_CONFIG_DIR / "scheduled_scripts"
PUBLISHED_APPS_DIR = APP_CONFIG_DIR / "published_apps"
APP_SNAPSHOTS_DIR = APP_CONFIG_DIR / "app_snapshots"
GITHUB_CONFIG_FILE = APP_CONFIG_DIR / "github.json"
REPOS_DIR = APP_CONFIG_DIR / "repos"
