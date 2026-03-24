"""MLPotion adapter for end-to-end training pipeline suggestions.

Generates complete train-evaluate-save pipeline code using MLPotion's
``ModelTrainer`` and ``ModelTrainingConfig``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_training_pipeline(
    var_name: str,
    task_type: str,
    target: str,
    n_rows: int,
    n_features: int,
) -> dict[str, Any]:
    """Generate a full Keras training pipeline using MLPotion.

    Args:
        var_name: DataFrame variable name.
        task_type: ``"classification"`` or ``"regression"``.
        target: Target column name.
        n_rows: Number of samples.
        n_features: Number of features.

    Returns:
        Recommendation dict compatible with Algorithm Matchmaker format.
    """
    # Adaptive hyperparameters based on dataset size
    epochs = 30 if n_rows < 5000 else 50
    batch_size = 32 if n_rows < 10000 else 64
    loss = "sparse_categorical_crossentropy" if task_type == "classification" else "mse"
    optimizer = "adam"

    code = (
        f"from mlpotion.frameworks.keras.training import ModelTrainer\n"
        f"from mlpotion.frameworks.keras.config import ModelTrainingConfig\n"
        f"from sklearn.model_selection import train_test_split\n"
        f"import keras\n"
        f"\n"
        f"# 1. Prepare data\n"
        f"X = {var_name}.drop(columns=['{target}'])\n"
        f"y = {var_name}['{target}']\n"
        f"X_train, X_test, y_train, y_test = train_test_split(\n"
        f"    X, y, test_size=0.2, random_state=42\n"
        f")\n"
        f"\n"
        f"# 2. Build your Keras model\n"
        f"model = keras.Sequential([\n"
        f"    keras.layers.Input(shape=({n_features},)),\n"
        f"    keras.layers.Dense(128, activation='relu'),\n"
        f"    keras.layers.Dropout(0.3),\n"
        f"    keras.layers.Dense(64, activation='relu'),\n"
        f"    keras.layers.Dropout(0.2),\n"
        f"    keras.layers.Dense(1, activation='{'sigmoid' if task_type == 'classification' else 'linear'}'),\n"
        f"])\n"
        f"\n"
        f"# 3. Configure training with MLPotion 🧪\n"
        f"config = ModelTrainingConfig(\n"
        f"    epochs={epochs},\n"
        f"    batch_size={batch_size},\n"
        f"    optimizer='{optimizer}',\n"
        f"    loss='{loss}',\n"
        f")\n"
        f"\n"
        f"# 4. Train with MLPotion's managed pipeline\n"
        f"trainer = ModelTrainer(config=config)\n"
        f"history = trainer.train(\n"
        f"    model=model,\n"
        f"    train_data=(X_train, y_train),\n"
        f"    val_data=(X_test, y_test),\n"
        f")\n"
        f"\n"
        f"print(f'✅ Training complete!')\n"
        f"print(f'   Final loss: {{history.history[\"loss\"][-1]:.4f}}')\n"
        f"if 'val_loss' in history.history:\n"
        f"    print(f'   Val loss:   {{history.history[\"val_loss\"][-1]:.4f}}')"
    )

    return {
        "name": "Keras + MLPotion Pipeline",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 82 if n_rows > 1000 else 68,
        "speed": "medium",
        "interpretability": "medium",
        "reasons": [
            "Type-safe training configuration — no missing parameters",
            "Managed training pipeline with history tracking",
            "Consistent interface across frameworks (Keras, TF, PyTorch)",
            "Production-ready training with built-in best practices",
        ],
        "caveats": [
            "Requires MLPotion: pip install mlpotion",
            "For small datasets (<500 rows), traditional ML may be better",
        ],
        "code": code,
    }


def generate_full_ecosystem_pipeline(
    var_name: str,
    task_type: str,
    target: str,
    feature_types: dict[str, str],
    n_rows: int,
    n_features: int,
) -> dict[str, Any]:
    """Generate a complete end-to-end pipeline: KDP → KerasFactory → MLPotion.

    This is the flagship recommendation combining all three packages.
    """
    features_list = [col for col in feature_types if col != target]
    features_str = ", ".join(f"'{f}'" for f in features_list[:8])
    output_activation = "sigmoid" if task_type == "classification" else "linear"
    loss = "binary_crossentropy" if task_type == "classification" else "mse"

    # Build KDP feature specs
    from flowyml_notebook.integrations.kdp_adapter import _FEATURE_TYPE_MAP
    specs_lines = []
    for col in features_list[:10]:
        ftype = feature_types.get(col, "continuous")
        kdp_type = _FEATURE_TYPE_MAP.get(ftype, "FLOAT_NORMALIZED")
        specs_lines.append(f'    "{col}": FeatureType.{kdp_type},')
    specs_block = "\n".join(specs_lines)

    code = (
        f"# 🚀 End-to-End UnicoLab ML Pipeline\n"
        f"# KDP (preprocessing) → KerasFactory (model) → MLPotion (training)\n"
        f"\n"
        f"from kdp import PreprocessingModel, FeatureType\n"
        f"from kerasfactory.layers import GatedResidualNetwork, DistributionTransformLayer\n"
        f"from mlpotion.frameworks.keras.training import ModelTrainer\n"
        f"from mlpotion.frameworks.keras.config import ModelTrainingConfig\n"
        f"from sklearn.model_selection import train_test_split\n"
        f"import keras\n"
        f"\n"
        f"# ── Step 1: KDP Preprocessing ──\n"
        f"features_specs = {{\n"
        f"{specs_block}\n"
        f"}}\n"
        f"\n"
        f"preprocessor = PreprocessingModel(\n"
        f"    path_data='data.csv',\n"
        f"    features_specs=features_specs,\n"
        f"    use_distribution_aware=True,\n"
        f"    tabular_attention={n_rows >= 500},\n"
        f")\n"
        f"prep_result = preprocessor.build_preprocessor()\n"
        f"prep_model = prep_result['model']\n"
        f"\n"
        f"# ── Step 2: KerasFactory Model ──\n"
        f"inputs = prep_model.input\n"
        f"x = prep_model.output\n"
        f"x = GatedResidualNetwork(units=64)(x)\n"
        f"x = keras.layers.Dropout(0.2)(x)\n"
        f"x = keras.layers.Dense(32, activation='relu')(x)\n"
        f"outputs = keras.layers.Dense(1, activation='{output_activation}')(x)\n"
        f"\n"
        f"full_model = keras.Model(inputs=inputs, outputs=outputs)\n"
        f"\n"
        f"# ── Step 3: MLPotion Training ──\n"
        f"config = ModelTrainingConfig(\n"
        f"    epochs=50,\n"
        f"    batch_size=32,\n"
        f"    optimizer='adam',\n"
        f"    loss='{loss}',\n"
        f")\n"
        f"\n"
        f"trainer = ModelTrainer(config=config)\n"
        f"X = {var_name}.drop(columns=['{target}'])\n"
        f"y = {var_name}['{target}']\n"
        f"X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n"
        f"\n"
        f"history = trainer.train(\n"
        f"    model=full_model,\n"
        f"    train_data=(X_train, y_train),\n"
        f"    val_data=(X_test, y_test),\n"
        f")\n"
        f"print('🎉 Full UnicoLab pipeline complete!')"
    )

    return {
        "name": "🦄 UnicoLab Full Pipeline (KDP + KerasFactory + MLPotion)",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 90 if n_rows > 2000 else 78,
        "speed": "medium",
        "interpretability": "medium",
        "reasons": [
            "End-to-end pipeline: preprocessing → model → training",
            "KDP handles all feature engineering as Keras layers",
            "KerasFactory GRN captures complex feature interactions",
            "MLPotion provides managed, reproducible training",
            "Entire pipeline deploys as a single Keras model",
        ],
        "caveats": [
            "Requires all 3 packages: pip install 'flowyml-notebook[keras]'",
            "Best for datasets with 1000+ samples",
        ],
        "code": code,
    }
