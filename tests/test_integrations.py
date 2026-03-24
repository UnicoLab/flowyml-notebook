"""Tests for the UnicoLab ecosystem integration module.

Tests the adapter logic, builtin recipes, and ecosystem detection
without requiring the actual ecosystem packages to be installed.
"""

from __future__ import annotations

import importlib
from unittest.mock import patch


# ── Ecosystem Detection ──────────────────────────────────────────────────────


class TestEcosystemDetection:
    """Test the UnicoLabEcosystem registry."""

    def test_available_packages_returns_dict(self):
        """available_packages() should return a dict with expected keys."""
        from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

        result = UnicoLabEcosystem.available_packages()
        assert isinstance(result, dict)
        assert "kdp" in result
        assert "kerasfactory" in result
        assert "mlpotion" in result
        # Values are booleans
        for v in result.values():
            assert isinstance(v, bool)

    def test_get_ecosystem_status_structure(self):
        """get_ecosystem_status() should return a well-structured dict."""
        from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

        status = UnicoLabEcosystem.get_ecosystem_status()
        assert "packages" in status
        assert "installed_count" in status
        assert "total_count" in status
        assert "fully_integrated" in status
        assert "install_all" in status
        assert status["total_count"] == 3
        assert isinstance(status["packages"], list)
        assert len(status["packages"]) == 3

    def test_ecosystem_status_package_fields(self):
        """Each package in status should have required fields."""
        from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

        status = UnicoLabEcosystem.get_ecosystem_status()
        for pkg in status["packages"]:
            assert "key" in pkg
            assert "name" in pkg
            assert "description" in pkg
            assert "installed" in pkg
            assert "install_command" in pkg
            assert "docs_url" in pkg
            assert "repo_url" in pkg

    def test_is_available_unknown_package(self):
        """is_available() should return False for unknown packages."""
        from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

        assert UnicoLabEcosystem.is_available("nonexistent_package") is False

    def test_get_package_version_unknown(self):
        """get_package_version() should return None for unknown packages."""
        from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

        assert UnicoLabEcosystem.get_package_version("nonexistent") is None


# ── KDP Adapter ──────────────────────────────────────────────────────────────


class TestKDPAdapter:
    """Test the KDP adapter without requiring KDP installed."""

    def test_map_feature_types_basic(self):
        """map_feature_types should convert FlowyML types to KDP types."""
        from flowyml_notebook.integrations.kdp_adapter import map_feature_types

        feature_types = {
            "age": "continuous",
            "income": "continuous",
            "gender": "binary",
            "city": "nominal",
            "description": "high_cardinality",
        }
        result = map_feature_types(feature_types)
        assert "age" in result
        assert result["age"] == "FeatureType.FLOAT_NORMALIZED"
        assert result["gender"] == "FeatureType.INTEGER_CATEGORICAL"
        assert result["city"] == "FeatureType.STRING_CATEGORICAL"
        assert result["description"] == "FeatureType.STRING_CATEGORICAL"
        assert len(result) == 5

    def test_map_feature_types_excludes_target(self):
        """map_feature_types should exclude the target column."""
        from flowyml_notebook.integrations.kdp_adapter import map_feature_types

        feature_types = {"x1": "continuous", "x2": "continuous", "y": "binary"}
        result = map_feature_types(feature_types, target="y")
        assert "y" not in result
        assert len(result) == 2

    def test_generate_preprocessing_suggestion(self):
        """Should generate a valid SmartPrep suggestion dict."""
        from flowyml_notebook.integrations.kdp_adapter import generate_preprocessing_suggestion

        result = generate_preprocessing_suggestion(
            var_name="df",
            feature_types={"age": "continuous", "city": "nominal", "target": "binary"},
            n_rows=1000,
            n_cols=3,
            target="target",
        )
        assert result["type"] == "kdp_preprocessing"
        assert result["ecosystem"] == "unicolab"
        assert "code" in result
        assert "PreprocessingModel" in result["code"]
        assert "FeatureType" in result["code"]
        # Target should not appear in generated features_specs
        assert '"target"' not in result["code"]

    def test_generate_preprocessing_suggestion_empty(self):
        """Should return empty dict when no features available."""
        from flowyml_notebook.integrations.kdp_adapter import generate_preprocessing_suggestion

        result = generate_preprocessing_suggestion(
            var_name="df",
            feature_types={"target": "binary"},
            n_rows=100,
            n_cols=1,
            target="target",
        )
        assert result == {}


# ── KerasFactory Adapter ─────────────────────────────────────────────────────


