# 📊 Data Exploration

FlowyML Notebook provides a premium data exploration experience, delivering deep visual insights directly within your cells.

## Rich Context Display

When you return a DataFrame (Pandas or Polars), FlowyML Notebook automatically generates a **Rich Context Display**, inspired by best-in-class research environments like Deepnote.

### Features

- **Interactive Tables**: Sort, filter, and paginated views for large datasets.
- **Bento-Grid Summary Deck**: A high-density overview of the most critical dataset metrics (rows, columns, missing values, memory footprint) using a modern grid layout.
- **Auto-generated Histograms**: Visual distributions for every numerical column with premium `framer-motion` animations.
- **Categorical Overviews**: Unique value counts and distribution charts for string/object columns.
- **Micro-Animations**: Subtle entrance and exit animations for all data panels and AI insights.
- **Smart Statistics**: Automated calculation of mean, median, standard deviation, and quartiles.
- **Null Analysis**: Rapidly identify missing data across your entire feature set with intelligent color-coding.

## Built-in Visualizations


In addition to DataFrame stats, FlowyML Notebook includes auto-injected visualization libraries:
- **Plotly Integration**: Interactive, web-ready charts.
- **Matplotlib/Seaborn**: Static, high-fidelity plots for publications.
- **Altair/Vega**: Declarative statistical visualizations.

## Machine Learning Observability

As you train models, FlowyML Notebook captures and displays:
- **Feature Importance**: Direct visualization of which features are driving model predictions.
- **Loss Curves**: Real-time tracking of training and validation metrics.
- **Drift Detection**: Automatic comparison between training and serving distributions.

## Exporting Analytics

Every visualization and table and be exported with a single click:
- **Copy as Image**: For presentations or documents.
- **Export as CSV/Parquet**: For downstream processing.
- **Promote to Dashboard**: Turn your exploration cells into a permanent interactive dashboard.
