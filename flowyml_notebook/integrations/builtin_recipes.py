"""Built-in UnicoLab ecosystem recipes for FlowyML Notebook.

Provides pre-built multi-cell recipes for common Keras-based workflows
using KDP, KerasFactory, and MLPotion.
"""

from __future__ import annotations

from typing import Any


def get_builtin_recipes() -> list[dict[str, Any]]:
    """Return all built-in ecosystem recipes.

    Each recipe has:
      - id, name, description, tags
      - cells: list of {source, cell_type, name}
      - builtin: True
      - ecosystem: "unicolab"
    """
    return [
        _kdp_preprocessing_recipe(),
        _kerasfactory_model_recipe(),
        _mlpotion_training_recipe(),
        _end_to_end_recipe(),
    ]


# ── Recipes ───────────────────────────────────────────────────────────────────


def _kdp_preprocessing_recipe() -> dict[str, Any]:
    return {
        "id": "unicolab-kdp-preprocessing",
        "name": "🧪 KDP Smart Preprocessing",
        "description": (
            "Auto-configure Keras preprocessing layers with KDP. "
            "Handles normalization, encoding, distribution-aware transforms, "
            "and tabular attention — all as Keras model layers."
        ),
        "tags": ["kdp", "preprocessing", "keras", "unicolab"],
        "builtin": True,
        "ecosystem": "unicolab",
        "package": "kdp",
        "cells": [
            {
                "source": "# 🧪 KDP Smart Preprocessing\n# Auto-configure Keras preprocessing layers for your data",
                "cell_type": "markdown",
                "name": "header",
            },
            {
                "source": (
                    "from kdp import PreprocessingModel, FeatureType\n"
                    "import pandas as pd\n"
                    "\n"
                    "# Load your data\n"
                    "df = pd.read_csv('your_data.csv')"
                ),
                "cell_type": "code",
                "name": "imports",
            },
            {
                "source": (
                    "# Define feature types\n"
                    "features_specs = {\n"
                    '    "age": FeatureType.FLOAT_NORMALIZED,\n'
                    '    "income": FeatureType.FLOAT_RESCALED,\n'
                    '    "occupation": FeatureType.STRING_CATEGORICAL,\n'
                    '    "description": FeatureType.TEXT,\n'
                    "}\n"
                    "\n"
                    "# Build preprocessor\n"
                    "preprocessor = PreprocessingModel(\n"
                    "    path_data='your_data.csv',\n"
                    "    features_specs=features_specs,\n"
                    "    use_distribution_aware=True,\n"
                    "    tabular_attention=True,\n"
                    ")\n"
                    "\n"
                    "result = preprocessor.build_preprocessor()\n"
                    "model = result['model']\n"
                    "model.summary()"
                ),
                "cell_type": "code",
                "name": "build_preprocessor",
            },
        ],
    }