class TestKerasFactoryAdapter:
    """Test the KerasFactory adapter."""

    def test_classification_recommendation(self):
        """Should generate a classification recommendation."""
        from flowyml_notebook.integrations.kerasfactory_adapter import (
            generate_model_recommendation,
        )

        result = generate_model_recommendation(
            var_name="df",
            task_type="classification",
            target="y",
            feature_names=["x1", "x2", "x3"],
            n_rows=5000,
            n_features=3,
        )
        assert result["name"] == "KerasFactory Neural Network"
        assert result["category"] == "deep_learning"
        assert result["ecosystem"] == "unicolab"
        assert "code" in result
        assert "BaseFeedForwardModel" in result["code"]
        assert "binary_crossentropy" in result["code"]

    def test_regression_recommendation(self):
        """Should generate a regression recommendation."""
        from flowyml_notebook.integrations.kerasfactory_adapter import (
            generate_model_recommendation,
        )

        result = generate_model_recommendation(
            var_name="df",
            task_type="regression",
            target="price",
            feature_names=["sqft", "bedrooms"],
            n_rows=2000,
            n_features=2,
        )
        assert result["name"] == "KerasFactory Neural Network"
        assert "mse" in result["code"]
        assert "'price'" in result["code"]

    def test_advanced_recommendation(self):
        """Should generate advanced recommendation with GRN layers."""
        from flowyml_notebook.integrations.kerasfactory_adapter import (
            generate_advanced_model_recommendation,
        )

        result = generate_advanced_model_recommendation(
            var_name="df",
            task_type="classification",
            target="y",
            feature_names=["x1", "x2"],
            n_rows=3000,
            n_features=2,
        )
        assert "GatedResidualNetwork" in result["name"]
        assert "GatedResidualNetwork" in result["code"]
        assert "DistributionTransformLayer" in result["code"]

    def test_unsupervised_recommendation(self):
        """Should generate autoencoder for unsupervised tasks."""
        from flowyml_notebook.integrations.kerasfactory_adapter import (
            generate_model_recommendation,
        )

        result = generate_model_recommendation(
            var_name="df",
            task_type="unsupervised",
            target="",
            feature_names=["x1", "x2"],
            n_rows=1000,
            n_features=2,
        )
        assert "Autoencoder" in result["name"]
        assert "anomal" in result["code"].lower()

    def test_score_varies_with_data_size(self):
        """Score should be higher for larger datasets."""
        from flowyml_notebook.integrations.kerasfactory_adapter import (
            generate_model_recommendation,
        )

        small = generate_model_recommendation(
            var_name="df", task_type="classification", target="y",
            feature_names=["x1"], n_rows=100, n_features=1,
        )
        large = generate_model_recommendation(
            var_name="df", task_type="classification", target="y",
            feature_names=["x1"], n_rows=5000, n_features=1,
        )
        assert large["score"] > small["score"]


# ── MLPotion Adapter ─────────────────────────────────────────────────────────


class TestMLPotionAdapter:
    """Test the MLPotion adapter."""

    def test_generate_training_pipeline(self):
        """Should generate a valid training pipeline."""
        from flowyml_notebook.integrations.mlpotion_adapter import (
            generate_training_pipeline,
        )

        result = generate_training_pipeline(
            var_name="df",
            task_type="classification",
            target="y",
            n_rows=5000,
            n_features=10,
        )
        assert result["name"] == "Keras + MLPotion Pipeline"
        assert result["ecosystem"] == "unicolab"
        assert "ModelTrainer" in result["code"]
        assert "ModelTrainingConfig" in result["code"]

    def test_pipeline_adapts_hyperparameters(self):
        """Pipeline should adapt epochs/batch based on dataset size."""
        from flowyml_notebook.integrations.mlpotion_adapter import (
            generate_training_pipeline,
        )

        small = generate_training_pipeline("df", "classification", "y", 1000, 5)
        large = generate_training_pipeline("df", "classification", "y", 20000, 5)
        # Small dataset => 30 epochs, large => 50
        assert "epochs=30" in small["code"]
        assert "epochs=50" in large["code"]

    def test_full_ecosystem_pipeline(self):
        """Should generate end-to-end pipeline with all 3 packages."""
        from flowyml_notebook.integrations.mlpotion_adapter import (
            generate_full_ecosystem_pipeline,
        )

        result = generate_full_ecosystem_pipeline(
            var_name="df",
            task_type="classification",
            target="y",
            feature_types={"x1": "continuous", "x2": "nominal", "y": "binary"},
            n_rows=5000,
            n_features=2,
        )
        assert "UnicoLab" in result["name"]
        # Should reference all 3 packages
        assert "PreprocessingModel" in result["code"]
        assert "GatedResidualNetwork" in result["code"]
        assert "ModelTrainer" in result["code"]


# ── Builtin Recipes ──────────────────────────────────────────────────────────


class TestBuiltinRecipes:
    """Test the builtin ecosystem recipes."""

    def test_get_builtin_recipes_returns_list(self):
        """Should return a non-empty list of recipes."""
        from flowyml_notebook.integrations.builtin_recipes import get_builtin_recipes

        recipes = get_builtin_recipes()
        assert isinstance(recipes, list)
        assert len(recipes) == 4

    def test_recipe_has_required_fields(self):
        """Each recipe must have id, name, description, cells."""
        from flowyml_notebook.integrations.builtin_recipes import get_builtin_recipes

        for recipe in get_builtin_recipes():
            assert "id" in recipe
            assert "name" in recipe
            assert "description" in recipe
            assert "cells" in recipe
            assert "tags" in recipe
            assert recipe["builtin"] is True
            assert recipe["ecosystem"] == "unicolab"

    def test_recipe_cells_have_source(self):
        """Each cell in a recipe must have source and cell_type."""
        from flowyml_notebook.integrations.builtin_recipes import get_builtin_recipes

        for recipe in get_builtin_recipes():
            for cell in recipe["cells"]:
                assert "source" in cell
                assert "cell_type" in cell
                assert cell["cell_type"] in ("code", "markdown")

    def test_recipe_ids_unique(self):
        """All recipe IDs must be unique."""
        from flowyml_notebook.integrations.builtin_recipes import get_builtin_recipes

        ids = [r["id"] for r in get_builtin_recipes()]
        assert len(ids) == len(set(ids))

    def test_e2e_recipe_references_all_packages(self):
        """End-to-end recipe should reference all 3 ecosystem packages."""
        from flowyml_notebook.integrations.builtin_recipes import get_builtin_recipes

        e2e = [r for r in get_builtin_recipes() if r["id"] == "unicolab-e2e-pipeline"]
        assert len(e2e) == 1
        all_source = " ".join(c["source"] for c in e2e[0]["cells"])
        assert "kdp" in all_source.lower() or "PreprocessingModel" in all_source
        assert "kerasfactory" in all_source.lower() or "GatedResidualNetwork" in all_source
        assert "mlpotion" in all_source.lower() or "ModelTrainer" in all_source
