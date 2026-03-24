"""KDP (Keras Data Processor) adapter for SmartPrep suggestions.

Maps detected DataFrame feature types to KDP ``FeatureType`` enums
and generates ready-to-use ``PreprocessingModel`` code snippets.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Feature-type mapping ──────────────────────────────────────────────────────

# Maps FlowyML ML-Insights feature types → KDP FeatureType enum names
_FEATURE_TYPE_MAP: dict[str, str] = {
    "continuous": "FLOAT_NORMALIZED",
    "binary": "INTEGER_CATEGORICAL",
    "ordinal": "INTEGER_CATEGORICAL",
    "nominal": "STRING_CATEGORICAL",
    "high_cardinality": "STRING_CATEGORICAL",
    "temporal": "FLOAT_NORMALIZED",  # dates pre-extracted to numeric
}

# KDP advanced options keyed by data characteristics
_KDP_OPTION_DEFAULTS = {
    "use_distribution_aware": True,
    "tabular_attention": True,
}


def map_feature_types(
    feature_types: dict[str, str],
    target: str | None = None,
) -> dict[str, str]:
    """Convert ML-Insights feature type dict to KDP FeatureType mapping.

    Args:
        feature_types: ``{column_name: flowyml_type}`` from ML Insights.
        target: Target column to exclude from features.

    Returns:
        ``{column_name: "FeatureType.XXX"}`` for KDP features_specs.
    """
    specs: dict[str, str] = {}
    for col, ftype in feature_types.items():
        if col == target:
            continue
        kdp_type = _FEATURE_TYPE_MAP.get(ftype, "FLOAT_NORMALIZED")
        specs[col] = f"FeatureType.{kdp_type}"
    return specs


def generate_preprocessing_suggestion(
    var_name: str,
    feature_types: dict[str, str],
    n_rows: int,
    n_cols: int,
    target: str | None = None,
    data_path: str | None = None,
) -> dict[str, Any]:
    """Generate a SmartPrep suggestion using KDP ``PreprocessingModel``.

    Args:
        var_name: DataFrame variable name in the notebook namespace.
        feature_types: ``{col: type}`` from ML Insights analysis.
        n_rows: Number of rows.
        n_cols: Number of columns.
        target: Optional target column (excluded from features).
        data_path: Optional path to CSV file for KDP.

    Returns:
        Suggestion dict compatible with SmartPrep response format.
    """
    specs = map_feature_types(feature_types, target=target)
    if not specs:
        return {}

    # Build the features_specs dict as formatted Python string
    specs_lines = []
    for col, ftype in specs.items():
        specs_lines.append(f'    "{col}": {ftype},')
    specs_block = "\n".join(specs_lines)

    # Decide which advanced features to enable based on data size
    use_distribution = n_rows >= 100
    use_attention = n_rows >= 500 and n_cols >= 4

    code = (
        f"from kdp import PreprocessingModel, FeatureType\n"
        f"\n"
        f"# Define feature types (auto-detected from your data)\n"
        f"features_specs = {{\n"
        f"{specs_block}\n"
        f"}}\n"
        f"\n"
        f"# Build the KDP preprocessing model\n"
        f"preprocessor = PreprocessingModel(\n"
        f"    path_data=\"data.csv\",  # or pass DataFrame directly\n"
        f"    features_specs=features_specs,\n"
        f"    use_distribution_aware={use_distribution},\n"
        f"    tabular_attention={use_attention},\n"
        f")\n"
        f"result = preprocessor.build_preprocessor()\n"
        f"preprocessing_model = result[\"model\"]\n"
        f"\n"
        f"# Use as standalone or as first layers of your Keras model\n"
        f"print(f\"✅ KDP preprocessor ready — {{preprocessing_model.count_params():,}} parameters\")\n"
        f"preprocessing_model.summary()"
    )

    n_features = len(specs)
    return {
        "type": "kdp_preprocessing",
        "severity": "recommended",
        "column": "__all__",
        "ecosystem": "unicolab",
        "title": f"🧪 KDP Smart Preprocessing — {n_features} features auto-configured",
        "reason": (
            f"KDP can process all {n_features} features in a single pass as Keras layers. "
            f"Distribution-aware encoding + tabular attention capture complex interactions "
            f"for better model performance. Deploys as part of your model."
        ),
        "code": code,
    }
