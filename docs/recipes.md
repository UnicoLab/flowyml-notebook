# 🧾 Cell Recipes

FlowyML Notebook allows you to create, share, and reuse "Recipes" — pre-configured cell templates for common ML tasks.

## What is a Recipe?

A recipe is a reusable block of code and configuration that can be injected into any notebook. Recipes can range from simple data loading snippets to complex model training loops and visualization templates.

## Built-in Recipes

FlowyML Notebook comes with several high-performance built-in recipes:
- **Data Loading**: S3/GCS connectors, SQL transformations.
- **ML Baseline**: XGBoost/LightGBM training with optimized defaults.
- **Explainability**: SHAP/LIME visualization templates.
- **Monitoring**: Drift detection and quality report generation.

## Creating Custom Recipes

You can save any cell as a custom recipe directly from the GUI:
1.  Write your code in a cell.
2.  Click the **"Save as Recipe"** icon in the cell header.
3.  Provide a **Name**, **Category**, and **Description**.

Custom recipes are stored locally in `~/.flowyml/recipes/` as `.recipe.json` files.

## Sharing Recipes

Recipes can be shared with your team in two ways:
1.  **Manual Export**: Export a recipe as a JSON file and share it.
2.  **GitHub Hub**: Sync your recipes to a central GitHub repository using the [Team Collaboration](collaboration.md) feature.

## Usage Tracking

FlowyML Notebook automatically tracks how many times each recipe is used. This helps teams identify the most valuable snippets and promotes best practices across the organization.