def _kerasfactory_model_recipe() -> dict[str, Any]:
    return {
        "id": "unicolab-kerasfactory-model",
        "name": "🏗️ KerasFactory Quick Model",
        "description": (
            "Build a production-ready tabular model with KerasFactory. "
            "Uses reusable layers like GatedResidualNetwork, TabularAttention, "
            "and DistributionTransformLayer for advanced feature processing."
        ),
        "tags": ["kerasfactory", "model", "keras", "tabular", "unicolab"],
        "builtin": True,
        "ecosystem": "unicolab",
        "package": "kerasfactory",
        "cells": [
            {
                "source": "# 🏗️ KerasFactory Quick Model\n# Build a tabular model with production-ready Keras layers",
                "cell_type": "markdown",
                "name": "header",
            },
            {
                "source": (
                    "import keras\n"
                    "from kerasfactory.layers import (\n"
                    "    DistributionTransformLayer,\n"
                    "    GatedResidualNetwork,\n"
                    "    GatedFeatureFusion,\n"
                    ")\n"
                    "from kerasfactory.models import BaseFeedForwardModel\n"
                    "import pandas as pd\n"
                    "from sklearn.model_selection import train_test_split\n"
                    "\n"
                    "# Load data\n"
                    "df = pd.read_csv('your_data.csv')\n"
                    "X = df.drop(columns=['target'])\n"
                    "y = df['target']\n"
                    "X_train, X_test, y_train, y_test = train_test_split(\n"
                    "    X, y, test_size=0.2, random_state=42\n"
                    ")"
                ),
                "cell_type": "code",
                "name": "setup",
            },
            {
                "source": (
                    "# Option A: One-liner with BaseFeedForwardModel\n"
                    "model = BaseFeedForwardModel(\n"
                    "    feature_names=list(X.columns),\n"
                    "    hidden_units=[128, 64, 32],\n"
                    "    output_units=1,\n"
                    "    dropout_rate=0.2,\n"
                    ")\n"
                    "\n"
                    "model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])\n"
                    "model.summary()"
                ),
                "cell_type": "code",
                "name": "build_model",
            },
            {
                "source": (
                    "# Option B: Custom architecture with advanced layers\n"
                    "inputs = keras.Input(shape=(X_train.shape[1],))\n"
                    "x = DistributionTransformLayer(transform_type='auto')(inputs)\n"
                    "x = GatedResidualNetwork(units=64)(x)\n"
                    "x = keras.layers.Dropout(0.2)(x)\n"
                    "x = GatedResidualNetwork(units=32)(x)\n"
                    "outputs = keras.layers.Dense(1, activation='sigmoid')(x)\n"
                    "\n"
                    "custom_model = keras.Model(inputs, outputs)\n"
                    "custom_model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])\n"
                    "custom_model.summary()"
                ),
                "cell_type": "code",
                "name": "advanced_model",
            },
        ],
    }


def _mlpotion_training_recipe() -> dict[str, Any]:
    return {
        "id": "unicolab-mlpotion-training",
        "name": "🧪 MLPotion Training Pipeline",
        "description": (
            "Managed Keras training with MLPotion. Type-safe configuration, "
            "consistent interface, and production-ready training pipeline."
        ),
        "tags": ["mlpotion", "training", "keras", "pipeline", "unicolab"],
        "builtin": True,
        "ecosystem": "unicolab",
        "package": "mlpotion",
        "cells": [
            {
                "source": "# 🧪 MLPotion Training Pipeline\n# Type-safe, managed Keras training",
                "cell_type": "markdown",
                "name": "header",
            },
            {
                "source": (
                    "from mlpotion.frameworks.keras.training import ModelTrainer\n"
                    "from mlpotion.frameworks.keras.config import ModelTrainingConfig\n"
                    "import keras\n"
                    "import pandas as pd\n"
                    "from sklearn.model_selection import train_test_split\n"
                    "\n"
                    "# Load and split data\n"
                    "df = pd.read_csv('your_data.csv')\n"
                    "X = df.drop(columns=['target'])\n"
                    "y = df['target']\n"
                    "X_train, X_test, y_train, y_test = train_test_split(\n"
                    "    X, y, test_size=0.2, random_state=42\n"
                    ")"
                ),
                "cell_type": "code",
                "name": "setup",
            },
            {
                "source": (
                    "# Build your model\n"
                    "model = keras.Sequential([\n"
                    "    keras.layers.Input(shape=(X_train.shape[1],)),\n"
                    "    keras.layers.Dense(128, activation='relu'),\n"
                    "    keras.layers.Dropout(0.3),\n"
                    "    keras.layers.Dense(64, activation='relu'),\n"
                    "    keras.layers.Dense(1, activation='sigmoid'),\n"
                    "])"
                ),
                "cell_type": "code",
                "name": "model",
            },
            {
                "source": (
                    "# Configure and run training with MLPotion\n"
                    "config = ModelTrainingConfig(\n"
                    "    epochs=30,\n"
                    "    batch_size=32,\n"
                    "    optimizer='adam',\n"
                    "    loss='binary_crossentropy',\n"
                    ")\n"
                    "\n"
                    "trainer = ModelTrainer(config=config)\n"
                    "history = trainer.train(\n"
                    "    model=model,\n"
                    "    train_data=(X_train, y_train),\n"
                    "    val_data=(X_test, y_test),\n"
                    ")\n"
                    "\n"
                    "print(f'✅ Training complete!')\n"
                    "print(f'   Loss: {history.history[\"loss\"][-1]:.4f}')\n"
                    "print(f'   Val Loss: {history.history[\"val_loss\"][-1]:.4f}')"
                ),
                "cell_type": "code",
                "name": "train",
            },
        ],
    }


