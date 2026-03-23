# :mag: Data Exploration

FlowyML Notebook provides a **premium data exploration experience** — every DataFrame gets automatic, multi-tab visual profiling with zero extra code.

---

## Rich Context Display

When you return a DataFrame (Pandas or Polars), FlowyML Notebook automatically generates a **Rich Context Display** with 10 interactive tabs:

| Tab | What It Shows |
|-----|--------------|
| :bar_chart: **Table** | Sortable, paginated data view |
| :chart_with_upwards_trend: **Stats** | Column-level statistics with bento-grid summary |
| :chart: **Charts** | Auto-generated histograms and distribution plots |
| :link: **Correlations** | Pearson correlation heatmap |
| :shield: **Quality** | Missing values, duplicates, data integrity |
| :bulb: **Insights** | Outlier detection, scaling, target suggestions |
| :left_right_arrow: **Compare** | Side-by-side DataFrame comparison |
| :robot: **AI** | AI-powered data analysis |
| :wrench: **SmartPrep** | Actionable preprocessing suggestions with code |
| :brain: **Algorithms** | ML algorithm recommendations with pipeline code |

---

## Stats View

A high-density overview of the most critical metrics: total rows, column count, missing values, and memory impact — plus per-column statistics with type detection.

<figure markdown>
  ![Stats View](screenshots/pandas-display.png){ width="100%" }
  <figcaption>Bento-grid summary deck with per-column mean, std, min/max, quartiles, skew, and kurtosis</figcaption>
</figure>

---

## Charts View

Auto-generated visualizations for every column. Numeric columns get histograms with µ/σ annotations. Categorical columns get horizontal bar charts with value counts.

<figure markdown>
  ![Charts View](screenshots/pandas-display2.png){ width="100%" }
  <figcaption>Interactive charts: learning_rate, accuracy, f1_score distributions, model counts, status breakdown</figcaption>
</figure>

---

## Correlations

Pearson correlation matrix with color-coded heatmap. Instantly spot positive (purple) and negative (red) relationships between features.

<figure markdown>
  ![Correlations](screenshots/pangas-display3.png){ width="100%" }
  <figcaption>Color-coded correlation matrix with scrollable DataFrame output</figcaption>
</figure>

---

## ML Insights

Automated recommendations for ML preprocessing — no manual analysis needed:

- **:zap: Outlier Detection** — IQR-based detection with percentage and bounds
- **:scales: Scaling Recommendations** — Log transform, no scaling, or normalization suggestions
- **:dart: Target Variables** — Automatically identifies classification and regression targets

<figure markdown>
  ![ML Insights](screenshots/recommendations.png){ width="100%" }
  <figcaption>training_time_s has 6% outliers, n_estimators needs log transform, model and status identified as targets</figcaption>
</figure>

---

## :wrench: SmartPrep Advisor — NEW in v1.2

Go beyond insights — get **actionable preprocessing suggestions** with severity-ranked cards and ready-to-run Python code.

The SmartPrep tab detects 6 categories of data quality issues:

- **Missing Values** — Per-column null analysis with imputation strategy (median for numeric, mode for categorical, drop for >60% missing)
- **Skewed Distributions** — Skewness detection with `log1p` or Yeo-Johnson power transform suggestions
- **Outliers** — IQR-based detection with `clip()` code
- **High Cardinality** — Categorical columns >50 unique values flagged for frequency encoding
- **Class Imbalance** — Target variable ratio analysis with SMOTE and class weight suggestions
- **Feature Scaling** — Cross-feature range analysis (>100x difference triggers `StandardScaler` suggestion)

Each card includes a **"Generate Cell"** button that inserts the fix directly into your notebook. Use **"Apply All Fixes"** to insert all suggestions at once.

---

## :brain: Algorithm Matchmaker — NEW in v1.2

Select a target column and get **ranked ML algorithm recommendations** with reasoning, caveats, and complete pipeline code.

The Matchmaker analyzes:

- **Task type** — Automatically detects classification (≤20 unique), regression (>20), or clustering (no target)
- **Data characteristics** — Sample size, feature counts, dimensionality, null presence
- **Algorithm fit** — Scores each algorithm 0-100 based on your specific data profile

Supported algorithms include Random Forest, XGBoost, LightGBM, Logistic/Linear Regression, SVM, KNN, ElasticNet, KMeans, DBSCAN, and Hierarchical Clustering.

Click **"Generate Pipeline Cell"** to insert a complete sklearn pipeline — train/test split, model fitting, and evaluation metrics — directly into your notebook.

---

## Built-in Visualization Libraries

In addition to the automatic profiling, FlowyML Notebook includes:

- **Plotly** — Interactive, web-ready charts
- **Matplotlib / Seaborn** — Static, publication-quality plots
- **Altair / Vega** — Declarative statistical visualizations
- **Recharts** — Built-in chart renderer for DataFrame outputs

## Exporting

Every visualization and table can be exported:

- :camera: **Copy as Image** — For presentations or documents
- :floppy_disk: **Export as CSV/Parquet** — For downstream processing
- :bar_chart: **Promote to Dashboard** — Turn exploration cells into interactive dashboards

