"""Cell Snippets Library for FlowyML Notebook.

Provides a built-in library of reusable data science code snippets
that users can search, insert, and contribute to. Unlike recipes
(multi-cell workflows), snippets are short, single-purpose code blocks.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Snippet:
    """A reusable code snippet for data science workflows."""

    id: str = ""
    title: str = ""
    description: str = ""
    code: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    language: str = "python"
    difficulty: str = "beginner"  # beginner / intermediate / advanced
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    uses: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "code": self.code,
            "category": self.category,
            "tags": list(self.tags),
            "language": self.language,
            "difficulty": self.difficulty,
            "created_at": self.created_at,
            "uses": self.uses,
        }


# ── Built-in snippets ───────────────────────────────────────────────────


def _builtin_snippets() -> list[Snippet]:
    """Return the full set of built-in data science snippets."""
    return [
        # ── Data Loading ─────────────────────────────────────────────
        Snippet(
            id="builtin-load-csv",
            title="Load CSV File",
            description="Read a CSV file into a pandas DataFrame with common options.",
            category="Data Loading",
            tags=["pandas", "csv", "io"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "df = pd.read_csv(\n"
                "    'data.csv',\n"
                "    sep=',',\n"
                "    encoding='utf-8',\n"
                "    na_values=['NA', 'N/A', ''],\n"
                "    parse_dates=['date_column'],\n"
                "    dtype={'id': str},\n"
                ")\n"
                "print(f'Loaded {len(df)} rows, {len(df.columns)} columns')\n"
                "df.head()"
            ),
        ),
        Snippet(
            id="builtin-load-excel",
            title="Load Excel File",
            description="Read an Excel workbook sheet into a DataFrame.",
            category="Data Loading",
            tags=["pandas", "excel", "io"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "df = pd.read_excel(\n"
                "    'data.xlsx',\n"
                "    sheet_name='Sheet1',\n"
                "    header=0,\n"
                "    usecols='A:F',\n"
                "    engine='openpyxl',\n"
                ")\n"
                "print(f'Loaded {len(df)} rows from Excel')\n"
                "df.head()"
            ),
        ),
        Snippet(
            id="builtin-load-json",
            title="Load JSON File",
            description="Read JSON data (records or nested) into a DataFrame.",
            category="Data Loading",
            tags=["pandas", "json", "io"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "# Flat JSON / JSON lines\n"
                "df = pd.read_json('data.json', orient='records', lines=False)\n"
                "\n"
                "# For nested JSON, normalize first:\n"
                "# import json\n"
                "# with open('nested.json') as f:\n"
                "#     raw = json.load(f)\n"
                "# df = pd.json_normalize(raw, record_path='items', meta=['id'])\n"
                "\n"
                "print(f'Loaded {len(df)} rows')\n"
                "df.head()"
            ),
        ),
        Snippet(
            id="builtin-load-sql",
            title="Load from SQL Database",
            description="Query a SQL database and load results into a DataFrame.",
            category="Data Loading",
            tags=["pandas", "sql", "database", "sqlalchemy"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "from sqlalchemy import create_engine\n"
                "\n"
                "engine = create_engine('sqlite:///my_database.db')\n"
                "# engine = create_engine('postgresql://user:pass@host:5432/dbname')\n"
                "\n"
                "query = '''\n"
                "SELECT *\n"
                "FROM my_table\n"
                "WHERE created_at >= '2024-01-01'\n"
                "ORDER BY id\n"
                "LIMIT 10000\n"
                "'''\n"
                "\n"
                "df = pd.read_sql(query, engine)\n"
                "print(f'Loaded {len(df)} rows from SQL')\n"
                "df.head()"
            ),
        ),
        Snippet(
            id="builtin-load-api",
            title="Load from REST API",
            description="Fetch data from a REST API endpoint and create a DataFrame.",
            category="Data Loading",
            tags=["api", "requests", "json", "rest"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import requests\n"
                "\n"
                "url = 'https://api.example.com/data'\n"
                "headers = {'Authorization': 'Bearer YOUR_TOKEN'}\n"
                "params = {'page': 1, 'per_page': 100}\n"
                "\n"
                "response = requests.get(url, headers=headers, params=params, timeout=30)\n"
                "response.raise_for_status()\n"
                "\n"
                "data = response.json()\n"
                "df = pd.DataFrame(data['results'])  # adjust key as needed\n"
                "print(f'Fetched {len(df)} records from API')\n"
                "df.head()"
            ),
        ),
        # ── Data Cleaning ────────────────────────────────────────────
        Snippet(
            id="builtin-handle-missing",
            title="Handle Missing Values",
            description="Detect, analyze, and fill or drop missing values in a DataFrame.",
            category="Data Cleaning",
            tags=["pandas", "missing", "fillna", "dropna"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "# Summarize missing data\n"
                "missing = df.isnull().sum()\n"
                "missing_pct = (missing / len(df) * 100).round(1)\n"
                "print(pd.DataFrame({'count': missing, 'pct': missing_pct}).query('count > 0'))\n"
                "\n"
                "# Strategy 1: Drop rows with any nulls\n"
                "# df_clean = df.dropna()\n"
                "\n"
                "# Strategy 2: Fill numeric with median, categorical with mode\n"
                "for col in df.select_dtypes(include='number').columns:\n"
                "    df[col] = df[col].fillna(df[col].median())\n"
                "for col in df.select_dtypes(include='object').columns:\n"
                "    df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else 'Unknown')\n"
                "\n"
                "print(f'Remaining nulls: {df.isnull().sum().sum()}')"
            ),
        ),
        Snippet(
            id="builtin-remove-duplicates",
            title="Remove Duplicates",
            description="Find and remove duplicate rows from a DataFrame.",
            category="Data Cleaning",
            tags=["pandas", "duplicates", "dedup"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "# Check duplicates\n"
                "n_dupes = df.duplicated().sum()\n"
                "print(f'Found {n_dupes} duplicate rows ({n_dupes / len(df) * 100:.1f}%)')\n"
                "\n"
                "# Show duplicate rows\n"
                "if n_dupes > 0:\n"
                "    print(df[df.duplicated(keep=False)].head(10))\n"
                "\n"
                "# Remove duplicates (keep first occurrence)\n"
                "df = df.drop_duplicates(keep='first').reset_index(drop=True)\n"
                "print(f'After dedup: {len(df)} rows')"
            ),
        ),
        Snippet(
            id="builtin-fix-dtypes",
            title="Fix Data Types",
            description="Convert columns to correct data types for analysis.",
            category="Data Cleaning",
            tags=["pandas", "dtypes", "astype", "convert"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "\n"
                "# Show current dtypes\n"
                "print(df.dtypes)\n"
                "\n"
                "# Convert columns\n"
                "df['id'] = df['id'].astype(str)\n"
                "df['amount'] = pd.to_numeric(df['amount'], errors='coerce')\n"
                "df['date'] = pd.to_datetime(df['date'], errors='coerce')\n"
                "df['category'] = df['category'].astype('category')\n"
                "df['is_active'] = df['is_active'].astype(bool)\n"
                "\n"
                "# Downcast numerics to save memory\n"
                "for col in df.select_dtypes(include=['int64']).columns:\n"
                "    df[col] = pd.to_numeric(df[col], downcast='integer')\n"
                "for col in df.select_dtypes(include=['float64']).columns:\n"
                "    df[col] = pd.to_numeric(df[col], downcast='float')\n"
                "\n"
                "print(f'Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB')"
            ),
        ),
        Snippet(
            id="builtin-string-cleaning",
            title="Clean String Columns",
            description="Normalize and clean text data in string columns.",
            category="Data Cleaning",
            tags=["pandas", "string", "text", "regex", "strip"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "\n"
                "col = 'name'  # target column\n"
                "\n"
                "# Strip whitespace\n"
                "df[col] = df[col].str.strip()\n"
                "\n"
                "# Normalize case\n"
                "df[col] = df[col].str.lower()  # or .str.title()\n"
                "\n"
                "# Remove special characters\n"
                "df[col] = df[col].str.replace(r'[^\\w\\s]', '', regex=True)\n"
                "\n"
                "# Collapse multiple spaces\n"
                "df[col] = df[col].str.replace(r'\\s+', ' ', regex=True)\n"
                "\n"
                "# Replace empty strings with NaN\n"
                "df[col] = df[col].replace('', pd.NA)\n"
                "\n"
                "print(f'Unique values: {df[col].nunique()}')\n"
                "df[col].value_counts().head(10)"
            ),
        ),
        # ── EDA ──────────────────────────────────────────────────────
        Snippet(
            id="builtin-eda-describe",
            title="Quick DataFrame Summary",
            description="Get comprehensive statistical summary of your DataFrame.",
            category="EDA",
            tags=["pandas", "describe", "info", "summary"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "print(f'Shape: {df.shape}')\n"
                "print(f'Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB')\n"
                "print()\n"
                "\n"
                "# Numeric summary\n"
                "print('=== Numeric Columns ===')\n"
                "print(df.describe().round(2))\n"
                "print()\n"
                "\n"
                "# Categorical summary\n"
                "print('=== Categorical Columns ===')\n"
                "print(df.describe(include='object'))\n"
                "print()\n"
                "\n"
                "# Missing data\n"
                "missing = df.isnull().sum()\n"
                "if missing.any():\n"
                "    print('=== Missing Values ===')\n"
                "    print(missing[missing > 0])"
            ),
        ),
        Snippet(
            id="builtin-eda-value-counts",
            title="Value Counts for Categoricals",
            description="Explore the distribution of categorical columns.",
            category="EDA",
            tags=["pandas", "value_counts", "categorical", "distribution"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "# Value counts for a specific column\n"
                "col = 'category'  # change this\n"
                "counts = df[col].value_counts()\n"
                "print(f'=== {col} ({df[col].nunique()} unique) ===')\n"
                "print(counts.head(15))\n"
                "print()\n"
                "\n"
                "# Value counts with percentages\n"
                "pct = df[col].value_counts(normalize=True).mul(100).round(1)\n"
                "summary = pd.DataFrame({'count': counts, 'pct': pct})\n"
                "print(summary.head(15))"
            ),
        ),
        Snippet(
            id="builtin-eda-correlation",
            title="Correlation Matrix",
            description="Compute and display the correlation matrix for numeric features.",
            category="EDA",
            tags=["pandas", "correlation", "heatmap", "seaborn"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import seaborn as sns\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "# Compute correlation matrix\n"
                "corr = df.select_dtypes(include='number').corr()\n"
                "\n"
                "# Plot heatmap\n"
                "plt.figure(figsize=(10, 8))\n"
                "mask = corr.abs() < 0.05  # hide weak correlations\n"
                "sns.heatmap(\n"
                "    corr,\n"
                "    annot=True,\n"
                "    fmt='.2f',\n"
                "    cmap='RdBu_r',\n"
                "    center=0,\n"
                "    mask=mask,\n"
                "    square=True,\n"
                "    linewidths=0.5,\n"
                ")\n"
                "plt.title('Correlation Matrix')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-eda-distribution",
            title="Distribution Plot",
            description="Plot the distribution of a numeric column with histogram and KDE.",
            category="EDA",
            tags=["seaborn", "matplotlib", "histogram", "kde", "distribution"],
            difficulty="beginner",
            code=(
                "import matplotlib.pyplot as plt\n"
                "import seaborn as sns\n"
                "\n"
                "col = 'value'  # change this\n"
                "\n"
                "fig, axes = plt.subplots(1, 2, figsize=(12, 4))\n"
                "\n"
                "# Histogram + KDE\n"
                "sns.histplot(df[col].dropna(), kde=True, ax=axes[0], color='steelblue')\n"
                "axes[0].set_title(f'Distribution of {col}')\n"
                "\n"
                "# Box plot\n"
                "sns.boxplot(x=df[col].dropna(), ax=axes[1], color='steelblue')\n"
                "axes[1].set_title(f'Box Plot of {col}')\n"
                "\n"
                "plt.tight_layout()\n"
                "plt.show()\n"
                "\n"
                "# Quick stats\n"
                "print(df[col].describe())"
            ),
        ),
        Snippet(
            id="builtin-eda-missing-heatmap",
            title="Missing Data Heatmap",
            description="Visualize missing data patterns across the DataFrame.",
            category="EDA",
            tags=["seaborn", "matplotlib", "missing", "heatmap", "nulls"],
            difficulty="intermediate",
            code=(
                "import matplotlib.pyplot as plt\n"
                "import seaborn as sns\n"
                "import pandas as pd\n"
                "\n"
                "# Missing data summary\n"
                "missing = df.isnull().sum()\n"
                "missing_pct = (missing / len(df) * 100).round(1)\n"
                "missing_df = pd.DataFrame({'count': missing, 'pct': missing_pct})\n"
                "missing_df = missing_df[missing_df['count'] > 0].sort_values('pct', ascending=False)\n"
                "print(missing_df)\n"
                "\n"
                "# Heatmap of nullity\n"
                "if not missing_df.empty:\n"
                "    plt.figure(figsize=(12, 6))\n"
                "    sns.heatmap(\n"
                "        df[missing_df.index].isnull().T,\n"
                "        cbar=False,\n"
                "        cmap='YlOrRd',\n"
                "        yticklabels=True,\n"
                "    )\n"
                "    plt.title('Missing Data Pattern (yellow = missing)')\n"
                "    plt.xlabel('Row index')\n"
                "    plt.tight_layout()\n"
                "    plt.show()\n"
                "else:\n"
                "    print('No missing data found!')"
            ),
        ),
        # ── Feature Engineering ──────────────────────────────────────
        Snippet(
            id="builtin-feat-onehot",
            title="One-Hot Encoding",
            description="Convert categorical columns to one-hot encoded features.",
            category="Feature Engineering",
            tags=["pandas", "encoding", "one-hot", "get_dummies", "categorical"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "\n"
                "cat_cols = ['category', 'region']  # columns to encode\n"
                "\n"
                "df_encoded = pd.get_dummies(\n"
                "    df,\n"
                "    columns=cat_cols,\n"
                "    drop_first=True,    # avoid multicollinearity\n"
                "    dtype=int,\n"
                ")\n"
                "\n"
                "print(f'Before: {df.shape[1]} columns')\n"
                "print(f'After:  {df_encoded.shape[1]} columns')\n"
                "df_encoded.head()"
            ),
        ),
        Snippet(
            id="builtin-feat-label-encode",
            title="Label Encoding",
            description="Encode categorical labels as integers with sklearn LabelEncoder.",
            category="Feature Engineering",
            tags=["sklearn", "encoding", "label", "ordinal"],
            difficulty="beginner",
            code=(
                "from sklearn.preprocessing import LabelEncoder\n"
                "import pandas as pd\n"
                "\n"
                "col = 'category'  # column to encode\n"
                "\n"
                "le = LabelEncoder()\n"
                "df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))\n"
                "\n"
                "# View mapping\n"
                "mapping = dict(zip(le.classes_, le.transform(le.classes_)))\n"
                "print(f'Label mapping: {mapping}')\n"
                "df[[col, f'{col}_encoded']].head(10)"
            ),
        ),
        Snippet(
            id="builtin-feat-scaling",
            title="Feature Scaling",
            description="StandardScaler and MinMaxScaler for numeric features.",
            category="Feature Engineering",
            tags=["sklearn", "scaling", "normalization", "standardization"],
            difficulty="intermediate",
            code=(
                "from sklearn.preprocessing import StandardScaler, MinMaxScaler\n"
                "import pandas as pd\n"
                "\n"
                "numeric_cols = df.select_dtypes(include='number').columns.tolist()\n"
                "\n"
                "# StandardScaler (mean=0, std=1)\n"
                "scaler = StandardScaler()\n"
                "df_scaled = df.copy()\n"
                "df_scaled[numeric_cols] = scaler.fit_transform(df[numeric_cols])\n"
                "\n"
                "# MinMaxScaler (range 0-1)\n"
                "# scaler = MinMaxScaler()\n"
                "# df_scaled[numeric_cols] = scaler.fit_transform(df[numeric_cols])\n"
                "\n"
                "print('Scaled statistics:')\n"
                "print(df_scaled[numeric_cols].describe().round(2))"
            ),
        ),
        Snippet(
            id="builtin-feat-binning",
            title="Binning / Discretization",
            description="Bin a continuous variable into discrete intervals.",
            category="Feature Engineering",
            tags=["pandas", "binning", "cut", "qcut", "discretize"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "\n"
                "col = 'age'  # column to bin\n"
                "\n"
                "# Equal-width bins\n"
                "df[f'{col}_bin'] = pd.cut(\n"
                "    df[col],\n"
                "    bins=[0, 18, 30, 50, 65, 100],\n"
                "    labels=['<18', '18-30', '30-50', '50-65', '65+'],\n"
                ")\n"
                "\n"
                "# Equal-frequency bins (quantile-based)\n"
                "# df[f'{col}_qbin'] = pd.qcut(df[col], q=5, labels=False)\n"
                "\n"
                "print(df[f'{col}_bin'].value_counts().sort_index())"
            ),
        ),
        Snippet(
            id="builtin-feat-date",
            title="Date Feature Extraction",
            description="Extract useful features from datetime columns.",
            category="Feature Engineering",
            tags=["pandas", "datetime", "date", "time", "features"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "\n"
                "col = 'date'  # datetime column\n"
                "df[col] = pd.to_datetime(df[col])\n"
                "\n"
                "df['year'] = df[col].dt.year\n"
                "df['month'] = df[col].dt.month\n"
                "df['day_of_week'] = df[col].dt.dayofweek  # 0=Mon\n"
                "df['day_of_year'] = df[col].dt.dayofyear\n"
                "df['is_weekend'] = df[col].dt.dayofweek.isin([5, 6]).astype(int)\n"
                "df['quarter'] = df[col].dt.quarter\n"
                "df['hour'] = df[col].dt.hour  # if timestamps\n"
                "\n"
                "# Days since a reference date\n"
                "df['days_since'] = (pd.Timestamp.now() - df[col]).dt.days\n"
                "\n"
                "print(df[[col, 'year', 'month', 'day_of_week', 'is_weekend']].head())"
            ),
        ),
        # ── Modeling ─────────────────────────────────────────────────
        Snippet(
            id="builtin-model-split",
            title="Train / Test Split",
            description="Split data into training and test sets with stratification.",
            category="Modeling",
            tags=["sklearn", "train_test_split", "split", "stratify"],
            difficulty="beginner",
            code=(
                "from sklearn.model_selection import train_test_split\n"
                "\n"
                "target = 'target'  # target column\n"
                "features = [c for c in df.columns if c != target]\n"
                "\n"
                "X = df[features]\n"
                "y = df[target]\n"
                "\n"
                "X_train, X_test, y_train, y_test = train_test_split(\n"
                "    X, y,\n"
                "    test_size=0.2,\n"
                "    random_state=42,\n"
                "    stratify=y,  # remove for regression\n"
                ")\n"
                "\n"
                "print(f'Train: {X_train.shape[0]} samples')\n"
                "print(f'Test:  {X_test.shape[0]} samples')\n"
                "print(f'Target distribution (train):\\n{y_train.value_counts(normalize=True).round(3)}')"
            ),
        ),
        Snippet(
            id="builtin-model-cv",
            title="Cross-Validation",
            description="Evaluate a model with k-fold cross-validation.",
            category="Modeling",
            tags=["sklearn", "cross_val_score", "kfold", "validation"],
            difficulty="intermediate",
            code=(
                "from sklearn.model_selection import cross_val_score, StratifiedKFold\n"
                "from sklearn.ensemble import RandomForestClassifier\n"
                "import numpy as np\n"
                "\n"
                "model = RandomForestClassifier(n_estimators=100, random_state=42)\n"
                "\n"
                "cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)\n"
                "scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='accuracy')\n"
                "\n"
                "print(f'CV Accuracy: {scores.mean():.4f} ± {scores.std():.4f}')\n"
                "print(f'Per-fold:    {np.round(scores, 4)}')"
            ),
        ),
        Snippet(
            id="builtin-model-gridsearch",
            title="Grid Search Hyperparameters",
            description="Find optimal hyperparameters with GridSearchCV.",
            category="Modeling",
            tags=["sklearn", "gridsearch", "hyperparameter", "tuning"],
            difficulty="advanced",
            code=(
                "from sklearn.model_selection import GridSearchCV\n"
                "from sklearn.ensemble import RandomForestClassifier\n"
                "\n"
                "param_grid = {\n"
                "    'n_estimators': [50, 100, 200],\n"
                "    'max_depth': [5, 10, 20, None],\n"
                "    'min_samples_split': [2, 5, 10],\n"
                "    'min_samples_leaf': [1, 2, 4],\n"
                "}\n"
                "\n"
                "grid = GridSearchCV(\n"
                "    RandomForestClassifier(random_state=42),\n"
                "    param_grid,\n"
                "    cv=5,\n"
                "    scoring='accuracy',\n"
                "    n_jobs=-1,\n"
                "    verbose=1,\n"
                ")\n"
                "grid.fit(X_train, y_train)\n"
                "\n"
                "print(f'Best score: {grid.best_score_:.4f}')\n"
                "print(f'Best params: {grid.best_params_}')\n"
                "best_model = grid.best_estimator_"
            ),
        ),
        Snippet(
            id="builtin-model-xgboost",
            title="XGBoost Classifier",
            description="Train an XGBoost gradient boosting classifier.",
            category="Modeling",
            tags=["xgboost", "boosting", "classifier", "ml"],
            difficulty="advanced",
            code=(
                "import xgboost as xgb\n"
                "from sklearn.metrics import accuracy_score, classification_report\n"
                "\n"
                "model = xgb.XGBClassifier(\n"
                "    n_estimators=200,\n"
                "    max_depth=6,\n"
                "    learning_rate=0.1,\n"
                "    subsample=0.8,\n"
                "    colsample_bytree=0.8,\n"
                "    random_state=42,\n"
                "    eval_metric='logloss',\n"
                ")\n"
                "\n"
                "model.fit(\n"
                "    X_train, y_train,\n"
                "    eval_set=[(X_test, y_test)],\n"
                "    verbose=False,\n"
                ")\n"
                "\n"
                "y_pred = model.predict(X_test)\n"
                "print(f'Accuracy: {accuracy_score(y_test, y_pred):.4f}')\n"
                "print(classification_report(y_test, y_pred))"
            ),
        ),
        # ── Visualization ────────────────────────────────────────────
        Snippet(
            id="builtin-viz-bar",
            title="Matplotlib Bar Chart",
            description="Create a styled bar chart with matplotlib.",
            category="Visualization",
            tags=["matplotlib", "bar", "chart", "plot"],
            difficulty="beginner",
            code=(
                "import matplotlib.pyplot as plt\n"
                "\n"
                "categories = ['A', 'B', 'C', 'D', 'E']\n"
                "values = [23, 45, 12, 67, 34]\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 5))\n"
                "bars = ax.bar(categories, values, color='#3b82f6', edgecolor='white', linewidth=0.5)\n"
                "\n"
                "# Add value labels on bars\n"
                "for bar, val in zip(bars, values):\n"
                "    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,\n"
                "            str(val), ha='center', va='bottom', fontweight='bold')\n"
                "\n"
                "ax.set_title('Bar Chart', fontsize=14, fontweight='bold')\n"
                "ax.set_xlabel('Category')\n"
                "ax.set_ylabel('Value')\n"
                "ax.spines[['top', 'right']].set_visible(False)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-viz-heatmap",
            title="Seaborn Heatmap",
            description="Create a publication-quality heatmap with seaborn.",
            category="Visualization",
            tags=["seaborn", "heatmap", "matrix", "correlation"],
            difficulty="intermediate",
            code=(
                "import seaborn as sns\n"
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "\n"
                "# Example: correlation heatmap\n"
                "data = df.select_dtypes(include='number').corr()\n"
                "\n"
                "# Mask upper triangle\n"
                "mask = np.triu(np.ones_like(data, dtype=bool))\n"
                "\n"
                "plt.figure(figsize=(10, 8))\n"
                "sns.heatmap(\n"
                "    data,\n"
                "    mask=mask,\n"
                "    annot=True,\n"
                "    fmt='.2f',\n"
                "    cmap='coolwarm',\n"
                "    center=0,\n"
                "    square=True,\n"
                "    linewidths=0.5,\n"
                "    cbar_kws={'shrink': 0.8},\n"
                ")\n"
                "plt.title('Correlation Heatmap', fontsize=14, fontweight='bold')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-viz-plotly",
            title="Plotly Interactive Chart",
            description="Create an interactive scatter plot with Plotly Express.",
            category="Visualization",
            tags=["plotly", "interactive", "scatter", "html"],
            difficulty="intermediate",
            code=(
                "import plotly.express as px\n"
                "\n"
                "fig = px.scatter(\n"
                "    df,\n"
                "    x='x_column',\n"
                "    y='y_column',\n"
                "    color='category',\n"
                "    size='size_column',\n"
                "    hover_data=['extra_info'],\n"
                "    title='Interactive Scatter Plot',\n"
                "    template='plotly_dark',\n"
                ")\n"
                "\n"
                "fig.update_layout(\n"
                "    width=800,\n"
                "    height=500,\n"
                "    font=dict(size=12),\n"
                ")\n"
                "fig.show()"
            ),
        ),
        Snippet(
            id="builtin-viz-pairplot",
            title="Pair Plot",
            description="Create a pair plot matrix for exploring relationships between features.",
            category="Visualization",
            tags=["seaborn", "pairplot", "scatter", "matrix"],
            difficulty="beginner",
            code=(
                "import seaborn as sns\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "# Select columns to plot (keep it small: 3-6 columns)\n"
                "cols = df.select_dtypes(include='number').columns[:5].tolist()\n"
                "hue_col = 'target'  # optional: color by category\n"
                "\n"
                "g = sns.pairplot(\n"
                "    df[cols + [hue_col]].dropna(),\n"
                "    hue=hue_col,\n"
                "    diag_kind='kde',\n"
                "    plot_kws={'alpha': 0.6, 's': 20},\n"
                "    height=2.5,\n"
                ")\n"
                "g.figure.suptitle('Pair Plot', y=1.02, fontsize=14, fontweight='bold')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        # ── ML Evaluation ────────────────────────────────────────────
        Snippet(
            id="builtin-eval-confusion",
            title="Confusion Matrix",
            description="Plot a confusion matrix with counts and percentages.",
            category="ML Evaluation",
            tags=["sklearn", "confusion_matrix", "classification", "evaluation"],
            difficulty="intermediate",
            code=(
                "from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "cm = confusion_matrix(y_test, y_pred)\n"
                "\n"
                "fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n"
                "\n"
                "# Raw counts\n"
                "ConfusionMatrixDisplay(cm).plot(ax=axes[0], cmap='Blues')\n"
                "axes[0].set_title('Confusion Matrix (Counts)')\n"
                "\n"
                "# Normalized\n"
                "cm_norm = confusion_matrix(y_test, y_pred, normalize='true')\n"
                "ConfusionMatrixDisplay(cm_norm).plot(ax=axes[1], cmap='Blues', values_format='.2f')\n"
                "axes[1].set_title('Confusion Matrix (Normalized)')\n"
                "\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-eval-roc",
            title="ROC Curve",
            description="Plot the ROC curve and compute AUC for a binary classifier.",
            category="ML Evaluation",
            tags=["sklearn", "roc", "auc", "binary", "classification"],
            difficulty="intermediate",
            code=(
                "from sklearn.metrics import roc_curve, auc\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "# Get predicted probabilities\n"
                "y_proba = model.predict_proba(X_test)[:, 1]\n"
                "\n"
                "fpr, tpr, thresholds = roc_curve(y_test, y_proba)\n"
                "roc_auc = auc(fpr, tpr)\n"
                "\n"
                "plt.figure(figsize=(7, 6))\n"
                "plt.plot(fpr, tpr, color='#3b82f6', lw=2,\n"
                "         label=f'ROC curve (AUC = {roc_auc:.3f})')\n"
                "plt.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5, label='Random')\n"
                "plt.fill_between(fpr, tpr, alpha=0.1, color='#3b82f6')\n"
                "plt.xlabel('False Positive Rate')\n"
                "plt.ylabel('True Positive Rate')\n"
                "plt.title('ROC Curve')\n"
                "plt.legend(loc='lower right')\n"
                "plt.grid(alpha=0.3)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-eval-report",
            title="Classification Report",
            description="Generate a full classification report with precision, recall, and F1.",
            category="ML Evaluation",
            tags=["sklearn", "classification_report", "precision", "recall", "f1"],
            difficulty="beginner",
            code=(
                "from sklearn.metrics import classification_report, accuracy_score\n"
                "\n"
                "y_pred = model.predict(X_test)\n"
                "\n"
                "print(f'Accuracy: {accuracy_score(y_test, y_pred):.4f}')\n"
                "print()\n"
                "print(classification_report(y_test, y_pred, digits=3))"
            ),
        ),
        Snippet(
            id="builtin-eval-learning-curve",
            title="Learning Curve",
            description="Plot learning curves to diagnose bias/variance tradeoff.",
            category="ML Evaluation",
            tags=["sklearn", "learning_curve", "bias", "variance", "overfitting"],
            difficulty="advanced",
            code=(
                "from sklearn.model_selection import learning_curve\n"
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "train_sizes, train_scores, val_scores = learning_curve(\n"
                "    model, X_train, y_train,\n"
                "    train_sizes=np.linspace(0.1, 1.0, 10),\n"
                "    cv=5,\n"
                "    scoring='accuracy',\n"
                "    n_jobs=-1,\n"
                ")\n"
                "\n"
                "train_mean = train_scores.mean(axis=1)\n"
                "train_std = train_scores.std(axis=1)\n"
                "val_mean = val_scores.mean(axis=1)\n"
                "val_std = val_scores.std(axis=1)\n"
                "\n"
                "plt.figure(figsize=(8, 5))\n"
                "plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color='#3b82f6')\n"
                "plt.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.1, color='#ef4444')\n"
                "plt.plot(train_sizes, train_mean, 'o-', color='#3b82f6', label='Training')\n"
                "plt.plot(train_sizes, val_mean, 'o-', color='#ef4444', label='Validation')\n"
                "plt.xlabel('Training Set Size')\n"
                "plt.ylabel('Accuracy')\n"
                "plt.title('Learning Curve')\n"
                "plt.legend(loc='lower right')\n"
                "plt.grid(alpha=0.3)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        # ── Utilities ────────────────────────────────────────────────
        Snippet(
            id="builtin-util-timer",
            title="Timer Decorator",
            description="A reusable decorator to measure function execution time.",
            category="Utilities",
            tags=["timer", "decorator", "performance", "profiling"],
            difficulty="intermediate",
            code=(
                "import time\n"
                "import functools\n"
                "\n"
                "def timer(func):\n"
                '    """Decorator that prints the execution time of a function."""\n'
                "    @functools.wraps(func)\n"
                "    def wrapper(*args, **kwargs):\n"
                "        start = time.perf_counter()\n"
                "        result = func(*args, **kwargs)\n"
                "        elapsed = time.perf_counter() - start\n"
                "        print(f'{func.__name__} took {elapsed:.4f}s')\n"
                "        return result\n"
                "    return wrapper\n"
                "\n"
                "# Usage:\n"
                "# @timer\n"
                "# def my_function():\n"
                "#     ...\n"
                "print('Timer decorator defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-util-progress",
            title="Progress Bar with tqdm",
            description="Add a progress bar to any iterable with tqdm.",
            category="Utilities",
            tags=["tqdm", "progress", "loop", "iteration"],
            difficulty="beginner",
            code=(
                "from tqdm import tqdm\n"
                "import time\n"
                "\n"
                "# Basic usage with a list\n"
                "results = []\n"
                "for item in tqdm(range(100), desc='Processing'):\n"
                "    time.sleep(0.01)  # simulate work\n"
                "    results.append(item * 2)\n"
                "\n"
                "# With pandas apply\n"
                "# tqdm.pandas(desc='Applying')\n"
                "# df['new_col'] = df['col'].progress_apply(my_func)\n"
                "\n"
                "print(f'Processed {len(results)} items')"
            ),
        ),
        Snippet(
            id="builtin-util-memory",
            title="Memory Usage Report",
            description="Analyze memory usage of variables and DataFrames.",
            category="Utilities",
            tags=["memory", "sys", "pandas", "optimization"],
            difficulty="intermediate",
            code=(
                "import sys\n"
                "import pandas as pd\n"
                "\n"
                "# Memory usage of all variables\n"
                "var_sizes = []\n"
                "for name, obj in list(globals().items()):\n"
                "    if not name.startswith('_'):\n"
                "        size = sys.getsizeof(obj)\n"
                "        var_sizes.append((name, type(obj).__name__, size))\n"
                "\n"
                "mem_df = pd.DataFrame(var_sizes, columns=['Variable', 'Type', 'Bytes'])\n"
                "mem_df['MB'] = (mem_df['Bytes'] / 1024**2).round(2)\n"
                "mem_df = mem_df.sort_values('Bytes', ascending=False).head(20)\n"
                "print(mem_df.to_string(index=False))\n"
                "print(f'\\nTotal tracked: {mem_df[\"MB\"].sum():.1f} MB')"
            ),
        ),
        Snippet(
            id="builtin-util-seed",
            title="Set Random Seeds",
            description="Set random seeds for reproducible experiments across libraries.",
            category="Utilities",
            tags=["seed", "random", "reproducibility", "numpy", "torch"],
            difficulty="beginner",
            code=(
                "import random\n"
                "import os\n"
                "\n"
                "SEED = 42\n"
                "\n"
                "# Python built-in\n"
                "random.seed(SEED)\n"
                "os.environ['PYTHONHASHSEED'] = str(SEED)\n"
                "\n"
                "# NumPy\n"
                "import numpy as np\n"
                "np.random.seed(SEED)\n"
                "\n"
                "# PyTorch (if installed)\n"
                "try:\n"
                "    import torch\n"
                "    torch.manual_seed(SEED)\n"
                "    torch.cuda.manual_seed_all(SEED)\n"
                "    torch.backends.cudnn.deterministic = True\n"
                "    torch.backends.cudnn.benchmark = False\n"
                "except ImportError:\n"
                "    pass\n"
                "\n"
                "# TensorFlow (if installed)\n"
                "try:\n"
                "    import tensorflow as tf\n"
                "    tf.random.set_seed(SEED)\n"
                "except ImportError:\n"
                "    pass\n"
                "\n"
                "print(f'All random seeds set to {SEED} ✓')"
            ),
        ),
        # ── Production ───────────────────────────────────────────────
        Snippet(
            id="builtin-prod-logging",
            title="Logging Setup",
            description="Professional Python logging config with file and console handlers.",
            category="Production",
            tags=["logging", "production", "config", "handlers"],
            difficulty="intermediate",
            code=(
                "import logging\n"
                "import sys\n"
                "from pathlib import Path\n"
                "\n"
                "LOG_DIR = Path('logs')\n"
                "LOG_DIR.mkdir(exist_ok=True)\n"
                "\n"
                "# Formatter\n"
                "fmt = logging.Formatter(\n"
                "    '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',\n"
                "    datefmt='%Y-%m-%d %H:%M:%S',\n"
                ")\n"
                "\n"
                "# Console handler\n"
                "console_handler = logging.StreamHandler(sys.stdout)\n"
                "console_handler.setLevel(logging.INFO)\n"
                "console_handler.setFormatter(fmt)\n"
                "\n"
                "# File handler (rotating)\n"
                "from logging.handlers import RotatingFileHandler\n"
                "file_handler = RotatingFileHandler(\n"
                "    LOG_DIR / 'app.log',\n"
                "    maxBytes=10 * 1024 * 1024,  # 10 MB\n"
                "    backupCount=5,\n"
                ")\n"
                "file_handler.setLevel(logging.DEBUG)\n"
                "file_handler.setFormatter(fmt)\n"
                "\n"
                "# Root logger\n"
                "logger = logging.getLogger('myapp')\n"
                "logger.setLevel(logging.DEBUG)\n"
                "logger.addHandler(console_handler)\n"
                "logger.addHandler(file_handler)\n"
                "\n"
                "logger.info('Logging configured ✓')\n"
                "logger.debug('Debug messages go to file only')"
            ),
        ),
        Snippet(
            id="builtin-prod-config",
            title="Config Management",
            description="Pydantic BaseSettings for type-safe config with environment variables.",
            category="Production",
            tags=["pydantic", "config", "env", "settings", "production"],
            difficulty="intermediate",
            code=(
                "from pydantic_settings import BaseSettings\n"
                "from pydantic import Field\n"
                "\n"
                "\n"
                "class AppConfig(BaseSettings):\n"
                '    """Application configuration loaded from env vars / .env file."""\n'
                "\n"
                "    app_name: str = 'MyApp'\n"
                "    debug: bool = False\n"
                "    database_url: str = 'sqlite:///app.db'\n"
                "    api_key: str = Field(default='', description='API secret key')\n"
                "    max_workers: int = 4\n"
                "    log_level: str = 'INFO'\n"
                "\n"
                "    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}\n"
                "\n"
                "\n"
                "config = AppConfig()\n"
                "print(f'App:      {config.app_name}')\n"
                "print(f'Debug:    {config.debug}')\n"
                "print(f'DB URL:   {config.database_url}')\n"
                "print(f'Workers:  {config.max_workers}')\n"
                "print(f'Log:      {config.log_level}')"
            ),
        ),
        Snippet(
            id="builtin-prod-error-handling",
            title="Error Handling",
            description="Production try/except with custom exceptions and retry logic.",
            category="Production",
            tags=["error", "exception", "retry", "production", "resilience"],
            difficulty="advanced",
            code=(
                "import time\n"
                "import functools\n"
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\n"
                "class AppError(Exception):\n"
                '    """Base application error."""\n'
                "\n"
                "class DataError(AppError):\n"
                '    """Raised when data validation fails."""\n'
                "\n"
                "class ServiceError(AppError):\n"
                '    """Raised when an external service call fails."""\n'
                "\n"
                "\n"
                "def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):\n"
                '    """Retry decorator with exponential backoff."""\n'
                "    def decorator(func):\n"
                "        @functools.wraps(func)\n"
                "        def wrapper(*args, **kwargs):\n"
                "            last_exc = None\n"
                "            wait = delay\n"
                "            for attempt in range(1, max_retries + 1):\n"
                "                try:\n"
                "                    return func(*args, **kwargs)\n"
                "                except Exception as exc:\n"
                "                    last_exc = exc\n"
                "                    logger.warning(\n"
                "                        f'{func.__name__} attempt {attempt}/{max_retries} '\n"
                "                        f'failed: {exc}. Retrying in {wait:.1f}s…'\n"
                "                    )\n"
                "                    time.sleep(wait)\n"
                "                    wait *= backoff\n"
                "            raise ServiceError(\n"
                "                f'{func.__name__} failed after {max_retries} retries'\n"
                "            ) from last_exc\n"
                "        return wrapper\n"
                "    return decorator\n"
                "\n"
                "\n"
                "# Usage:\n"
                "# @retry(max_retries=3, delay=1.0)\n"
                "# def fetch_data(url):\n"
                "#     ...\n"
                "print('Error handling utilities defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-prod-pipeline",
            title="Data Pipeline",
            description="ETL pipeline template with extract, transform, and load functions.",
            category="Production",
            tags=["etl", "pipeline", "data", "production", "workflow"],
            difficulty="advanced",
            code=(
                "import pandas as pd\n"
                "import logging\n"
                "from datetime import datetime\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\n"
                "def extract(source: str) -> pd.DataFrame:\n"
                '    """Extract data from source."""\n'
                "    logger.info(f'Extracting from {source}')\n"
                "    df = pd.read_csv(source)\n"
                "    logger.info(f'Extracted {len(df)} rows')\n"
                "    return df\n"
                "\n"
                "\n"
                "def transform(df: pd.DataFrame) -> pd.DataFrame:\n"
                '    """Apply transformations: clean, enrich, validate."""\n'
                "    logger.info('Transforming data…')\n"
                "    # Drop duplicates\n"
                "    df = df.drop_duplicates().reset_index(drop=True)\n"
                "    # Handle missing values\n"
                "    for col in df.select_dtypes(include='number').columns:\n"
                "        df[col] = df[col].fillna(df[col].median())\n"
                "    # Add metadata\n"
                "    df['_processed_at'] = datetime.now().isoformat()\n"
                "    logger.info(f'Transformed → {len(df)} rows, {len(df.columns)} cols')\n"
                "    return df\n"
                "\n"
                "\n"
                "def load(df: pd.DataFrame, dest: str) -> None:\n"
                '    """Load data to destination."""\n'
                "    logger.info(f'Loading {len(df)} rows to {dest}')\n"
                "    df.to_csv(dest, index=False)\n"
                "    logger.info('Load complete ✓')\n"
                "\n"
                "\n"
                "def run_pipeline(source: str, dest: str) -> None:\n"
                '    """Run the full ETL pipeline."""\n'
                "    start = datetime.now()\n"
                "    raw = extract(source)\n"
                "    clean = transform(raw)\n"
                "    load(clean, dest)\n"
                "    elapsed = (datetime.now() - start).total_seconds()\n"
                "    logger.info(f'Pipeline finished in {elapsed:.1f}s')\n"
                "\n"
                "\n"
                "# run_pipeline('raw_data.csv', 'processed_data.csv')\n"
                "print('ETL pipeline defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-prod-model-serving",
            title="Model Serving",
            description="FastAPI model serving endpoint template for ML inference.",
            category="Production",
            tags=["fastapi", "serving", "api", "inference", "production"],
            difficulty="advanced",
            code=(
                "import joblib\n"
                "import numpy as np\n"
                "from fastapi import FastAPI, HTTPException\n"
                "from pydantic import BaseModel\n"
                "\n"
                "app = FastAPI(title='ML Model API', version='1.0.0')\n"
                "\n"
                "# Load model at startup\n"
                "model = joblib.load('model.pkl')\n"
                "\n"
                "\n"
                "class PredictRequest(BaseModel):\n"
                "    features: list[float]\n"
                "\n"
                "\n"
                "class PredictResponse(BaseModel):\n"
                "    prediction: float\n"
                "    confidence: float | None = None\n"
                "\n"
                "\n"
                "@app.get('/health')\n"
                "def health():\n"
                "    return {'status': 'healthy'}\n"
                "\n"
                "\n"
                "@app.post('/predict', response_model=PredictResponse)\n"
                "def predict(req: PredictRequest):\n"
                "    try:\n"
                "        X = np.array(req.features).reshape(1, -1)\n"
                "        pred = float(model.predict(X)[0])\n"
                "        conf = None\n"
                "        if hasattr(model, 'predict_proba'):\n"
                "            conf = float(model.predict_proba(X).max())\n"
                "        return PredictResponse(prediction=pred, confidence=conf)\n"
                "    except Exception as e:\n"
                "        raise HTTPException(status_code=400, detail=str(e))\n"
                "\n"
                "\n"
                "# Run: uvicorn app:app --host 0.0.0.0 --port 8000\n"
                "print('FastAPI model serving app defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-prod-docker",
            title="Docker Inference",
            description="Dockerfile for ML model inference with Python.",
            category="Production",
            tags=["docker", "container", "deployment", "inference"],
            difficulty="advanced",
            code=(
                "# === Dockerfile for ML Inference ===\n"
                "# Save this as 'Dockerfile'\n"
                "\n"
                "DOCKERFILE = '''\n"
                "FROM python:3.11-slim\n"
                "\n"
                "WORKDIR /app\n"
                "\n"
                "# Install dependencies\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "\n"
                "# Copy application code and model\n"
                "COPY app.py .\n"
                "COPY model.pkl .\n"
                "\n"
                "# Expose port\n"
                "EXPOSE 8000\n"
                "\n"
                "# Health check\n"
                "HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\\\\n"
                "    CMD curl -f http://localhost:8000/health || exit 1\n"
                "\n"
                "# Run the server\n"
                'CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]\n'
                "'''.strip()\n"
                "\n"
                "from pathlib import Path\n"
                "Path('Dockerfile').write_text(DOCKERFILE)\n"
                "print('Dockerfile created ✓')\n"
                "print('Build:  docker build -t ml-inference .')\n"
                "print('Run:    docker run -p 8000:8000 ml-inference')"
            ),
        ),
        # ── Deep Learning ────────────────────────────────────────────
        Snippet(
            id="builtin-dl-pytorch-train",
            title="PyTorch Training Loop",
            description="Complete PyTorch training and evaluation loop with loss, optimizer, and scheduler.",
            category="Deep Learning",
            tags=["pytorch", "training", "deep-learning", "gpu", "neural-network"],
            difficulty="advanced",
            code=(
                "import torch\n"
                "import torch.nn as nn\n"
                "from torch.utils.data import DataLoader\n"
                "\n"
                "# Setup\n"
                "device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')\n"
                "model = model.to(device)  # your nn.Module\n"
                "\n"
                "criterion = nn.CrossEntropyLoss()\n"
                "optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)\n"
                "scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)\n"
                "\n"
                "EPOCHS = 50\n"
                "\n"
                "for epoch in range(1, EPOCHS + 1):\n"
                "    # ── Train ──\n"
                "    model.train()\n"
                "    train_loss, correct, total = 0.0, 0, 0\n"
                "    for X_batch, y_batch in train_loader:\n"
                "        X_batch, y_batch = X_batch.to(device), y_batch.to(device)\n"
                "        optimizer.zero_grad()\n"
                "        outputs = model(X_batch)\n"
                "        loss = criterion(outputs, y_batch)\n"
                "        loss.backward()\n"
                "        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)\n"
                "        optimizer.step()\n"
                "        train_loss += loss.item() * X_batch.size(0)\n"
                "        correct += (outputs.argmax(1) == y_batch).sum().item()\n"
                "        total += X_batch.size(0)\n"
                "    scheduler.step()\n"
                "\n"
                "    # ── Eval ──\n"
                "    model.eval()\n"
                "    val_loss, val_correct, val_total = 0.0, 0, 0\n"
                "    with torch.no_grad():\n"
                "        for X_batch, y_batch in val_loader:\n"
                "            X_batch, y_batch = X_batch.to(device), y_batch.to(device)\n"
                "            outputs = model(X_batch)\n"
                "            val_loss += criterion(outputs, y_batch).item() * X_batch.size(0)\n"
                "            val_correct += (outputs.argmax(1) == y_batch).sum().item()\n"
                "            val_total += X_batch.size(0)\n"
                "\n"
                "    print(\n"
                "        f'Epoch {epoch:3d}/{EPOCHS} | '\n"
                "        f'Train Loss: {train_loss/total:.4f} Acc: {correct/total:.4f} | '\n"
                "        f'Val Loss: {val_loss/val_total:.4f} Acc: {val_correct/val_total:.4f}'\n"
                "    )"
            ),
        ),
        Snippet(
            id="builtin-dl-keras-layer",
            title="Keras Custom Layer",
            description="Custom Keras layer template with build and call methods.",
            category="Deep Learning",
            tags=["keras", "tensorflow", "layer", "custom", "deep-learning"],
            difficulty="advanced",
            code=(
                "import tensorflow as tf\n"
                "from tensorflow import keras\n"
                "\n"
                "\n"
                "class AttentionLayer(keras.layers.Layer):\n"
                '    """Simple single-head attention layer."""\n'
                "\n"
                "    def __init__(self, units: int = 64, **kwargs):\n"
                "        super().__init__(**kwargs)\n"
                "        self.units = units\n"
                "\n"
                "    def build(self, input_shape):\n"
                "        self.W_query = self.add_weight(\n"
                "            'W_query', shape=(input_shape[-1], self.units),\n"
                "            initializer='glorot_uniform', trainable=True,\n"
                "        )\n"
                "        self.W_key = self.add_weight(\n"
                "            'W_key', shape=(input_shape[-1], self.units),\n"
                "            initializer='glorot_uniform', trainable=True,\n"
                "        )\n"
                "        self.W_value = self.add_weight(\n"
                "            'W_value', shape=(input_shape[-1], self.units),\n"
                "            initializer='glorot_uniform', trainable=True,\n"
                "        )\n"
                "        super().build(input_shape)\n"
                "\n"
                "    def call(self, inputs):\n"
                "        Q = tf.matmul(inputs, self.W_query)\n"
                "        K = tf.matmul(inputs, self.W_key)\n"
                "        V = tf.matmul(inputs, self.W_value)\n"
                "        scale = tf.math.sqrt(tf.cast(self.units, tf.float32))\n"
                "        scores = tf.matmul(Q, K, transpose_b=True) / scale\n"
                "        weights = tf.nn.softmax(scores, axis=-1)\n"
                "        return tf.matmul(weights, V)\n"
                "\n"
                "    def get_config(self):\n"
                "        config = super().get_config()\n"
                "        config.update({'units': self.units})\n"
                "        return config\n"
                "\n"
                "\n"
                "# Usage:\n"
                "# layer = AttentionLayer(units=64)\n"
                "# output = layer(input_tensor)  # shape: (batch, seq_len, 64)\n"
                "print('AttentionLayer defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-dl-transfer",
            title="Transfer Learning",
            description="Fine-tune a pretrained model (ResNet/BERT pattern) with frozen backbone.",
            category="Deep Learning",
            tags=["transfer-learning", "pretrained", "fine-tune", "pytorch", "resnet"],
            difficulty="advanced",
            code=(
                "import torch\n"
                "import torch.nn as nn\n"
                "from torchvision import models\n"
                "\n"
                "NUM_CLASSES = 10\n"
                "\n"
                "# Load pretrained backbone\n"
                "backbone = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)\n"
                "\n"
                "# Freeze all backbone layers\n"
                "for param in backbone.parameters():\n"
                "    param.requires_grad = False\n"
                "\n"
                "# Replace classifier head\n"
                "in_features = backbone.fc.in_features\n"
                "backbone.fc = nn.Sequential(\n"
                "    nn.Dropout(0.3),\n"
                "    nn.Linear(in_features, 256),\n"
                "    nn.ReLU(),\n"
                "    nn.Dropout(0.2),\n"
                "    nn.Linear(256, NUM_CLASSES),\n"
                ")\n"
                "\n"
                "# Only train the new head\n"
                "optimizer = torch.optim.Adam(backbone.fc.parameters(), lr=1e-3)\n"
                "\n"
                "# Optional: unfreeze last N layers for fine-tuning\n"
                "# for param in backbone.layer4.parameters():\n"
                "#     param.requires_grad = True\n"
                "\n"
                "trainable = sum(p.numel() for p in backbone.parameters() if p.requires_grad)\n"
                "total = sum(p.numel() for p in backbone.parameters())\n"
                "print(f'Trainable: {trainable:,} / {total:,} params '\n"
                "      f'({trainable / total * 100:.1f}%)')"
            ),
        ),
        Snippet(
            id="builtin-dl-gpu-check",
            title="GPU Memory Check",
            description="Check CUDA/MPS availability and GPU memory usage.",
            category="Deep Learning",
            tags=["gpu", "cuda", "mps", "memory", "device"],
            difficulty="beginner",
            code=(
                "import torch\n"
                "\n"
                "print('=== Device Information ===')\n"
                "if torch.cuda.is_available():\n"
                "    device = torch.device('cuda')\n"
                "    print(f'CUDA available: ✓')\n"
                "    print(f'GPU:           {torch.cuda.get_device_name(0)}')\n"
                "    print(f'GPU count:     {torch.cuda.device_count()}')\n"
                "    mem_total = torch.cuda.get_device_properties(0).total_mem / 1024**3\n"
                "    mem_alloc = torch.cuda.memory_allocated(0) / 1024**3\n"
                "    mem_cached = torch.cuda.memory_reserved(0) / 1024**3\n"
                "    print(f'Total memory:  {mem_total:.1f} GB')\n"
                "    print(f'Allocated:     {mem_alloc:.1f} GB')\n"
                "    print(f'Cached:        {mem_cached:.1f} GB')\n"
                "    print(f'Free:          {mem_total - mem_alloc:.1f} GB')\n"
                "elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():\n"
                "    device = torch.device('mps')\n"
                "    print('MPS (Apple Silicon) available: ✓')\n"
                "else:\n"
                "    device = torch.device('cpu')\n"
                "    print('No GPU found — using CPU')\n"
                "\n"
                "print(f'\\nActive device: {device}')\n"
                "print(f'PyTorch version: {torch.__version__}')"
            ),
        ),
        Snippet(
            id="builtin-dl-mixed-precision",
            title="Mixed Precision Training",
            description="Enable mixed precision (FP16/BF16) training for faster performance.",
            category="Deep Learning",
            tags=["mixed-precision", "fp16", "amp", "performance", "pytorch"],
            difficulty="advanced",
            code=(
                "import torch\n"
                "from torch.cuda.amp import autocast, GradScaler\n"
                "\n"
                "device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')\n"
                "model = model.to(device)\n"
                "optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)\n"
                "scaler = GradScaler()\n"
                "\n"
                "EPOCHS = 10\n"
                "\n"
                "for epoch in range(1, EPOCHS + 1):\n"
                "    model.train()\n"
                "    epoch_loss = 0.0\n"
                "    for X_batch, y_batch in train_loader:\n"
                "        X_batch = X_batch.to(device)\n"
                "        y_batch = y_batch.to(device)\n"
                "\n"
                "        optimizer.zero_grad()\n"
                "\n"
                "        # Forward pass with mixed precision\n"
                "        with autocast():\n"
                "            outputs = model(X_batch)\n"
                "            loss = criterion(outputs, y_batch)\n"
                "\n"
                "        # Backward pass with scaled gradients\n"
                "        scaler.scale(loss).backward()\n"
                "        scaler.unscale_(optimizer)\n"
                "        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)\n"
                "        scaler.step(optimizer)\n"
                "        scaler.update()\n"
                "\n"
                "        epoch_loss += loss.item()\n"
                "\n"
                "    avg_loss = epoch_loss / len(train_loader)\n"
                "    print(f'Epoch {epoch}/{EPOCHS} | Loss: {avg_loss:.4f}')\n"
                "\n"
                "print('Mixed precision training complete ✓')"
            ),
        ),
        # ── NLP ──────────────────────────────────────────────────────
        Snippet(
            id="builtin-nlp-preprocess",
            title="Text Preprocessing",
            description="Clean text: lowercase, remove punctuation, tokenize, and remove stop words.",
            category="NLP",
            tags=["nlp", "text", "preprocessing", "tokenize", "clean"],
            difficulty="beginner",
            code=(
                "import re\n"
                "import string\n"
                "\n"
                "\n"
                "def preprocess_text(text: str) -> str:\n"
                '    """Clean and normalize text for NLP."""\n'
                "    # Lowercase\n"
                "    text = text.lower()\n"
                "    # Remove URLs\n"
                "    text = re.sub(r'https?://\\S+|www\\.\\S+', '', text)\n"
                "    # Remove HTML tags\n"
                "    text = re.sub(r'<[^>]+>', '', text)\n"
                "    # Remove punctuation\n"
                "    text = text.translate(str.maketrans('', '', string.punctuation))\n"
                "    # Remove extra whitespace\n"
                "    text = re.sub(r'\\s+', ' ', text).strip()\n"
                "    return text\n"
                "\n"
                "\n"
                "# Example usage\n"
                "raw = 'Hello, World!!! Visit https://example.com for <b>more</b> info.'\n"
                "clean = preprocess_text(raw)\n"
                "print(f'Raw:   {raw}')\n"
                "print(f'Clean: {clean}')\n"
                "\n"
                "# Apply to DataFrame column\n"
                "# df['clean_text'] = df['text'].apply(preprocess_text)\n"
                "# print(df[['text', 'clean_text']].head())"
            ),
        ),
        Snippet(
            id="builtin-nlp-tfidf",
            title="TF-IDF Vectorization",
            description="Scikit-learn TF-IDF vectorization with n-grams for text features.",
            category="NLP",
            tags=["nlp", "tfidf", "sklearn", "vectorize", "features"],
            difficulty="intermediate",
            code=(
                "from sklearn.feature_extraction.text import TfidfVectorizer\n"
                "import pandas as pd\n"
                "\n"
                "corpus = [\n"
                "    'Machine learning is great',\n"
                "    'Deep learning is a subset of machine learning',\n"
                "    'Natural language processing uses machine learning',\n"
                "    'Neural networks power deep learning',\n"
                "]\n"
                "\n"
                "# Fit TF-IDF with unigrams and bigrams\n"
                "vectorizer = TfidfVectorizer(\n"
                "    max_features=1000,\n"
                "    ngram_range=(1, 2),     # unigrams + bigrams\n"
                "    min_df=1,               # min document frequency\n"
                "    max_df=0.95,            # max document frequency\n"
                "    stop_words='english',\n"
                "    sublinear_tf=True,\n"
                ")\n"
                "\n"
                "tfidf_matrix = vectorizer.fit_transform(corpus)\n"
                "print(f'Matrix shape: {tfidf_matrix.shape}')\n"
                "print(f'Vocabulary size: {len(vectorizer.vocabulary_)}')\n"
                "\n"
                "# Top features per document\n"
                "feature_names = vectorizer.get_feature_names_out()\n"
                "df_tfidf = pd.DataFrame(\n"
                "    tfidf_matrix.toarray(),\n"
                "    columns=feature_names,\n"
                ")\n"
                "print(df_tfidf.round(3))"
            ),
        ),
        Snippet(
            id="builtin-nlp-sentiment",
            title="Sentiment Analysis",
            description="Quick sentiment scoring with VADER from NLTK.",
            category="NLP",
            tags=["nlp", "sentiment", "vader", "nltk", "opinion"],
            difficulty="beginner",
            code=(
                "import nltk\n"
                "nltk.download('vader_lexicon', quiet=True)\n"
                "\n"
                "from nltk.sentiment.vader import SentimentIntensityAnalyzer\n"
                "import pandas as pd\n"
                "\n"
                "sia = SentimentIntensityAnalyzer()\n"
                "\n"
                "texts = [\n"
                "    'This product is amazing! Best purchase ever.',\n"
                "    'Terrible quality. Broke after one day.',\n"
                "    'It is okay, nothing special.',\n"
                "    'Absolutely love it, highly recommend!',\n"
                "    'Not worth the money, very disappointing.',\n"
                "]\n"
                "\n"
                "results = []\n"
                "for text in texts:\n"
                "    scores = sia.polarity_scores(text)\n"
                "    results.append({\n"
                "        'text': text[:50],\n"
                "        'positive': scores['pos'],\n"
                "        'negative': scores['neg'],\n"
                "        'neutral': scores['neu'],\n"
                "        'compound': scores['compound'],\n"
                "        'label': 'positive' if scores['compound'] > 0.05\n"
                "                 else 'negative' if scores['compound'] < -0.05\n"
                "                 else 'neutral',\n"
                "    })\n"
                "\n"
                "df_sent = pd.DataFrame(results)\n"
                "print(df_sent.to_string(index=False))"
            ),
        ),
        Snippet(
            id="builtin-nlp-embeddings",
            title="Word Embeddings",
            description="Load and use pre-trained word2vec or GloVe word embeddings.",
            category="NLP",
            tags=["nlp", "embeddings", "word2vec", "gensim", "vectors"],
            difficulty="intermediate",
            code=(
                "import numpy as np\n"
                "from gensim.models import KeyedVectors\n"
                "\n"
                "# Option 1: Load pre-trained Word2Vec (Google News)\n"
                "# model = KeyedVectors.load_word2vec_format(\n"
                "#     'GoogleNews-vectors-negative300.bin', binary=True\n"
                "# )\n"
                "\n"
                "# Option 2: Load GloVe (convert to word2vec format first)\n"
                "# from gensim.scripts.glove2word2vec import glove2word2vec\n"
                "# glove2word2vec('glove.6B.100d.txt', 'glove.6B.100d.w2v.txt')\n"
                "# model = KeyedVectors.load_word2vec_format('glove.6B.100d.w2v.txt')\n"
                "\n"
                "# Option 3: Train on your own corpus\n"
                "from gensim.models import Word2Vec\n"
                "sentences = [\n"
                "    ['machine', 'learning', 'is', 'great'],\n"
                "    ['deep', 'learning', 'neural', 'networks'],\n"
                "    ['natural', 'language', 'processing'],\n"
                "]\n"
                "model = Word2Vec(sentences, vector_size=100, window=5, min_count=1, epochs=100)\n"
                "wv = model.wv\n"
                "\n"
                "# Find similar words\n"
                "print('Most similar to \"learning\":')\n"
                "for word, score in wv.most_similar('learning', topn=5):\n"
                "    print(f'  {word:20s} {score:.4f}')\n"
                "\n"
                "# Get document vector (mean of word vectors)\n"
                "def doc_vector(words, wv):\n"
                "    vecs = [wv[w] for w in words if w in wv]\n"
                "    return np.mean(vecs, axis=0) if vecs else np.zeros(wv.vector_size)\n"
                "\n"
                "vec = doc_vector(['machine', 'learning'], wv)\n"
                "print(f'\\nDocument vector shape: {vec.shape}')"
            ),
        ),
        Snippet(
            id="builtin-nlp-ner",
            title="Named Entity Recognition",
            description="Extract named entities (persons, orgs, locations) with spaCy.",
            category="NLP",
            tags=["nlp", "ner", "spacy", "entities", "extraction"],
            difficulty="intermediate",
            code=(
                "import spacy\n"
                "import pandas as pd\n"
                "\n"
                "# Load spaCy model (run: python -m spacy download en_core_web_sm)\n"
                "nlp = spacy.load('en_core_web_sm')\n"
                "\n"
                "text = (\n"
                "    'Apple Inc. was founded by Steve Jobs in Cupertino, California. '\n"
                "    'The company reported $394 billion in revenue in 2022. '\n"
                "    'Tim Cook has been CEO since August 2011.'\n"
                ")\n"
                "\n"
                "doc = nlp(text)\n"
                "\n"
                "# Extract entities\n"
                "entities = []\n"
                "for ent in doc.ents:\n"
                "    entities.append({\n"
                "        'text': ent.text,\n"
                "        'label': ent.label_,\n"
                "        'description': spacy.explain(ent.label_),\n"
                "        'start': ent.start_char,\n"
                "        'end': ent.end_char,\n"
                "    })\n"
                "\n"
                "df_ents = pd.DataFrame(entities)\n"
                "print(df_ents.to_string(index=False))\n"
                "\n"
                "# Summary by type\n"
                "print('\\n=== Entity Summary ===')\n"
                "print(df_ents['label'].value_counts())"
            ),
        ),
        # ── Time Series ──────────────────────────────────────────────
        Snippet(
            id="builtin-ts-decompose",
            title="Time Series Decomposition",
            description="Decompose a time series into trend, seasonal, and residual components.",
            category="Time Series",
            tags=["time-series", "decomposition", "statsmodels", "trend", "seasonal"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import matplotlib.pyplot as plt\n"
                "from statsmodels.tsa.seasonal import seasonal_decompose\n"
                "\n"
                "# Prepare data (ensure datetime index)\n"
                "# df['date'] = pd.to_datetime(df['date'])\n"
                "# df = df.set_index('date').sort_index()\n"
                "# series = df['value']\n"
                "\n"
                "# Example: generate sample data\n"
                "import numpy as np\n"
                "dates = pd.date_range('2020-01-01', periods=365, freq='D')\n"
                "trend = np.linspace(10, 50, 365)\n"
                "seasonal = 10 * np.sin(2 * np.pi * np.arange(365) / 365)\n"
                "noise = np.random.normal(0, 2, 365)\n"
                "series = pd.Series(trend + seasonal + noise, index=dates)\n"
                "\n"
                "# Decompose\n"
                "result = seasonal_decompose(series, model='additive', period=30)\n"
                "\n"
                "fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)\n"
                "result.observed.plot(ax=axes[0], title='Observed')\n"
                "result.trend.plot(ax=axes[1], title='Trend')\n"
                "result.seasonal.plot(ax=axes[2], title='Seasonal')\n"
                "result.resid.plot(ax=axes[3], title='Residual')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-ts-rolling",
            title="Rolling Statistics",
            description="Compute moving average, rolling std, and Bollinger Bands.",
            category="Time Series",
            tags=["time-series", "rolling", "moving-average", "bollinger", "statistics"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import matplotlib.pyplot as plt\n"
                "\n"
                "# series = df['value']  # your time series column\n"
                "\n"
                "# Example data\n"
                "import numpy as np\n"
                "np.random.seed(42)\n"
                "dates = pd.date_range('2023-01-01', periods=200, freq='D')\n"
                "series = pd.Series(\n"
                "    np.cumsum(np.random.randn(200)) + 100,\n"
                "    index=dates, name='value',\n"
                ")\n"
                "\n"
                "window = 20\n"
                "\n"
                "# Rolling statistics\n"
                "rolling_mean = series.rolling(window=window).mean()\n"
                "rolling_std = series.rolling(window=window).std()\n"
                "\n"
                "# Bollinger Bands\n"
                "upper_band = rolling_mean + 2 * rolling_std\n"
                "lower_band = rolling_mean - 2 * rolling_std\n"
                "\n"
                "# Plot\n"
                "plt.figure(figsize=(14, 6))\n"
                "plt.plot(series, label='Original', alpha=0.6)\n"
                "plt.plot(rolling_mean, label=f'{window}-day MA', color='red', linewidth=2)\n"
                "plt.fill_between(series.index, lower_band, upper_band,\n"
                "                 alpha=0.15, color='blue', label='Bollinger Bands')\n"
                "plt.title('Rolling Statistics & Bollinger Bands')\n"
                "plt.legend()\n"
                "plt.grid(alpha=0.3)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-ts-stationarity",
            title="Stationarity Test",
            description="Augmented Dickey-Fuller test for stationarity with interpretation.",
            category="Time Series",
            tags=["time-series", "stationarity", "adf", "statsmodels", "test"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "from statsmodels.tsa.stattools import adfuller\n"
                "\n"
                "\n"
                "def test_stationarity(series: pd.Series, name: str = 'Series') -> dict:\n"
                '    """Run ADF test and interpret results."""\n'
                "    result = adfuller(series.dropna(), autolag='AIC')\n"
                "    adf_stat, p_value, used_lag, n_obs, critical_values, icbest = result\n"
                "\n"
                "    print(f'=== Stationarity Test: {name} ===')\n"
                "    print(f'ADF Statistic:   {adf_stat:.6f}')\n"
                "    print(f'p-value:         {p_value:.6f}')\n"
                "    print(f'Lags used:       {used_lag}')\n"
                "    print(f'Observations:    {n_obs}')\n"
                "    print(f'Critical values:')\n"
                "    for key, val in critical_values.items():\n"
                "        marker = ' ← reject' if adf_stat < val else ''\n"
                "        print(f'  {key}: {val:.4f}{marker}')\n"
                "\n"
                "    is_stationary = p_value < 0.05\n"
                '    print(f\'\\nConclusion: {"✓ STATIONARY" if is_stationary else "✗ NON-STATIONARY"} \'\n'
                "          f'(p={p_value:.4f})')\n"
                "    return {'adf': adf_stat, 'p_value': p_value, 'stationary': is_stationary}\n"
                "\n"
                "\n"
                "# Usage:\n"
                "# result = test_stationarity(df['value'], name='Revenue')\n"
                "# If non-stationary, try differencing:\n"
                "# result_diff = test_stationarity(df['value'].diff().dropna(), name='Revenue (diff)')\n"
                "\n"
                "# Demo with random walk (non-stationary)\n"
                "import numpy as np\n"
                "demo = pd.Series(np.cumsum(np.random.randn(200)))\n"
                "test_stationarity(demo, 'Random Walk')"
            ),
        ),
        Snippet(
            id="builtin-ts-arima",
            title="ARIMA Forecast",
            description="Fit an ARIMA model and generate forecasts with confidence intervals.",
            category="Time Series",
            tags=["time-series", "arima", "forecast", "statsmodels", "prediction"],
            difficulty="advanced",
            code=(
                "import pandas as pd\n"
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "from statsmodels.tsa.arima.model import ARIMA\n"
                "\n"
                "# Example data\n"
                "np.random.seed(42)\n"
                "dates = pd.date_range('2020-01-01', periods=200, freq='M')\n"
                "trend = np.linspace(50, 150, 200)\n"
                "noise = np.random.normal(0, 5, 200)\n"
                "series = pd.Series(trend + noise, index=dates)\n"
                "\n"
                "# Split train / test\n"
                "train = series[:160]\n"
                "test = series[160:]\n"
                "\n"
                "# Fit ARIMA(p,d,q)\n"
                "model = ARIMA(train, order=(2, 1, 2))\n"
                "fitted = model.fit()\n"
                "print(fitted.summary())\n"
                "\n"
                "# Forecast\n"
                "forecast = fitted.get_forecast(steps=len(test))\n"
                "pred_mean = forecast.predicted_mean\n"
                "pred_ci = forecast.conf_int(alpha=0.05)\n"
                "\n"
                "# Plot\n"
                "plt.figure(figsize=(14, 6))\n"
                "plt.plot(train, label='Train')\n"
                "plt.plot(test, label='Test', color='gray', alpha=0.7)\n"
                "plt.plot(pred_mean, label='Forecast', color='red')\n"
                "plt.fill_between(\n"
                "    pred_ci.index, pred_ci.iloc[:, 0], pred_ci.iloc[:, 1],\n"
                "    alpha=0.2, color='red', label='95% CI',\n"
                ")\n"
                "plt.title('ARIMA Forecast')\n"
                "plt.legend()\n"
                "plt.grid(alpha=0.3)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
        ),
        Snippet(
            id="builtin-ts-prophet",
            title="Prophet Forecast",
            description="Facebook Prophet quick start for time series forecasting.",
            category="Time Series",
            tags=["time-series", "prophet", "forecast", "facebook", "prediction"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import numpy as np\n"
                "from prophet import Prophet\n"
                "\n"
                "# Prophet requires columns: 'ds' (datetime) and 'y' (value)\n"
                "# df_prophet = df.rename(columns={'date': 'ds', 'value': 'y'})\n"
                "\n"
                "# Example data\n"
                "np.random.seed(42)\n"
                "dates = pd.date_range('2020-01-01', periods=365, freq='D')\n"
                "trend = np.linspace(10, 50, 365)\n"
                "seasonal = 8 * np.sin(2 * np.pi * np.arange(365) / 365)\n"
                "df_prophet = pd.DataFrame({\n"
                "    'ds': dates,\n"
                "    'y': trend + seasonal + np.random.normal(0, 2, 365),\n"
                "})\n"
                "\n"
                "# Fit model\n"
                "model = Prophet(\n"
                "    yearly_seasonality=True,\n"
                "    weekly_seasonality=False,\n"
                "    daily_seasonality=False,\n"
                "    changepoint_prior_scale=0.05,\n"
                ")\n"
                "model.fit(df_prophet)\n"
                "\n"
                "# Create future dates and forecast\n"
                "future = model.make_future_dataframe(periods=90)\n"
                "forecast = model.predict(future)\n"
                "\n"
                "# Plot\n"
                "fig = model.plot(forecast)\n"
                "fig.set_size_inches(14, 6)\n"
                "\n"
                "# Components\n"
                "fig2 = model.plot_components(forecast)\n"
                "\n"
                "print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(10))"
            ),
        ),
        # ── Testing ──────────────────────────────────────────────────
        Snippet(
            id="builtin-test-unit",
            title="Unit Test Template",
            description="pytest test class with setup, teardown, and parametrized tests.",
            category="Testing",
            tags=["testing", "pytest", "unit-test", "setup", "teardown"],
            difficulty="intermediate",
            code=(
                "import pytest\n"
                "\n"
                "\n"
                "class TestMyFeature:\n"
                '    """Tests for MyFeature."""\n'
                "\n"
                "    @pytest.fixture(autouse=True)\n"
                "    def setup(self):\n"
                '        """Set up test fixtures."""\n'
                "        self.data = [1, 2, 3, 4, 5]\n"
                "        self.expected_sum = 15\n"
                "        yield\n"
                "        # Teardown runs after each test\n"
                "        self.data = None\n"
                "\n"
                "    def test_basic_operation(self):\n"
                "        assert sum(self.data) == self.expected_sum\n"
                "\n"
                "    def test_length(self):\n"
                "        assert len(self.data) == 5\n"
                "\n"
                "    @pytest.mark.parametrize('value,expected', [\n"
                "        (2, True),\n"
                "        (6, False),\n"
                "        (5, True),\n"
                "    ])\n"
                "    def test_contains(self, value, expected):\n"
                "        assert (value in self.data) == expected\n"
                "\n"
                "    def test_raises_on_invalid_index(self):\n"
                "        with pytest.raises(IndexError):\n"
                "            _ = self.data[100]\n"
                "\n"
                "\n"
                "# Run: pytest -v test_my_feature.py\n"
                "print('Test class defined ✓')"
            ),
        ),
        Snippet(
            id="builtin-test-data-validation",
            title="Data Validation Assert",
            description="Comprehensive data quality assertions for DataFrames.",
            category="Testing",
            tags=["testing", "data", "validation", "quality", "assert"],
            difficulty="intermediate",
            code=(
                "import pandas as pd\n"
                "import numpy as np\n"
                "\n"
                "\n"
                "def validate_dataframe(df: pd.DataFrame, config: dict) -> list[str]:\n"
                '    """Validate a DataFrame against a config spec. Returns list of errors."""\n'
                "    errors = []\n"
                "\n"
                "    # Check required columns\n"
                "    for col in config.get('required_columns', []):\n"
                "        if col not in df.columns:\n"
                "            errors.append(f'Missing required column: {col}')\n"
                "\n"
                "    # Check no nulls in specified columns\n"
                "    for col in config.get('no_nulls', []):\n"
                "        if col in df.columns and df[col].isnull().any():\n"
                "            n = df[col].isnull().sum()\n"
                "            errors.append(f'{col}: has {n} null values')\n"
                "\n"
                "    # Check value ranges\n"
                "    for col, (lo, hi) in config.get('ranges', {}).items():\n"
                "        if col in df.columns:\n"
                "            oob = ((df[col] < lo) | (df[col] > hi)).sum()\n"
                "            if oob > 0:\n"
                "                errors.append(f'{col}: {oob} values outside [{lo}, {hi}]')\n"
                "\n"
                "    # Check uniqueness\n"
                "    for col in config.get('unique', []):\n"
                "        if col in df.columns:\n"
                "            dupes = df[col].duplicated().sum()\n"
                "            if dupes > 0:\n"
                "                errors.append(f'{col}: {dupes} duplicate values')\n"
                "\n"
                "    # Row count\n"
                "    min_rows = config.get('min_rows', 0)\n"
                "    if len(df) < min_rows:\n"
                "        errors.append(f'Expected >= {min_rows} rows, got {len(df)}')\n"
                "\n"
                "    # Print results\n"
                "    if errors:\n"
                "        print(f'✗ Validation FAILED ({len(errors)} issues):')\n"
                "        for e in errors:\n"
                "            print(f'  - {e}')\n"
                "    else:\n"
                "        print('✓ All validations passed')\n"
                "\n"
                "    return errors\n"
                "\n"
                "\n"
                "# Example\n"
                "df = pd.DataFrame({'id': [1, 2, 3], 'value': [10, 20, 30], 'name': ['a', 'b', 'c']})\n"
                "errors = validate_dataframe(df, {\n"
                "    'required_columns': ['id', 'value', 'name'],\n"
                "    'no_nulls': ['id', 'name'],\n"
                "    'ranges': {'value': (0, 100)},\n"
                "    'unique': ['id'],\n"
                "    'min_rows': 1,\n"
                "})"
            ),
        ),
        Snippet(
            id="builtin-test-model-quality",
            title="Model Quality Check",
            description="Assert model metrics meet minimum quality thresholds.",
            category="Testing",
            tags=["testing", "model", "quality", "metrics", "threshold"],
            difficulty="intermediate",
            code=(
                "from sklearn.metrics import (\n"
                "    accuracy_score,\n"
                "    precision_score,\n"
                "    recall_score,\n"
                "    f1_score,\n"
                "    mean_squared_error,\n"
                "    r2_score,\n"
                ")\n"
                "import numpy as np\n"
                "\n"
                "\n"
                "def check_classification_quality(\n"
                "    y_true, y_pred, thresholds: dict | None = None\n"
                ") -> bool:\n"
                '    """Check classification metrics meet minimum thresholds."""\n'
                "    defaults = {'accuracy': 0.80, 'precision': 0.75, 'recall': 0.75, 'f1': 0.75}\n"
                "    thresholds = thresholds or defaults\n"
                "\n"
                "    metrics = {\n"
                "        'accuracy': accuracy_score(y_true, y_pred),\n"
                "        'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),\n"
                "        'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),\n"
                "        'f1': f1_score(y_true, y_pred, average='weighted', zero_division=0),\n"
                "    }\n"
                "\n"
                "    all_pass = True\n"
                "    print('=== Model Quality Check ===')\n"
                "    for name, value in metrics.items():\n"
                "        threshold = thresholds.get(name, 0)\n"
                "        passed = value >= threshold\n"
                "        status = '✓' if passed else '✗'\n"
                "        print(f'  {status} {name:12s}: {value:.4f} (threshold: {threshold:.2f})')\n"
                "        if not passed:\n"
                "            all_pass = False\n"
                "\n"
                '    print(f\'\\nOverall: {"PASS ✓" if all_pass else "FAIL ✗"}\')\n'
                "    return all_pass\n"
                "\n"
                "\n"
                "# Example:\n"
                "y_true = [0, 1, 1, 0, 1, 1, 0, 0, 1, 1]\n"
                "y_pred = [0, 1, 1, 0, 0, 1, 0, 1, 1, 1]\n"
                "check_classification_quality(y_true, y_pred)"
            ),
        ),
        Snippet(
            id="builtin-test-benchmark",
            title="Performance Benchmark",
            description="timeit-based performance comparison of multiple implementations.",
            category="Testing",
            tags=["testing", "benchmark", "performance", "timeit", "comparison"],
            difficulty="intermediate",
            code=(
                "import timeit\n"
                "import statistics\n"
                "\n"
                "\n"
                "def benchmark(funcs: dict, number: int = 1000, repeat: int = 5) -> None:\n"
                '    """Benchmark multiple functions and compare performance."""\n'
                "    results = {}\n"
                "    for name, func in funcs.items():\n"
                "        times = timeit.repeat(func, number=number, repeat=repeat)\n"
                "        per_call = [t / number * 1000 for t in times]  # ms per call\n"
                "        results[name] = {\n"
                "            'mean': statistics.mean(per_call),\n"
                "            'std': statistics.stdev(per_call) if len(per_call) > 1 else 0,\n"
                "            'min': min(per_call),\n"
                "            'max': max(per_call),\n"
                "        }\n"
                "\n"
                "    # Find fastest\n"
                "    fastest = min(results, key=lambda k: results[k]['mean'])\n"
                "\n"
                "    print(f'=== Benchmark ({number} calls × {repeat} repeats) ===')\n"
                "    for name, r in sorted(results.items(), key=lambda x: x[1]['mean']):\n"
                "        ratio = r['mean'] / results[fastest]['mean']\n"
                "        badge = ' 🏆' if name == fastest else ''\n"
                "        print(\n"
                '            f\'  {name:25s}: {r["mean"]:.4f}ms ± {r["std"]:.4f}ms \'\n'
                '            f\'(min={r["min"]:.4f}, max={r["max"]:.4f}) \'\n'
                "            f'x{ratio:.2f}{badge}'\n"
                "        )\n"
                "\n"
                "\n"
                "# Example: compare list comprehension vs map\n"
                "data = list(range(10000))\n"
                "benchmark({\n"
                "    'list_comprehension': lambda: [x ** 2 for x in data],\n"
                "    'map_function': lambda: list(map(lambda x: x ** 2, data)),\n"
                "    'numpy_vectorized': lambda: __import__('numpy').array(data) ** 2,\n"
                "})"
            ),
        ),
        # ── SQL & Databases ──────────────────────────────────────────
        Snippet(
            id="builtin-sql-sqlalchemy",
            title="SQLAlchemy Connection",
            description="Connect to PostgreSQL, MySQL, or SQLite with SQLAlchemy ORM.",
            category="SQL & Databases",
            tags=["sql", "sqlalchemy", "database", "postgres", "orm"],
            difficulty="intermediate",
            code=(
                "from sqlalchemy import create_engine, text, inspect\n"
                "\n"
                "# Connection strings:\n"
                "# PostgreSQL: 'postgresql://user:pass@host:5432/dbname'\n"
                "# MySQL:      'mysql+pymysql://user:pass@host:3306/dbname'\n"
                "# SQLite:     'sqlite:///my_database.db'\n"
                "\n"
                "DATABASE_URL = 'sqlite:///example.db'\n"
                "\n"
                "engine = create_engine(\n"
                "    DATABASE_URL,\n"
                "    echo=False,      # set True for SQL logging\n"
                "    pool_size=5,\n"
                "    max_overflow=10,\n"
                ")\n"
                "\n"
                "# Test connection\n"
                "with engine.connect() as conn:\n"
                "    result = conn.execute(text('SELECT 1'))\n"
                "    print(f'Connection OK: {result.scalar()}')\n"
                "\n"
                "# List tables\n"
                "inspector = inspect(engine)\n"
                "tables = inspector.get_table_names()\n"
                "print(f'Tables: {tables}')\n"
                "\n"
                "# Example query\n"
                "# with engine.connect() as conn:\n"
                "#     rows = conn.execute(text('SELECT * FROM users LIMIT 5'))\n"
                "#     for row in rows:\n"
                "#         print(row)\n"
                "\n"
                "print(f'Engine: {engine.url}')"
            ),
        ),
        Snippet(
            id="builtin-sql-pandas",
            title="Pandas SQL Query",
            description="Read SQL queries into DataFrames with parameterized queries.",
            category="SQL & Databases",
            tags=["sql", "pandas", "query", "database", "read_sql"],
            difficulty="beginner",
            code=(
                "import pandas as pd\n"
                "from sqlalchemy import create_engine, text\n"
                "\n"
                "engine = create_engine('sqlite:///example.db')\n"
                "\n"
                "# Simple query\n"
                "df = pd.read_sql('SELECT * FROM my_table LIMIT 1000', engine)\n"
                "print(f'Loaded {len(df)} rows')\n"
                "\n"
                "# Parameterized query (safe from SQL injection)\n"
                "query = text('''\n"
                "    SELECT id, name, created_at\n"
                "    FROM users\n"
                "    WHERE status = :status\n"
                "      AND created_at >= :start_date\n"
                "    ORDER BY created_at DESC\n"
                "    LIMIT :limit\n"
                "''')\n"
                "params = {\n"
                "    'status': 'active',\n"
                "    'start_date': '2024-01-01',\n"
                "    'limit': 500,\n"
                "}\n"
                "\n"
                "df = pd.read_sql(query, engine, params=params, parse_dates=['created_at'])\n"
                "print(f'Active users since 2024: {len(df)}')\n"
                "df.head()"
            ),
        ),
        Snippet(
            id="builtin-sql-duckdb",
            title="DuckDB Analytics",
            description="Fast in-memory analytics on CSV/Parquet files with DuckDB.",
            category="SQL & Databases",
            tags=["duckdb", "analytics", "sql", "parquet", "olap"],
            difficulty="intermediate",
            code=(
                "import duckdb\n"
                "import pandas as pd\n"
                "\n"
                "# DuckDB runs SQL directly on files — no loading step!\n"
                "con = duckdb.connect(':memory:')\n"
                "\n"
                "# Query CSV files directly\n"
                "# df = con.execute(\"SELECT * FROM 'data.csv' LIMIT 10\").fetchdf()\n"
                "\n"
                "# Query Parquet files (very fast)\n"
                "# df = con.execute(\"SELECT * FROM 'data.parquet' WHERE value > 100\").fetchdf()\n"
                "\n"
                "# Work with existing DataFrames (zero copy!)\n"
                "sample = pd.DataFrame({\n"
                "    'product': ['A', 'B', 'A', 'C', 'B', 'A', 'C'],\n"
                "    'revenue': [100, 200, 150, 300, 250, 175, 350],\n"
                "    'quarter': ['Q1', 'Q1', 'Q2', 'Q2', 'Q3', 'Q3', 'Q4'],\n"
                "})\n"
                "\n"
                "# Aggregate with SQL\n"
                "result = con.execute('''\n"
                "    SELECT\n"
                "        product,\n"
                "        COUNT(*) AS n_sales,\n"
                "        SUM(revenue) AS total_revenue,\n"
                "        ROUND(AVG(revenue), 2) AS avg_revenue\n"
                "    FROM sample\n"
                "    GROUP BY product\n"
                "    ORDER BY total_revenue DESC\n"
                "''').fetchdf()\n"
                "\n"
                "print(result)\n"
                "con.close()"
            ),
        ),
        Snippet(
            id="builtin-sql-migration",
            title="Database Migration",
            description="Alembic-style schema migration template for database versioning.",
            category="SQL & Databases",
            tags=["sql", "migration", "alembic", "schema", "database"],
            difficulty="advanced",
            code=(
                "from sqlalchemy import create_engine, text, Column, Integer, String, DateTime\n"
                "from sqlalchemy.orm import declarative_base\n"
                "from datetime import datetime\n"
                "\n"
                "Base = declarative_base()\n"
                "\n"
                "\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True, autoincrement=True)\n"
                "    email = Column(String(255), unique=True, nullable=False)\n"
                "    name = Column(String(255), nullable=False)\n"
                "    created_at = Column(DateTime, default=datetime.utcnow)\n"
                "\n"
                "\n"
                "# Create/migrate schema\n"
                "engine = create_engine('sqlite:///app.db', echo=True)\n"
                "Base.metadata.create_all(engine)\n"
                "\n"
                "# For production, use Alembic:\n"
                "# pip install alembic\n"
                "# alembic init migrations\n"
                "# alembic revision --autogenerate -m 'add users table'\n"
                "# alembic upgrade head\n"
                "\n"
                "print('Schema migration applied ✓')\n"
                "print('Tables:', list(Base.metadata.tables.keys()))"
            ),
        ),
        Snippet(
            id="builtin-sql-pool",
            title="Connection Pool",
            description="SQLAlchemy connection pool with health checks and pre-ping.",
            category="SQL & Databases",
            tags=["sql", "connection-pool", "sqlalchemy", "health", "performance"],
            difficulty="advanced",
            code=(
                "from sqlalchemy import create_engine, event, text, pool\n"
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "DATABASE_URL = 'sqlite:///app.db'\n"
                "\n"
                "engine = create_engine(\n"
                "    DATABASE_URL,\n"
                "    pool_size=10,             # max persistent connections\n"
                "    max_overflow=20,           # extra connections allowed\n"
                "    pool_timeout=30,           # seconds to wait for connection\n"
                "    pool_recycle=1800,         # recycle connections after 30 min\n"
                "    pool_pre_ping=True,        # test connections before use\n"
                "    echo_pool='debug',         # log pool events\n"
                ")\n"
                "\n"
                "\n"
                "@event.listens_for(engine, 'connect')\n"
                "def on_connect(dbapi_conn, connection_record):\n"
                "    logger.info('New database connection established')\n"
                "\n"
                "\n"
                "@event.listens_for(engine, 'checkout')\n"
                "def on_checkout(dbapi_conn, connection_record, connection_proxy):\n"
                "    logger.debug('Connection checked out from pool')\n"
                "\n"
                "\n"
                "def health_check() -> bool:\n"
                '    """Check database connection health."""\n'
                "    try:\n"
                "        with engine.connect() as conn:\n"
                "            conn.execute(text('SELECT 1'))\n"
                "        return True\n"
                "    except Exception as e:\n"
                "        logger.error(f'Health check failed: {e}')\n"
                "        return False\n"
                "\n"
                "\n"
                "# Pool status\n"
                "p = engine.pool\n"
                "print(f'Pool size:      {p.size()}')\n"
                "print(f'Checked out:    {p.checkedout()}')\n"
                "print(f'Overflow:       {p.overflow()}')\n"
                'print(f\'Health check:   {"✓" if health_check() else "✗"}\')'
            ),
        ),
    ]


# ── Snippet Library ─────────────────────────────────────────────────────


class SnippetLibrary:
    """Searchable library of built-in and custom code snippets.

    Built-in snippets are loaded on init. Users can add their own
    custom snippets which are stored in-memory (session-scoped).
    """

    def __init__(self) -> None:
        self._builtins: list[Snippet] = _builtin_snippets()
        self._custom: list[Snippet] = []

    # ── Query ────────────────────────────────────────────────────────

    def _all(self) -> list[Snippet]:
        """Return combined list of built-in + custom snippets."""
        return self._builtins + self._custom

    def search(
        self,
        query: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Snippet]:
        """Search snippets by query text, optional category, and optional tags.

        The query is matched against title, description, code, and tags.
        An empty query returns all snippets (optionally filtered by category/tags).
        """
        q = query.lower().strip()
        results: list[Snippet] = []

        for snippet in self._all():
            # Category filter
            if category and snippet.category.lower() != category.lower():
                continue

            # Tags filter (all requested tags must be present)
            if tags:
                snippet_tags_lower = {t.lower() for t in snippet.tags}
                if not all(t.lower() in snippet_tags_lower for t in tags):
                    continue

            # Text search (empty query matches everything)
            if q:
                searchable = " ".join(
                    [
                        snippet.title.lower(),
                        snippet.description.lower(),
                        snippet.code.lower(),
                        " ".join(t.lower() for t in snippet.tags),
                        snippet.category.lower(),
                    ]
                )
                if q not in searchable:
                    continue

            results.append(snippet)

        return results

    def get_by_category(self, category: str) -> list[Snippet]:
        """Get all snippets in a given category."""
        return [s for s in self._all() if s.category.lower() == category.lower()]

    def get_categories(self) -> list[str]:
        """Return sorted list of unique categories."""
        cats: set[str] = set()
        for s in self._all():
            if s.category:
                cats.add(s.category)
        return sorted(cats)

    def get_snippet(self, snippet_id: str) -> Snippet | None:
        """Get a snippet by ID."""
        for s in self._all():
            if s.id == snippet_id:
                return s
        return None

    # ── Custom snippets ──────────────────────────────────────────────

    def add_custom(self, snippet: Snippet) -> Snippet:
        """Add a user-defined snippet to the library.

        If no ID is provided, one is generated automatically.
        """
        if not snippet.id:
            snippet.id = f"custom-{uuid.uuid4().hex[:8]}"
        if not snippet.created_at:
            snippet.created_at = datetime.now().isoformat()
        self._custom.append(snippet)
        logger.info(f"Added custom snippet: {snippet.title} ({snippet.id})")
        return snippet

    def delete_custom(self, snippet_id: str) -> bool:
        """Delete a custom snippet by ID.  Built-in snippets cannot be deleted."""
        for i, s in enumerate(self._custom):
            if s.id == snippet_id:
                self._custom.pop(i)
                logger.info(f"Deleted custom snippet: {snippet_id}")
                return True
        return False

    # ── Usage tracking ───────────────────────────────────────────────

    def record_use(self, snippet_id: str) -> None:
        """Increment the usage counter for a snippet."""
        for s in self._all():
            if s.id == snippet_id:
                s.uses += 1
                return