def _end_to_end_recipe() -> dict[str, Any]:
    return {
        "id": "unicolab-e2e-pipeline",
        "name": "🦄 UnicoLab End-to-End Pipeline",
        "description": (
            "Complete ML pipeline combining all three UnicoLab packages: "
            "KDP (preprocessing) → KerasFactory (model architecture) → MLPotion (training). "
            "The entire pipeline deploys as a single Keras model."
        ),
        "tags": ["kdp", "kerasfactory", "mlpotion", "e2e", "pipeline", "keras", "unicolab"],
        "builtin": True,
        "ecosystem": "unicolab",
        "package": "all",
        "cells": [
            {
                "source": (
                    "# 🦄 UnicoLab End-to-End Pipeline\n"
                    "# KDP → KerasFactory → MLPotion\n"
                    "# Preprocessing, model building, and training as one unified workflow"
                ),
                "cell_type": "markdown",
                "name": "header",
            },
            {
                "source": (
                    "from kdp import PreprocessingModel, FeatureType\n"
                    "from kerasfactory.layers import GatedResidualNetwork, DistributionTransformLayer\n"
                    "from mlpotion.frameworks.keras.training import ModelTrainer\n"
                    "from mlpotion.frameworks.keras.config import ModelTrainingConfig\n"
                    "from sklearn.model_selection import train_test_split\n"
                    "import keras\n"
                    "import pandas as pd\n"
                    "\n"
                    "df = pd.read_csv('your_data.csv')"
                ),
                "cell_type": "code",
                "name": "imports",
            },
            {
                "source": (
                    "# Step 1: KDP Preprocessing\n"
                    "features_specs = {\n"
                    '    "feature_1": FeatureType.FLOAT_NORMALIZED,\n'
                    '    "feature_2": FeatureType.FLOAT_RESCALED,\n'
                    '    "category": FeatureType.STRING_CATEGORICAL,\n'
                    "}\n"
                    "\n"
                    "preprocessor = PreprocessingModel(\n"
                    "    path_data='your_data.csv',\n"
                    "    features_specs=features_specs,\n"
                    "    use_distribution_aware=True,\n"
                    "    tabular_attention=True,\n"
                    ")\n"
                    "prep_result = preprocessor.build_preprocessor()\n"
                    "prep_model = prep_result['model']\n"
                    "print(f'✅ Preprocessor built: {prep_model.count_params():,} params')"
                ),
                "cell_type": "code",
                "name": "preprocessing",
            },
            {
                "source": (
                    "# Step 2: KerasFactory Model Architecture\n"
                    "inputs = prep_model.input\n"
                    "x = prep_model.output\n"
                    "x = GatedResidualNetwork(units=64)(x)\n"
                    "x = keras.layers.Dropout(0.2)(x)\n"
                    "x = keras.layers.Dense(32, activation='relu')(x)\n"
                    "outputs = keras.layers.Dense(1, activation='sigmoid')(x)\n"
                    "\n"
                    "full_model = keras.Model(inputs=inputs, outputs=outputs)\n"
                    "print(f'✅ Full model: {full_model.count_params():,} params')"
                ),
                "cell_type": "code",
                "name": "model",
            },
            {
                "source": (
                    "# Step 3: MLPotion Training\n"
                    "config = ModelTrainingConfig(\n"
                    "    epochs=50,\n"
                    "    batch_size=32,\n"
                    "    optimizer='adam',\n"
                    "    loss='binary_crossentropy',\n"
                    ")\n"
                    "\n"
                    "X = df.drop(columns=['target'])\n"
                    "y = df['target']\n"
                    "X_train, X_test, y_train, y_test = train_test_split(\n"
                    "    X, y, test_size=0.2, random_state=42\n"
                    ")\n"
                    "\n"
                    "trainer = ModelTrainer(config=config)\n"
                    "history = trainer.train(\n"
                    "    model=full_model,\n"
                    "    train_data=(X_train, y_train),\n"
                    "    val_data=(X_test, y_test),\n"
                    ")\n"
                    "print('🎉 Full UnicoLab pipeline complete!')"
                ),
                "cell_type": "code",
                "name": "training",
            },
        ],
    }
