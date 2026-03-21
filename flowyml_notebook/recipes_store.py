"""Persistent recipe store for FlowyML Notebook.

Manages custom cell recipes with:
- Local file-based persistence (~/.flowyml/recipes/)
- Usage tracking per recipe
- Optional GitHub sync for shared team recipes
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RECIPES_DIR = Path.home() / ".flowyml" / "recipes"
USAGE_FILE = RECIPES_DIR / "usage.json"


class RecipeStore:
    """Local recipe store with usage tracking and GitHub sync support."""

    def __init__(self, recipes_dir: str | Path | None = None):
        self.recipes_dir = Path(recipes_dir) if recipes_dir else RECIPES_DIR
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        self._usage: dict[str, int] = self._load_usage()

    # ── CRUD ───────────────────────────────────────────────────────────

    def list_recipes(self) -> list[dict[str, Any]]:
        """List all custom recipes with usage counts."""
        recipes = []
        for f in sorted(self.recipes_dir.glob("*.recipe.json")):
            try:
                recipe = json.loads(f.read_text(encoding="utf-8"))
                recipe["usage_count"] = self._usage.get(recipe.get("id", ""), 0)
                recipes.append(recipe)
            except Exception as e:
                logger.warning(f"Failed to load recipe {f.name}: {e}")
        return recipes

    def get_recipe(self, recipe_id: str) -> dict[str, Any] | None:
        """Get a single recipe by ID."""
        filepath = self.recipes_dir / f"{recipe_id}.recipe.json"
        if not filepath.exists():
            return None
        try:
            recipe = json.loads(filepath.read_text(encoding="utf-8"))
            recipe["usage_count"] = self._usage.get(recipe_id, 0)
            return recipe
        except Exception:
            return None

    def save_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """Save or update a recipe."""
        recipe_id = recipe.get("id")
        if not recipe_id:
            recipe_id = f"custom-{int(datetime.now().timestamp() * 1000)}"
            recipe["id"] = recipe_id

        recipe.setdefault("created_at", datetime.now().isoformat())
        recipe["updated_at"] = datetime.now().isoformat()
        recipe.setdefault("builtin", False)

        filepath = self.recipes_dir / f"{recipe_id}.recipe.json"
        filepath.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

        logger.info(f"Saved recipe: {recipe.get('name', recipe_id)}")
        return recipe

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe by ID."""
        filepath = self.recipes_dir / f"{recipe_id}.recipe.json"
        if filepath.exists():
            filepath.unlink()
            # Remove usage data
            self._usage.pop(recipe_id, None)
            self._save_usage()
            logger.info(f"Deleted recipe: {recipe_id}")
            return True
        return False

    # ── Usage Tracking ─────────────────────────────────────────────────

    def track_usage(self, recipe_id: str) -> int:
        """Increment usage count for a recipe and return new count."""
        self._usage[recipe_id] = self._usage.get(recipe_id, 0) + 1
        self._save_usage()
        return self._usage[recipe_id]

    def get_usage(self, recipe_id: str) -> int:
        """Get usage count for a specific recipe."""
        return self._usage.get(recipe_id, 0)

    def get_all_usage(self) -> dict[str, int]:
        """Get all usage counts."""
        return dict(self._usage)

    def _load_usage(self) -> dict[str, int]:
        """Load usage tracking data."""
        if USAGE_FILE.exists():
            try:
                return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_usage(self) -> None:
        """Persist usage tracking data."""
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(self._usage, indent=2), encoding="utf-8")

    # ── Import / Export ────────────────────────────────────────────────

    def export_all(self) -> list[dict[str, Any]]:
        """Export all custom recipes as a list (for JSON export)."""
        return self.list_recipes()

    def import_recipes(self, recipes: list[dict[str, Any]], overwrite: bool = False) -> int:
        """Import recipes from a list. Returns count of imported recipes."""
        imported = 0
        for recipe in recipes:
            recipe_id = recipe.get("id")
            if not recipe_id:
                continue
            existing = self.recipes_dir / f"{recipe_id}.recipe.json"
            if existing.exists() and not overwrite:
                continue
            self.save_recipe(recipe)
            imported += 1
        return imported
