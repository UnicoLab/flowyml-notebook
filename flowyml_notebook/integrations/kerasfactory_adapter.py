"""KerasFactory adapter for Algorithm Matchmaker recommendations.

Generates model-building code using KerasFactory reusable layers
and production-ready model architectures for tabular data.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_model_recommendation(
    var_name: str,
    task_type: str,
    target: str,
    feature_names: list[str],
    n_rows: int,
    n_features: int,
    has_categorical: bool = False,
) -> dict[str, Any]:
    """Generate an Algorithm Matchmaker recommendation using KerasFactory.

    Args:
        var_name: DataFrame variable name.
        task_type: ``"classification"`` or ``"regression"``.
        target: Target column name.
        feature_names: List of feature column names.
        n_rows: Number of samples.
        n_features: Number of features.
        has_categorical: Whether dataset has categorical features.

    Returns:
        Recommendation dict compatible with Algorithm Matchmaker format.
    """
    # Select architecture based on task
    if task_type == "classification":
        return _classification_recommendation(
            var_name, target, feature_names, n_rows, n_features, has_categorical,
        )
    elif task_type == "regression":
        return _regression_recommendation(
            var_name, target, feature_names, n_rows, n_features, has_categorical,
        )
    else:
        return _unsupervised_recommendation(var_name, feature_names, n_rows, n_features)


def generate_advanced_model_recommendation(
    var_name: str,
    task_type: str,
    target: str,
    feature_names: list[str],
    n_rows: int,
    n_features: int,
) -> dict[str, Any]:
    """Generate an advanced KerasFactory recommendation with custom layers.

    Uses advanced layers like ``TabularAttention``, ``GatedResidualNetwork``,
    and ``DistributionTransformLayer`` for maximum performance.
    """
    features_str = ", ".join(f"'{f}'" for f in feature_names[:10])
    output_activation = "sigmoid" if task_type == "classification" else "linear"
    loss = "binary_crossentropy" if task_type == "classification" else "mse"
    metrics = "['accuracy']" if task_type == "classification" else "['mae']"

    code = (
        f"import keras\n"
        f"from kerasfactory.layers import (\n"
        f"    DistributionTransformLayer,\n"
        f"    GatedFeatureFusion,\n"
        f"    TabularAttention,\n"
        f"    GatedResidualNetwork,\n"
        f")\n"
        f"from sklearn.model_selection import train_test_split\n"
        f"\n"
        f"# Prepare data\n"
        f"X = {var_name}.drop(columns=['{target}'])\n"
        f"y = {var_name}['{target}']\n"
        f"X_train, X_test, y_train, y_test = train_test_split(\n"
        f"    X, y, test_size=0.2, random_state=42\n"
        f")\n"
        f"\n"
        f"# Build advanced model with KerasFactory layers\n"
        f"inputs = keras.Input(shape=({n_features},), name='features')\n"
        f"\n"
        f"# Smart distribution transform\n"
        f"x = DistributionTransformLayer(transform_type='auto')(inputs)\n"
        f"\n"
        f"# Gated Residual Network for feature processing\n"
        f"x = GatedResidualNetwork(units=64)(x)\n"
        f"x = keras.layers.Dropout(0.2)(x)\n"
        f"x = GatedResidualNetwork(units=32)(x)\n"
        f"\n"
        f"# Final prediction\n"
        f"outputs = keras.layers.Dense(1, activation='{output_activation}')(x)\n"
        f"\n"
        f"model = keras.Model(inputs=inputs, outputs=outputs)\n"
        f"model.compile(\n"
        f"    optimizer='adam',\n"
        f"    loss='{loss}',\n"
        f"    metrics={metrics},\n"
        f")\n"
        f"\n"
        f"# Train\n"
        f"history = model.fit(\n"
        f"    X_train, y_train,\n"
        f"    validation_data=(X_test, y_test),\n"
        f"    epochs=50,\n"
        f"    batch_size=32,\n"
        f"    verbose=1,\n"
        f")\n"
        f"print(f'✅ Final val_loss: {{history.history[\"val_loss\"][-1]:.4f}}')"
    )

    return {
        "name": "KerasFactory Advanced (GRN + Attention)",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 88 if n_rows > 1000 else 75,
        "speed": "medium",
        "interpretability": "medium",
        "reasons": [
            "Gated Residual Networks learn complex feature interactions",
            "Distribution-aware transform handles skewed data automatically",
            "Production-ready Keras model — deploy as single unit",
            f"Strong performance with {n_rows:,} samples",
        ],
        "caveats": [
            "Requires Keras 3+ and KerasFactory installed",
            "Needs GPU for large datasets (>100K rows)",
        ],
        "code": code,
    }


# ── Private helpers ───────────────────────────────────────────────────────────


def _classification_recommendation(
    var_name: str,
    target: str,
    feature_names: list[str],
    n_rows: int,
    n_features: int,
    has_categorical: bool,
) -> dict[str, Any]:
    """KerasFactory classification recommendation."""
    features_str = ", ".join(f"'{f}'" for f in feature_names[:10])

    code = (
        f"from kerasfactory.models import BaseFeedForwardModel\n"
        f"from sklearn.model_selection import train_test_split\n"
        f"import numpy as np\n"
        f"\n"
        f"# Prepare data\n"
        f"X = {var_name}.drop(columns=['{target}'])\n"
        f"y = {var_name}['{target}']\n"
        f"X_train, X_test, y_train, y_test = train_test_split(\n"
        f"    X, y, test_size=0.2, random_state=42\n"
        f")\n"
        f"\n"
        f"# Build model with KerasFactory\n"
        f"feature_cols = [{features_str}]\n"
        f"model = BaseFeedForwardModel(\n"
        f"    feature_names=feature_cols,\n"
        f"    hidden_units=[128, 64, 32],\n"
        f"    output_units=1,\n"
        f"    dropout_rate=0.3,\n"
        f")\n"
        f"\n"
        f"model.compile(\n"
        f"    optimizer='adam',\n"
        f"    loss='binary_crossentropy',\n"
        f"    metrics=['accuracy'],\n"
        f")\n"
        f"\n"
        f"# Prepare inputs (one array per feature)\n"
        f"train_inputs = [X_train[c].values for c in feature_cols]\n"
        f"test_inputs = [X_test[c].values for c in feature_cols]\n"
        f"\n"
        f"history = model.fit(\n"
        f"    train_inputs, y_train,\n"
        f"    validation_data=(test_inputs, y_test),\n"
        f"    epochs=30, batch_size=32, verbose=1,\n"
        f")\n"
        f"print(f'✅ Accuracy: {{model.evaluate(test_inputs, y_test, verbose=0)[1]:.4f}}')"
    )

    return {
        "name": "KerasFactory Neural Network",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 85 if n_rows > 1000 else 72,
        "speed": "medium",
        "interpretability": "low",
        "reasons": [
            "Production-ready Keras model with one line of code",
            "Built-in dropout regularization",
            "Deploys as a Keras SavedModel for serving",
            f"Good for {n_rows:,} samples with {n_features} features",
        ],
        "caveats": [
            "Requires KerasFactory: pip install kerasfactory",
            "Neural networks need more data than tree-based models",
        ],
        "code": code,
    }


def _regression_recommendation(
    var_name: str,
    target: str,
    feature_names: list[str],
    n_rows: int,
    n_features: int,
    has_categorical: bool,
) -> dict[str, Any]:
    """KerasFactory regression recommendation."""
    features_str = ", ".join(f"'{f}'" for f in feature_names[:10])

    code = (
        f"from kerasfactory.models import BaseFeedForwardModel\n"
        f"from sklearn.model_selection import train_test_split\n"
        f"from sklearn.metrics import mean_squared_error, r2_score\n"
        f"import numpy as np\n"
        f"\n"
        f"# Prepare data\n"
        f"X = {var_name}.drop(columns=['{target}'])\n"
        f"y = {var_name}['{target}']\n"
        f"X_train, X_test, y_train, y_test = train_test_split(\n"
        f"    X, y, test_size=0.2, random_state=42\n"
        f")\n"
        f"\n"
        f"# Build model with KerasFactory\n"
        f"feature_cols = [{features_str}]\n"
        f"model = BaseFeedForwardModel(\n"
        f"    feature_names=feature_cols,\n"
        f"    hidden_units=[128, 64, 32],\n"
        f"    output_units=1,\n"
        f"    dropout_rate=0.2,\n"
        f")\n"
        f"\n"
        f"model.compile(optimizer='adam', loss='mse', metrics=['mae'])\n"
        f"\n"
        f"# Prepare inputs (one array per feature)\n"
        f"train_inputs = [X_train[c].values for c in feature_cols]\n"
        f"test_inputs = [X_test[c].values for c in feature_cols]\n"
        f"\n"
        f"history = model.fit(\n"
        f"    train_inputs, y_train,\n"
        f"    validation_data=(test_inputs, y_test),\n"
        f"    epochs=50, batch_size=32, verbose=1,\n"
        f")\n"
        f"\n"
        f"y_pred = model.predict(test_inputs).flatten()\n"
        f"print(f'RMSE: {{np.sqrt(mean_squared_error(y_test, y_pred)):.4f}}')\n"
        f"print(f'R²:   {{r2_score(y_test, y_pred):.4f}}')"
    )

    return {
        "name": "KerasFactory Neural Network",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 83 if n_rows > 1000 else 70,
        "speed": "medium",
        "interpretability": "low",
        "reasons": [
            "Production-ready Keras regressor with minimal setup",
            "Handles non-linear relationships automatically",
            "Deploys as a Keras SavedModel",
            f"Suitable for {n_rows:,} samples",
        ],
        "caveats": [
            "Requires KerasFactory: pip install kerasfactory",
            "Consider tree models if dataset is small (<500 rows)",
        ],
        "code": code,
    }


def _unsupervised_recommendation(
    var_name: str,
    feature_names: list[str],
    n_rows: int,
    n_features: int,
) -> dict[str, Any]:
    """KerasFactory autoencoder for unsupervised anomaly detection."""
    code = (
        f"import keras\n"
        f"from kerasfactory.layers import DistributionTransformLayer\n"
        f"from sklearn.preprocessing import StandardScaler\n"
        f"import numpy as np\n"
        f"\n"
        f"# Prepare data\n"
        f"X = {var_name}.select_dtypes(include='number').dropna()\n"
        f"scaler = StandardScaler()\n"
        f"X_scaled = scaler.fit_transform(X)\n"
        f"\n"
        f"# Build autoencoder with KerasFactory transforms\n"
        f"inputs = keras.Input(shape=({n_features},))\n"
        f"x = DistributionTransformLayer(transform_type='auto')(inputs)\n"
        f"x = keras.layers.Dense(32, activation='relu')(x)\n"
        f"encoded = keras.layers.Dense(8, activation='relu')(x)\n"
        f"x = keras.layers.Dense(32, activation='relu')(encoded)\n"
        f"decoded = keras.layers.Dense({n_features}, activation='linear')(x)\n"
        f"\n"
        f"autoencoder = keras.Model(inputs, decoded)\n"
        f"autoencoder.compile(optimizer='adam', loss='mse')\n"
        f"autoencoder.fit(X_scaled, X_scaled, epochs=50, batch_size=32, verbose=1)\n"
        f"\n"
        f"# Anomaly detection via reconstruction error\n"
        f"reconstructed = autoencoder.predict(X_scaled)\n"
        f"mse = np.mean((X_scaled - reconstructed) ** 2, axis=1)\n"
        f"threshold = np.percentile(mse, 95)\n"
        f"anomalies = mse > threshold\n"
        f"print(f'🔍 Found {{anomalies.sum()}} anomalies (threshold={{threshold:.4f}})')"
    )

    return {
        "name": "KerasFactory Autoencoder (Anomaly Detection)",
        "category": "deep_learning",
        "ecosystem": "unicolab",
        "score": 75,
        "speed": "medium",
        "interpretability": "low",
        "reasons": [
            "Detects anomalies via reconstruction error",
            "Distribution-aware transform handles skewed features",
            "No labels needed — fully unsupervised",
        ],
        "caveats": [
            "Requires KerasFactory: pip install kerasfactory",
            "Threshold selection is semi-manual",
        ],
        "code": code,
    }
