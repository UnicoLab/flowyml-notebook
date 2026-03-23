# /// flowyml-notebook
# name: FlowyML E2E Demo
# version: 1
# ///

# %% [code] id=4f3ec0ca "imports"
# FlowyML Notebook — E2E Demo
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
print('\u2705 Libraries loaded successfully')

# %% [code] id=041a3983 "data_generation"
# Generate ML experiment dataset
np.random.seed(42)
n = 100

df = pd.DataFrame({
    'experiment_id': [f'exp_{i:03d}' for i in range(n)],
    'model': np.random.choice(['RandomForest', 'XGBoost', 'LightGBM', 'Neural Net', 'SVM'], n),
    'learning_rate': np.round(np.random.uniform(0.001, 0.1, n), 4),
    'n_estimators': np.random.choice([50, 100, 200, 500, 1000], n),
    'accuracy': np.round(np.random.uniform(0.72, 0.98, n), 4),
    'f1_score': np.round(np.random.uniform(0.68, 0.96, n), 4),
    'training_time_s': np.round(np.random.exponential(30, n), 2),
    'memory_mb': np.round(np.random.uniform(50, 2000, n), 1),
    'dataset_size': np.random.choice([1000, 5000, 10000, 50000, 100000], n),
    'status': np.random.choice(['completed', 'completed', 'completed', 'failed', 'timeout'], n),
    'created_at': [datetime.now() - timedelta(hours=np.random.randint(1, 720)) for _ in range(n)],
})

print(f'Generated {len(df)} experiments with {len(df.columns)} features')
df

# %% [code] id=90342531 "analysis"
# Analysis: Best models by accuracy
summary = df.groupby('model').agg(
    avg_accuracy=('accuracy', 'mean'),
    avg_f1=('f1_score', 'mean'),
    avg_time=('training_time_s', 'mean'),
    count=('experiment_id', 'count'),
    best_accuracy=('accuracy', 'max'),
).round(4).sort_values('avg_accuracy', ascending=False)

print('\U0001f3c6 Model Performance Summary:')
summary

# %% [code] id=5218f349 "exploration"
# Filter and explore: high-performance experiments
top_experiments = df[
    (df['accuracy'] > 0.90) &
    (df['status'] == 'completed')
].sort_values('accuracy', ascending=False)

print(f'\U0001f680 Found {len(top_experiments)} high-performance experiments (accuracy > 90%)')
top_experiments[['experiment_id', 'model', 'accuracy', 'f1_score', 'training_time_s', 'memory_mb']]

# %% [markdown] id=4700ae65 "summary"
# ## \U0001f4ca Results Summary\n\nThis demo notebook shows end-to-end FlowyML Notebook capabilities:\n\n- **DataFrame display** with interactive exploration\n- **Cell execution metrics** (duration, memory)\n- **Reactive execution** — downstream cells auto-update\n- **Variable inspector** — track all variables in the session\n\n> Click **Run All** to execute all cells and see results!

