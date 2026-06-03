import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Package, Search, Plus, Star, StarOff, Download, Upload, Edit3,
  Trash2, Copy, ChevronRight, ChevronDown, Code, Database,
  BarChart2, Zap, Puzzle, GitBranch, GripVertical, X,
  FolderPlus, Tag, Check, ExternalLink, RefreshCw, TrendingUp,
  Share2, Eye, Brain, Languages, Clock, Shield, Layers
} from 'lucide-react';

// Built-in recipe categories
const CATEGORIES = [
  { id: 'flowyml-core', label: 'Core', icon: Zap, color: 'var(--accent)' },
  { id: 'flowyml-assets', label: 'Assets', icon: Database, color: 'var(--cyan)' },
  { id: 'flowyml-parallel', label: 'Parallel', icon: Zap, color: '#a855f7' },
  { id: 'flowyml-observe', label: 'Observability', icon: Eye, color: '#f59e0b' },
  { id: 'flowyml-evals', label: 'Evals', icon: TrendingUp, color: '#10b981' },
  { id: 'production', label: 'Production', icon: Shield, color: '#ef4444' },
  { id: 'nlp', label: 'NLP', icon: Languages, color: '#06b6d4' },
  { id: 'time-series', label: 'Time Series', icon: Clock, color: '#f97316' },
  { id: 'deep-learning', label: 'Deep Learning', icon: Brain, color: '#8b5cf6' },
  { id: 'data-engineering', label: 'Data Engineering', icon: Layers, color: '#14b8a6' },
  { id: 'data-prep', label: 'Data Prep', icon: Database, color: 'var(--success)' },
  { id: 'ml', label: 'ML / Models', icon: BarChart2, color: 'var(--warning)' },
  { id: 'viz', label: 'Visualization', icon: BarChart2, color: '#e879f9' },
  { id: 'custom', label: 'Custom', icon: Puzzle, color: 'var(--fg-dim)' },
  { id: 'shared', label: 'Shared', icon: Share2, color: '#60a5fa' },
];

// Default built-in recipes — comprehensive FlowyML collection

// ── Python syntax highlighting (CSS-based, no external lib) ──
function highlightPython(code) {
  if (!code) return '';
  // Escape HTML first
  const esc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Token patterns (order matters — strings/comments first to avoid partial matches)
  const patterns = [
    // Triple-quoted strings
    [/(&quot;&quot;&quot;[\s\S]*?&quot;&quot;&quot;|&#039;&#039;&#039;[\s\S]*?&#039;&#039;&#039;|"""[\s\S]*?"""|'''[\s\S]*?''')/g, 'syn-str'],
    // Comments
    [/(#.*)/gm, 'syn-cmt'],
    // Strings (double/single)
    [/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g, 'syn-str'],
    // Decorators
    [/(@\w+)/g, 'syn-dec'],
    // Keywords
    [/\b(from|import|def|class|return|if|elif|else|for|while|in|not|and|or|is|with|as|try|except|finally|raise|yield|lambda|pass|break|continue|async|await|None|True|False)\b/g, 'syn-kw'],
    // Builtins
    [/\b(print|len|range|type|str|int|float|list|dict|set|tuple|enumerate|zip|map|filter|sorted|sum|min|max|abs|open|isinstance|super|round|format)\b/g, 'syn-bi'],
    // FlowyML identifiers
    [/\b(Pipeline|step|context|Context|Dataset|Model|Metrics|Artifact|FeatureSet|Report|Prompt|Checkpoint|Experiment|Run|ModelRegistry|ArtifactCatalog|EvalSuite|EvalSchedule|SmartCache|TraceBridge|JudgeArena)\b/g, 'syn-fml'],
    // Numbers
    [/\b(\d+\.?\d*(?:e[+-]?\d+)?|0x[0-9a-f]+)\b/gi, 'syn-num'],
    // f-string prefix
    [/\b(f)(?=["\'\{])/g, 'syn-kw'],
  ];

  let result = esc;
  // Apply patterns — skip already-wrapped spans
  patterns.forEach(([regex, cls]) => {
    result = result.replace(regex, (match) => {
      // Don't double-wrap
      if (match.includes('class="syn-')) return match;
      return `<span class="${cls}">${match}</span>`;
    });
  });

  return result;
}

const BUILTIN_RECIPES = [
  // ═══════════════════════════════════════
  //  FlowyML CORE — Steps & Pipelines
  // ═══════════════════════════════════════
  {
    id: 'fml-step-basic',
    name: 'FlowyML Step',
    category: 'flowyml-core',
    description: 'Define a reusable pipeline step with typed I/O',
    tags: ['step', 'pipeline', 'decorator'],
    builtin: true,
    docs: 'The @step decorator registers a function as a pipeline step. Use `inputs` and `outputs` to declare typed data flow.',
    source: `from flowyml import step

@step(outputs=["data/processed"])
def process_data(raw_input):
    """Process and clean raw input data."""
    import pandas as pd
    df = pd.DataFrame(raw_input)
    
    # Clean and transform
    df = df.dropna()
    df = df.drop_duplicates()
    
    print(f"✅ Processed {len(df)} rows")
    return df`,
  },
  {
    id: 'fml-step-io',
    name: 'Step with Inputs/Outputs',
    category: 'flowyml-core',
    description: 'Step with explicit input/output declarations and caching',
    tags: ['step', 'inputs', 'outputs', 'cache'],
    builtin: true,
    docs: 'Declare explicit inputs/outputs for the reactive dependency graph. Use execution_group to batch related steps.',
    source: `from flowyml import step

@step(
    inputs=["data/train", "data/val"],
    outputs=["model/trained"],
    cache=True,
    execution_group="training",
)
def train_model(train_data, val_data, learning_rate=0.01, epochs=100):
    """Train model with automatic dependency tracking."""
    print(f"🎯 Training: lr={learning_rate}, epochs={epochs}")
    print(f"   Train: {len(train_data)} samples")
    print(f"   Val: {len(val_data)} samples")
    
    # Your training code here
    model = {"weights": "trained", "lr": learning_rate}
    return model`,
  },
  {
    id: 'fml-pipeline',
    name: 'FlowyML Pipeline',
    category: 'flowyml-core',
    description: 'Complete pipeline with context, steps, and execution',
    tags: ['pipeline', 'orchestration', 'context'],
    builtin: true,
    docs: 'A Pipeline orchestrates step execution with automatic dependency resolution. Context provides shared parameters.',
    source: `from flowyml import Pipeline, step, context

# Shared configuration
ctx = context(
    data_path="data.csv",
    learning_rate=0.01,
    batch_size=32,
    epochs=50,
)

@step(outputs=["data/raw"])
def load_data(data_path):
    import pandas as pd
    df = pd.read_csv(data_path)
    print(f"📂 Loaded {len(df)} rows")
    return df

@step(inputs=["data/raw"], outputs=["data/clean"])
def preprocess(df):
    df = df.dropna().drop_duplicates()
    print(f"🧹 Clean: {len(df)} rows")
    return df

@step(inputs=["data/clean"], outputs=["model/trained"])
def train(df, learning_rate, epochs):
    print(f"🎯 Training: lr={learning_rate}, epochs={epochs}")
    return {"trained": True}

# Build & run
pipeline = Pipeline("my_pipeline", context=ctx, version="1.0.0")
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train)

result = pipeline.run()
print(f"{'✅' if result.success else '❌'} Pipeline {'completed' if result.success else 'failed'}")`,
  },
  {
    id: 'fml-conditional',
    name: 'Conditional Branching',
    category: 'flowyml-core',
    description: 'Add If/Switch control flow to pipelines',
    tags: ['conditional', 'branching', 'if', 'switch'],
    builtin: true,
    docs: 'Use If() for binary decisions and Switch() for multi-way branching based on runtime conditions.',
    source: `from flowyml import Pipeline, step, context, If, Switch

@step(inputs=["metrics/eval"], outputs=["deploy/status"])
def deploy_model(model):
    print("🚀 Deploying model to production!")
    return {"status": "deployed"}

@step(inputs=["metrics/eval"])
def retrain_model(metrics):
    print("🔄 Model needs retraining, accuracy too low")

# Conditional deployment
def check_accuracy(ctx):
    """Deploy only if accuracy > 0.9"""
    metrics = ctx.steps["evaluate"].outputs["metrics/eval"]
    return metrics.data.get("accuracy", 0) > 0.9

pipeline.add_control_flow(
    If(
        condition=check_accuracy,
        then_step=deploy_model,
        else_step=retrain_model,
    )
)`,
  },
  {
    id: 'fml-context',
    name: 'Context & Configuration',
    category: 'flowyml-core',
    description: 'Configure pipelines with typed context parameters',
    tags: ['context', 'config', 'parameters'],
    builtin: true,
    source: `from flowyml import context, Pipeline, step

# Context provides type-safe configuration
ctx = context(
    # Data settings
    data_path="s3://bucket/train.csv",
    test_size=0.2,
    random_seed=42,
    
    # Model hyperparameters
    model_type="xgboost",
    learning_rate=0.1,
    max_depth=6,
    n_estimators=200,
    
    # Deployment
    min_accuracy=0.85,
    deploy_target="staging",
)

# Steps automatically receive matching context parameters
@step(outputs=["data/raw"])
def load(data_path, random_seed):
    """data_path and random_seed are injected from context."""
    print(f"Loading from {data_path} (seed={random_seed})")`,
  },
  {
    id: 'fml-template',
    name: 'Pipeline from Template',
    category: 'flowyml-core',
    description: 'Create pipelines using built-in templates',
    tags: ['template', 'quick-start', 'etl'],
    builtin: true,
    source: `from flowyml import create_from_template, list_templates

# Available templates: ml_training, etl, data_pipeline, ab_test
print("📋 Templates:", list_templates())

# Create an ETL pipeline from template
pipeline = create_from_template(
    "etl",
    name="my_etl",
    extractor=lambda: {"raw": "data"},
    transformer=lambda data: {"clean": data},
    loader=lambda data: print(f"Loaded: {data}"),
)

result = pipeline.run()`,
  },
  {
    id: 'fml-scheduler',
    name: 'Pipeline Scheduling',
    category: 'flowyml-core',
    description: 'Schedule pipelines to run on cron/daily/hourly',
    tags: ['scheduler', 'cron', 'automation'],
    builtin: true,
    source: `from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Run daily at 2am
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: my_pipeline.run(),
    hour=2, minute=0,
    timezone="UTC",
)

# Run every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: etl_pipeline.run(),
    hours=6,
)

# Cron expression
scheduler.schedule_cron(
    name="weekly_retrain",
    pipeline_func=lambda: training_pipeline.run(),
    cron="0 3 * * MON",  # Every Monday at 3am
)

scheduler.start()
print("📅 Scheduler running...")`,
  },
  {
    id: 'fml-map-task',
    name: 'Map Task (Fan-Out)',
    category: 'flowyml-core',
    description: 'Process items in parallel with map_task',
    tags: ['map', 'fan-out', 'parallel', 'batch'],
    builtin: true,
    source: `from flowyml import map_task, step

@step(outputs=["data/items"])
def get_items():
    return [{"id": i, "value": i * 10} for i in range(20)]

@map_task(inputs=["data/items"], outputs=["results/processed"])
def process_item(item):
    """Runs on each item in parallel."""
    result = item["value"] ** 2
    print(f"  Processed item {item['id']}: {result}")
    return {"id": item["id"], "result": result}

# Results are automatically collected into a list`,
  },
  {
    id: 'fml-subpipeline',
    name: 'Sub-Pipeline',
    category: 'flowyml-core',
    description: 'Compose pipelines by nesting them as sub-pipelines',
    tags: ['subpipeline', 'composition', 'modular'],
    builtin: true,
    source: `from flowyml import Pipeline, step, sub_pipeline

# Define a reusable sub-pipeline
preprocessing_pipeline = Pipeline("preprocessing")

@step(outputs=["data/clean"])
def clean(df):
    return df.dropna()

preprocessing_pipeline.add_step(clean)

# Use it in a parent pipeline
main_pipeline = Pipeline("main")
main_pipeline.add_step(
    sub_pipeline(preprocessing_pipeline, name="preprocess")
)`,
  },
  // ═══════════════════════════════════════
  //  FlowyML ASSETS
  // ═══════════════════════════════════════
  {
    id: 'fml-dataset',
    name: 'Dataset Asset',
    category: 'flowyml-assets',
    description: 'Create a tracked Dataset asset with metadata',
    tags: ['dataset', 'asset', 'tracking'],
    builtin: true,
    docs: 'Dataset wraps your data with version tracking, metadata, and lineage.',
    source: `from flowyml import Dataset
import pandas as pd

df = pd.read_csv("data.csv")

# Create a tracked Dataset
dataset = Dataset.create(
    data=df.to_dict("records"),
    name="customer_churn_v2",
    properties={
        "source": "data.csv",
        "rows": len(df),
        "columns": list(df.columns),
        "target": "churned",
    },
    tags={"domain": "customer", "version": "2.0"},
)

print(f"📊 Dataset: {dataset.name}")
print(f"   Rows: {dataset.properties['rows']}")
print(f"   Columns: {dataset.properties['columns']}")`,
  },
  {
    id: 'fml-model',
    name: 'Model Asset',
    category: 'flowyml-assets',
    description: 'Track a trained model with automatic framework detection',
    tags: ['model', 'asset', 'tracking'],
    builtin: true,
    source: `from flowyml import Model
from sklearn.ensemble import RandomForestClassifier

# Train model
clf = RandomForestClassifier(n_estimators=100)
clf.fit(X_train, y_train)

# Create tracked Model asset — auto-detects framework!
model_asset = Model.create(
    data=clf,
    name="churn_predictor_v3",
    properties={
        "framework": "sklearn",
        "algorithm": "RandomForest",
        "n_estimators": 100,
        "accuracy": 0.94,
        "features": list(X_train.columns),
    },
)

print(f"🤖 Model: {model_asset.name}")
print(f"   Framework: {model_asset.properties.get('framework')}")`,
  },
  {
    id: 'fml-model-keras',
    name: 'Keras Model Asset',
    category: 'flowyml-assets',
    description: 'Track a Keras model with auto-extracted architecture',
    tags: ['keras', 'model', 'deep-learning'],
    builtin: true,
    source: `from flowyml import Model
from flowyml.integrations.keras import FlowymlKerasCallback
import keras

# Build model
model = keras.Sequential([
    keras.layers.Dense(128, activation="relu", input_shape=(10,)),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(64, activation="relu"),
    keras.layers.Dense(1, activation="sigmoid"),
])

# Auto-tracking callback
callback = FlowymlKerasCallback(
    experiment_name="deep-churn-model",
    project="churn_detection",
)

model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
model.fit(X_train, y_train, epochs=20, callbacks=[callback], validation_split=0.2)

# Auto-extracts: architecture, params, optimizer, training history
model_asset = Model.from_keras(model, name="deep_churn", callback=callback)
print(f"🧠 {model_asset.name}: {model_asset.parameters:,} params")`,
  },
  {
    id: 'fml-metrics',
    name: 'Metrics Asset',
    category: 'flowyml-assets',
    description: 'Track evaluation metrics with Metrics asset',
    tags: ['metrics', 'evaluation', 'tracking'],
    builtin: true,
    source: `from flowyml import Metrics
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

metrics = Metrics.create(
    data={
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_score": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
    },
    name="eval_metrics_v3",
    properties={"dataset": "test_set", "samples": len(y_test)},
)

for k, v in metrics.data.items():
    print(f"   📊 {k}: {v:.4f}")`,
  },
  {
    id: 'fml-featureset',
    name: 'FeatureSet Asset',
    category: 'flowyml-assets',
    description: 'Track feature engineering with FeatureSet',
    tags: ['features', 'asset', 'feature-store'],
    builtin: true,
    source: `from flowyml import FeatureSet
import pandas as pd

# Your engineered features
features_df = pd.DataFrame({
    "user_tenure_days": [120, 30, 365],
    "activity_score": [0.8, 0.2, 0.95],
    "purchase_frequency": [5, 1, 12],
    "churn_risk_score": [0.15, 0.87, 0.05],
})

feature_set = FeatureSet.create(
    data=features_df.to_dict("list"),
    name="churn_features_v2",
    properties={
        "feature_count": len(features_df.columns),
        "entity": "user",
        "frequency": "daily",
    },
)

print(f"🔧 FeatureSet: {feature_set.name}")
print(f"   Features: {list(features_df.columns)}")`,
  },
  {
    id: 'fml-report',
    name: 'Report Asset',
    category: 'flowyml-assets',
    description: 'Generate a tracking Report for your pipeline run',
    tags: ['report', 'documentation', 'summary'],
    builtin: true,
    source: `from flowyml import Report

report = Report.create(
    data={
        "title": "Model Training Report",
        "sections": [
            {"heading": "Data Summary", "content": f"Trained on {len(X_train)} samples"},
            {"heading": "Model Performance", "content": "Accuracy: 94.2%, F1: 0.91"},
            {"heading": "Next Steps", "content": "A/B test against v2 in production"},
        ],
    },
    name="training_report_v3",
    properties={"pipeline": "churn_training", "author": "data-team"},
)

print(f"📝 Report: {report.name}")`,
  },
  {
    id: 'fml-experiment',
    name: 'Experiment Tracking',
    category: 'flowyml-assets',
    description: 'Track experiments and compare runs',
    tags: ['experiment', 'tracking', 'runs', 'comparison'],
    builtin: true,
    source: `from flowyml import Experiment, Run, ModelLeaderboard, compare_runs

# Create experiment
experiment = Experiment(name="churn_prediction", project="ml-team")

# Log a run
with experiment.run(name="xgboost_v3") as run:
    run.log_params({"lr": 0.1, "max_depth": 6, "n_estimators": 200})
    run.log_metrics({"accuracy": 0.942, "f1": 0.91, "auc": 0.967})
    run.log_artifact("model", model)

# Compare runs
comparison = compare_runs(experiment.runs[-3:])
print(comparison)

# Leaderboard
leaderboard = ModelLeaderboard(experiment)
print(leaderboard.rank_by("accuracy"))`,
  },
  {
    id: 'fml-model-registry',
    name: 'Model Registry',
    category: 'flowyml-assets',
    description: 'Register and manage model versions with staging',
    tags: ['registry', 'versioning', 'staging', 'production'],
    builtin: true,
    source: `from flowyml import ModelRegistry, ModelStage

registry = ModelRegistry()

# Register a new model version
version = registry.register(
    name="churn_predictor",
    model=model,
    metrics={"accuracy": 0.942, "f1": 0.91},
    description="XGBoost v3 with engineered features",
)

# Promote through stages
registry.transition(
    name="churn_predictor",
    version=version.version,
    stage=ModelStage.STAGING,
)

# List versions
for v in registry.list_versions("churn_predictor"):
    print(f"  v{v.version} [{v.stage}] — acc: {v.metrics.get('accuracy', 'N/A')}")`,
  },
  // ═══════════════════════════════════════
  //  FlowyML PARALLEL & ERROR HANDLING
  // ═══════════════════════════════════════
  {
    id: 'fml-parallel',
    name: 'Parallel Execution',
    category: 'flowyml-parallel',
    description: 'Execute steps in parallel with ParallelExecutor',
    tags: ['parallel', 'concurrent', 'performance'],
    builtin: true,
    source: `from flowyml import ParallelExecutor, BatchExecutor, parallel_map

# Parallel map — process data chunks concurrently
def process_chunk(chunk):
    return chunk ** 2

results = parallel_map(process_chunk, data_chunks, max_workers=4)

# Batch executor — process large datasets in batches
batch_exec = BatchExecutor(batch_size=1000, max_workers=4)
results = batch_exec.execute(process_fn, large_dataset)

print(f"✨ Processed {len(results)} results in parallel")`,
  },
  {
    id: 'fml-retry',
    name: 'Retry & Error Handling',
    category: 'flowyml-parallel',
    description: 'Add retry logic and circuit breakers to steps',
    tags: ['retry', 'error', 'resilience', 'circuit-breaker'],
    builtin: true,
    docs: 'Use @retry for transient failures, CircuitBreaker for cascading failure protection, and FallbackHandler for graceful degradation.',
    source: `from flowyml import retry, CircuitBreaker, FallbackHandler, on_failure

# Retry with exponential backoff
@retry(max_retries=3, backoff_factor=2.0)
@step(outputs=["data/external"])
def fetch_external_data():
    """Retries up to 3 times with exponential backoff."""
    import requests
    resp = requests.get("https://api.example.com/data", timeout=10)
    resp.raise_for_status()
    return resp.json()

# Circuit breaker — stops calling after N failures
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)

@breaker
def call_ml_service(payload):
    return ml_client.predict(payload)

# Fallback handler
fallback = FallbackHandler(
    primary=call_ml_service,
    fallback=lambda x: {"prediction": "default", "confidence": 0.0},
)
result = fallback.execute(input_data)`,
  },
  {
    id: 'fml-checkpoint',
    name: 'Pipeline Checkpointing',
    category: 'flowyml-parallel',
    description: 'Save and resume long-running pipelines',
    tags: ['checkpoint', 'resume', 'fault-tolerance'],
    builtin: true,
    source: `from flowyml import PipelineCheckpoint, checkpoint_enabled_pipeline

# Enable checkpointing on a pipeline
pipeline = checkpoint_enabled_pipeline(
    "long_training",
    checkpoint_dir="./checkpoints",
    save_interval=5,  # Save every 5 steps
)

# Add steps...
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train)

# Run — automatically resumes from last checkpoint on failure
result = pipeline.run(resume=True)`,
  },
  {
    id: 'fml-caching',
    name: 'Smart Caching',
    category: 'flowyml-parallel',
    description: 'Content-based and shared caching strategies',
    tags: ['cache', 'memoize', 'performance'],
    builtin: true,
    source: `from flowyml import ContentBasedCache, SmartCache, memoize, step

# Content-based caching — invalidates when input data changes
@step(outputs=["data/features"], cache=True)
def compute_features(df):
    """Cached based on df content hash."""
    return expensive_feature_engineering(df)

# Decorator-based memoization
@memoize(ttl=3600)
def get_model_predictions(model_id, input_data):
    return model.predict(input_data)

# Smart cache — auto-selects strategy
cache = SmartCache(max_size=1000, ttl=3600)
cache.set("my_key", expensive_result)
cached = cache.get("my_key")`,
  },
  // ═══════════════════════════════════════
  //  FlowyML OBSERVABILITY
  // ═══════════════════════════════════════
  {
    id: 'fml-genai-trace',
    name: 'GenAI Tracing (Base)',
    category: 'flowyml-observe',
    description: 'Trace LLM calls with FlowyML observability',
    tags: ['tracing', 'llm', 'observability', 'genai'],
    builtin: true,
    source: `from flowyml import trace_genai, observe_genai, log_llm_call, span

# Trace a function
@trace_genai(name="my_ai_workflow")
def ai_pipeline(prompt):
    # Auto-traces LLM calls
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return response

# Manual span for custom tracing
with span("preprocessing") as s:
    cleaned = preprocess(data)
    s.set_attribute("rows_processed", len(cleaned))

# Log individual LLM calls
log_llm_call(
    model="gpt-4",
    prompt="Summarize this text...",
    completion="Here is the summary...",
    tokens_used=150,
    latency_ms=1200,
)`,
  },
  {
    id: 'fml-openai-trace',
    name: 'OpenAI Observability',
    category: 'flowyml-observe',
    description: 'Auto-trace OpenAI API calls with zero config',
    tags: ['openai', 'tracing', 'gpt-4', 'auto'],
    builtin: true,
    source: `from flowyml import patch_openai, TracedOpenAI
import openai

# Option 1: Monkey-patch existing client
patch_openai()

# All OpenAI calls are now auto-traced!
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Explain ML pipelines"}],
)

# Option 2: Use traced client directly
traced = TracedOpenAI(experiment="chatbot_v2")
response = traced.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(f"📊 Response tracked with {traced.total_tokens} tokens")`,
  },
  {
    id: 'fml-langchain-trace',
    name: 'LangChain/LangGraph Tracing',
    category: 'flowyml-observe',
    description: 'Trace LangChain chains and LangGraph workflows',
    tags: ['langchain', 'langgraph', 'tracing', 'agents'],
    builtin: true,
    source: `from flowyml import FlowyMLCallbackHandler, trace_graph, observe

# LangChain — auto-trace with callback
handler = FlowyMLCallbackHandler(experiment="rag_pipeline")

from langchain.chains import LLMChain
chain = LLMChain(llm=llm, prompt=prompt_template, callbacks=[handler])
result = chain.invoke({"query": "What is FlowyML?"})

# LangGraph — trace entire graph execution
@trace_graph(name="agent_workflow")
def run_agent(state):
    graph = build_agent_graph()
    return graph.invoke(state)

# Decorator-based observation
@observe(name="rag_query")
def rag_pipeline(query):
    docs = retriever.get_relevant_documents(query)
    answer = llm.invoke(docs)
    return answer`,
  },
  {
    id: 'fml-drift-detection',
    name: 'Data Drift Detection',
    category: 'flowyml-observe',
    description: 'Monitor data drift and compute statistics',
    tags: ['drift', 'monitoring', 'statistics'],
    builtin: true,
    source: `from flowyml import detect_drift, compute_stats

# Compute baseline statistics
baseline_stats = compute_stats(train_df)

# Check for drift in new data
drift_report = detect_drift(
    reference=train_df,
    current=new_data_df,
    features=["age", "income", "purchase_count"],
)

print(f"🔍 Drift Detection Report:")
for feature, result in drift_report.items():
    status = "⚠️ DRIFT" if result["drifted"] else "✅ OK"
    print(f"   {feature}: {status} (p={result['p_value']:.4f})")`,
  },
  {
    id: 'fml-notifications',
    name: 'Pipeline Notifications',
    category: 'flowyml-observe',
    description: 'Configure Slack, Email, and Console notifications',
    tags: ['notifications', 'slack', 'email', 'alerts'],
    builtin: true,
    source: `from flowyml import configure_notifications, get_notifier

# Configure notification channels
configure_notifications(
    slack_webhook="https://hooks.slack.com/services/...",
    email_to="team@company.com",
    email_from="ml-pipelines@company.com",
)

notifier = get_notifier()

# Send notifications
notifier.send(
    channel="slack",
    title="🚀 Model Deployed",
    message=f"churn_predictor v3 deployed to production\\nAccuracy: 94.2%",
    level="success",
)

# Auto-notify on pipeline completion
pipeline = Pipeline("training", on_complete=notifier.slack, on_failure=notifier.email)`,
  },
  // ═══════════════════════════════════════
  //  FlowyML EVALS
  // ═══════════════════════════════════════
  {
    id: 'fml-eval-basic',
    name: 'LLM Evaluation',
    category: 'flowyml-evals',
    description: 'Evaluate LLM outputs with built-in scorers',
    tags: ['eval', 'llm', 'quality', 'scoring'],
    builtin: true,
    docs: 'FlowyML Evals provides a framework for evaluating LLM outputs with custom and built-in scorers.',
    source: `from flowyml import evaluate, EvalDataset, make_scorer

# Create evaluation dataset
dataset = EvalDataset([
    {"input": "What is ML?", "expected": "Machine Learning is..."},
    {"input": "Explain NLP", "expected": "NLP stands for..."},
])

# Define scorers
relevance = make_scorer("relevance", model="gpt-4")
coherence = make_scorer("coherence")

# Run evaluation
results = evaluate(
    model_fn=lambda x: llm.invoke(x),
    dataset=dataset,
    scorers=[relevance, coherence],
)

print(f"📊 Eval Results:")
print(f"   Relevance: {results.avg('relevance'):.2f}")
print(f"   Coherence: {results.avg('coherence'):.2f}")`,
  },
  {
    id: 'fml-eval-suite',
    name: 'Evaluation Suite',
    category: 'flowyml-evals',
    description: 'Run comprehensive eval suites with assertions',
    tags: ['eval', 'suite', 'assertions', 'regression'],
    builtin: true,
    source: `from flowyml import EvalSuite, EvalAssert, EvalStep

suite = EvalSuite(
    name="chatbot_quality",
    steps=[
        EvalStep(
            name="greeting",
            input="Hello!",
            assertions=[
                EvalAssert.contains("hello", case_insensitive=True),
                EvalAssert.max_length(200),
                EvalAssert.no_toxicity(),
            ],
        ),
        EvalStep(
            name="factual",
            input="What year was Python created?",
            assertions=[
                EvalAssert.contains("1991"),
                EvalAssert.no_hallucination(context="Python was created by Guido van Rossum in 1991"),
            ],
        ),
    ],
)

results = suite.run(model_fn=lambda x: llm.invoke(x))
print(f"✅ Passed: {results.passed}/{results.total}")`,
  },
  {
    id: 'fml-judge-arena',
    name: 'Judge Arena (A/B)',
    category: 'flowyml-evals',
    description: 'Compare models head-to-head with LLM judges',
    tags: ['arena', 'comparison', 'judge', 'ab-test'],
    builtin: true,
    source: `from flowyml import JudgeArena, make_judge

# Create judge
judge = make_judge(
    model="gpt-4",
    criteria=["helpfulness", "accuracy", "conciseness"],
)

# Set up arena
arena = JudgeArena(judge=judge)

# Compare two models
results = arena.compare(
    model_a=lambda x: gpt35.invoke(x),
    model_b=lambda x: gpt4.invoke(x),
    prompts=[
        "Explain quantum computing",
        "Write a Python function to sort a list",
        "What causes inflation?",
    ],
)

print(f"🏆 Winner: Model {'A' if results.a_wins > results.b_wins else 'B'}")
print(f"   Model A wins: {results.a_wins}, Model B wins: {results.b_wins}")`,
  },
  {
    id: 'fml-prompt',
    name: 'Prompt Asset',
    category: 'flowyml-assets',
    description: 'Version-controlled prompt templates with variables',
    tags: ['prompt', 'llm', 'template', 'genai'],
    builtin: true,
    docs: 'The Prompt asset lets you version and manage LLM prompts as first-class pipeline artifacts with variable interpolation.',
    source: `from flowyml import Prompt

# Create a versioned prompt template
prompt = Prompt(
    name="summarizer",
    template="""You are an expert summarizer.
Summarize the following text in {style} style:

{text}

Keep it under {max_words} words.""",
    variables={"style": "concise", "max_words": "100"},
)

# Render with variables
rendered = prompt.render(
    text="FlowyML is a next-generation ML pipeline framework...",
    style="technical",
    max_words="50",
)
print(rendered)

# Save as asset for pipeline reuse
prompt.save("prompts/summarizer_v1")`,
  },
  {
    id: 'fml-checkpoint-asset',
    name: 'Checkpoint Save/Restore',
    category: 'flowyml-assets',
    description: 'Save and restore training state mid-pipeline',
    tags: ['checkpoint', 'save', 'restore', 'training'],
    builtin: true,
    docs: 'Checkpoint lets you persist intermediate training state so long-running pipelines can resume from the last good point.',
    source: `from flowyml import Checkpoint, step

@step(outputs=["model/trained"])
def train_model(data, epochs=100):
    """Train with automatic checkpointing."""
    ckpt = Checkpoint("training_checkpoint")

    # Restore if previous run exists
    start_epoch = 0
    if ckpt.exists():
        state = ckpt.restore()
        model = state["model"]
        start_epoch = state["epoch"]
        print(f"♻️ Resumed from epoch {start_epoch}")
    else:
        model = create_model()

    for epoch in range(start_epoch, epochs):
        loss = train_one_epoch(model, data)

        # Save checkpoint every 10 epochs
        if epoch % 10 == 0:
            ckpt.save({"model": model, "epoch": epoch, "loss": loss})
            print(f"💾 Checkpoint at epoch {epoch}, loss={loss:.4f}")

    return model`,
  },
  {
    id: 'fml-versioned-pipeline',
    name: 'Versioned Pipeline',
    category: 'flowyml-core',
    description: 'Freeze and version pipelines for reproducibility',
    tags: ['version', 'freeze', 'snapshot', 'reproducibility'],
    builtin: true,
    docs: 'VersionedPipeline + freeze_pipeline let you snapshot a pipeline definition so you can reproduce exact runs later.',
    source: `from flowyml import Pipeline, step, VersionedPipeline, freeze_pipeline

@step(outputs=["data/clean"])
def clean(raw): return raw.dropna()

@step(outputs=["model/trained"])
def train(clean_data): return fit_model(clean_data)

# Build pipeline
pipe = Pipeline("ml_pipeline", steps=[clean, train])

# Freeze current version (snapshot code + config)
snapshot = freeze_pipeline(pipe, version="1.0.0", tag="production")
print(f"📌 Frozen: {snapshot.version} at {snapshot.frozen_at}")

# Load a versioned pipeline later
versioned = VersionedPipeline("ml_pipeline")
versions = versioned.list_versions()
print(f"Available versions: {[v.version for v in versions]}")

# Run a specific historical version
versioned.run(version="1.0.0")`,
  },
  {
    id: 'fml-dynamic-step',
    name: 'Dynamic Step',
    category: 'flowyml-core',
    description: 'Create pipeline steps dynamically at runtime',
    tags: ['dynamic', 'runtime', 'adaptive', 'step'],
    builtin: true,
    docs: 'The @dynamic decorator lets a step create new sub-steps at runtime based on data or conditions — essential for adaptive pipelines.',
    source: `from flowyml import dynamic, step, Pipeline

@dynamic
def process_files(file_list):
    """Dynamically create a step per file at runtime."""
    results = []
    for f in file_list:
        # Each call creates a tracked sub-step
        result = process_single_file(f)
        results.append(result)
    return results

@step
def process_single_file(filepath):
    """Process one file — this runs as its own tracked step."""
    import pandas as pd
    df = pd.read_csv(filepath)
    df = df.dropna()
    print(f"✅ Processed {filepath}: {len(df)} rows")
    return df

pipe = Pipeline("adaptive", steps=[process_files])
pipe.run(file_list=["data_jan.csv", "data_feb.csv", "data_mar.csv"])`,
  },
  {
    id: 'fml-approval',
    name: 'Human Approval Gate',
    category: 'flowyml-core',
    description: 'Pause pipeline for human review before proceeding',
    tags: ['approval', 'gate', 'human-in-loop', 'review'],
    builtin: true,
    docs: 'The @approval decorator adds a human-in-the-loop gate that pauses the pipeline and waits for manual approval before continuing.',
    source: `from flowyml import approval, step, Pipeline

@step(outputs=["model/candidate"])
def train_candidate(data):
    model = train(data)
    metrics = evaluate(model)
    print(f"📊 Accuracy: {metrics['accuracy']:.2%}")
    return model, metrics

@approval(
    message="Review model metrics before deploying",
    timeout_hours=24,
    notify=["team-lead@company.com"],
)
@step(outputs=["model/production"])
def deploy_model(model, metrics):
    """This step only runs after human approval."""
    print("🚀 Deploying approved model to production")
    return deploy(model)

pipe = Pipeline("safe_deploy", steps=[train_candidate, deploy_model])
pipe.run(data=training_data)`,
  },
  {
    id: 'fml-artifact-catalog',
    name: 'Artifact Catalog',
    category: 'flowyml-assets',
    description: 'Browse, register, and fetch versioned artifacts',
    tags: ['catalog', 'browse', 'versioned', 'artifacts'],
    builtin: true,
    docs: 'ArtifactCatalog provides a searchable registry of all datasets, models, and artifacts produced by your pipelines.',
    source: `from flowyml import ArtifactCatalog, Dataset, Model

catalog = ArtifactCatalog()

# Register artifacts
dataset = Dataset(name="training_v3", data=df)
catalog.register(dataset, tags=["training", "v3"])

model = Model(name="xgb_classifier", model=trained_model)
catalog.register(model, tags=["production", "xgboost"])

# Browse catalog
all_items = catalog.list()
print(f"📦 {len(all_items)} artifacts in catalog")

# Search by tag
production = catalog.search(tags=["production"])
for item in production:
    print(f"  {item.name} ({item.type}) — v{item.version}")

# Fetch a specific artifact
fetched = catalog.fetch("training_v3", version="latest")
print(f"✅ Loaded: {fetched.name}, shape={fetched.data.shape}")`,
  },
  {
    id: 'fml-debug-step',
    name: 'Debug & Profile Steps',
    category: 'flowyml-observe',
    description: 'Debug, trace, and profile step execution',
    tags: ['debug', 'profile', 'trace', 'performance'],
    builtin: true,
    docs: 'Decorators for detailed step introspection: @debug_step prints inputs/outputs, @profile_step measures time/memory, @trace_step logs execution flow.',
    source: `from flowyml import step, debug_step, profile_step, trace_step

# Debug: prints inputs, outputs, and intermediate values
@debug_step
@step(outputs=["data/features"])
def extract_features(df):
    features = df.select_dtypes(include="number")
    print(f"Selected {len(features.columns)} numeric features")
    return features

# Profile: measures execution time and memory usage
@profile_step
@step(outputs=["model/trained"])
def train_model(features, labels):
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100)
    model.fit(features, labels)
    return model

# Trace: logs the full execution graph
@trace_step
@step(outputs=["metrics/evaluation"])
def evaluate_model(model, test_features, test_labels):
    score = model.score(test_features, test_labels)
    print(f"✅ Accuracy: {score:.2%}")
    return {"accuracy": score}`,
  },
  {
    id: 'fml-gpu-resource',
    name: 'GPU Resource Manager',
    category: 'flowyml-parallel',
    description: 'Allocate and manage GPU resources for training',
    tags: ['gpu', 'resource', 'allocation', 'training'],
    builtin: true,
    docs: 'GPUResourceManager handles GPU allocation and memory management for training steps that need hardware acceleration.',
    source: `from flowyml import GPUResourceManager, step

# Check available GPUs
gpu = GPUResourceManager()
devices = gpu.list_devices()
for dev in devices:
    print(f"🖥️ {dev.name}: {dev.memory_total}GB ({dev.memory_free}GB free)")

# Allocate specific GPU for training
@step(outputs=["model/trained"])
def train_on_gpu(data):
    with gpu.allocate(device_id=0, memory_fraction=0.8) as device:
        print(f"Training on {device.name}")
        model = build_model()
        model.to(device.torch_device)
        trained = train(model, data)
    return trained

# Batch across multiple GPUs
results = gpu.distribute(
    fn=train_variant,
    inputs=[config_a, config_b, config_c],
    devices=[0, 1],
)
print(f"✅ Trained {len(results)} model variants")`,
  },
  {
    id: 'fml-smart-cache',
    name: 'Smart Caching',
    category: 'flowyml-core',
    description: 'Content-based and shared caching for steps',
    tags: ['cache', 'memoize', 'smart', 'performance'],
    builtin: true,
    docs: 'SmartCache auto-detects when inputs change and skips re-execution. @memoize caches function results by arguments.',
    source: `from flowyml import SmartCache, ContentBasedCache, memoize, step

# Smart cache: auto-skips if inputs unchanged
@step(outputs=["data/processed"], cache=SmartCache())
def process_data(raw_df):
    """This step is skipped if raw_df hasn't changed."""
    print("⚙️ Processing data...")
    return raw_df.dropna().drop_duplicates()

# Content-based: caches by data hash, not reference
@step(outputs=["features/extracted"], cache=ContentBasedCache())
def extract_features(df):
    return df.select_dtypes(include="number")

# @memoize for any function
@memoize(ttl_seconds=3600)
def expensive_api_call(query):
    """Cached for 1 hour — avoids redundant API calls."""
    import requests
    return requests.get(f"https://api.example.com/search?q={query}").json()

result = expensive_api_call("flowyml")  # First call hits API
result = expensive_api_call("flowyml")  # ⚡ Returns cached result`,
  },
  {
    id: 'fml-project',
    name: 'Project Manager',
    category: 'flowyml-core',
    description: 'Organize pipelines and assets into projects',
    tags: ['project', 'organization', 'workspace'],
    builtin: true,
    docs: 'Project and ProjectManager let you organize multiple pipelines, experiments, and assets under a single project namespace.',
    source: `from flowyml import Project, ProjectManager

# Create or load a project
pm = ProjectManager()
project = pm.get_or_create("recommendation-engine",
    description="Product recommendation ML pipeline",
    tags=["ml", "recommendations", "production"],
)

# List project contents
print(f"📁 Project: {project.name}")
print(f"   Pipelines: {len(project.pipelines)}")
print(f"   Experiments: {len(project.experiments)}")
print(f"   Assets: {len(project.assets)}")

# Set active project (all new artifacts auto-register here)
project.activate()
print(f"✅ Active project: {project.name}")

# List all projects
for p in pm.list_projects():
    print(f"  📂 {p.name} — {p.description}")`,
  },
  {
    id: 'fml-scorer',
    name: 'Custom Scorer',
    category: 'flowyml-evals',
    description: 'Build custom evaluation scorers and judges',
    tags: ['scorer', 'judge', 'evaluation', 'custom'],
    builtin: true,
    docs: 'make_scorer creates reusable evaluation functions. make_judge creates LLM-based evaluators. get_scorer loads pre-built scorers.',
    source: `from flowyml import make_scorer, make_judge, get_scorer

# Custom scorer function
@make_scorer
def response_quality(output, reference=None, **kwargs):
    """Score response quality on 0-1 scale."""
    score = 0.0
    if len(output) > 50: score += 0.3
    if reference and reference.lower() in output.lower(): score += 0.5
    if "error" not in output.lower(): score += 0.2
    return score

# LLM-based judge
judge = make_judge(
    model="gpt-4",
    criteria=["accuracy", "helpfulness", "conciseness"],
    scale=(1, 5),
)

# Use built-in scorers
bleu = get_scorer("bleu")
rouge = get_scorer("rouge")
toxicity = get_scorer("toxicity")

# Evaluate
result = response_quality("FlowyML is a great framework for ML pipelines.")
print(f"Quality score: {result:.2f}")`,
  },
  {
    id: 'fml-trace-bridge',
    name: 'Trace Bridge (Evals ↔ Traces)',
    category: 'flowyml-evals',
    description: 'Link evaluation results to GenAI execution traces',
    tags: ['trace', 'bridge', 'eval', 'observability'],
    builtin: true,
    docs: 'TraceBridge connects evaluation scores back to GenAI execution traces so you can see exactly which LLM calls led to each score.',
    source: `from flowyml import TraceBridge, evaluate, trace_genai

# Initialize trace bridge
bridge = TraceBridge()

# Run traced LLM calls
@trace_genai("qa_pipeline")
def answer_question(question):
    response = llm.invoke(question)
    return response

# Run evaluation with trace linking
results = evaluate(
    fn=answer_question,
    dataset=eval_dataset,
    scorers=["accuracy", "latency"],
    trace_bridge=bridge,  # Links scores to traces
)

# Now each eval result has linked traces
for r in results:
    print(f"Q: {r.input[:40]}...")
    print(f"  Score: {r.score:.2f}")
    print(f"  Trace: {r.trace_id} ({r.trace_latency_ms}ms)")
    print(f"  Tokens: {r.trace_tokens}")`,
  },
  {
    id: 'fml-eval-schedule',
    name: 'Scheduled Evaluations',
    category: 'flowyml-evals',
    description: 'Run evaluations on a schedule for continuous monitoring',
    tags: ['schedule', 'eval', 'continuous', 'monitoring'],
    builtin: true,
    docs: 'EvalSchedule runs your evaluation suites on a cron schedule and alerts you when scores drop below thresholds.',
    source: `from flowyml import EvalSchedule, EvalSuite, configure_notifications

# Define eval suite
suite = EvalSuite("production_checks", cases=[
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Capital of France?", "expected": "Paris"},
])

# Schedule to run every 6 hours
schedule = EvalSchedule(
    name="prod_eval_monitor",
    suite=suite,
    model_fn=lambda x: production_model.predict(x),
    cron="0 */6 * * *",
    alert_threshold=0.8,  # Alert if score drops below 80%
)

schedule.enable()
print(f"⏰ Eval schedule active: {schedule.cron}")
print(f"   Alert threshold: {schedule.alert_threshold}")

# Check last results
last_run = schedule.last_result()
if last_run:
    print(f"   Last score: {last_run.score:.2%}")
    print(f"   Last run: {last_run.timestamp}")`,
  },
  {
    id: 'fml-generic-span',
    name: 'Custom Observability Span',
    category: 'flowyml-observe',
    description: 'Wrap any code block in a named observability span',
    tags: ['span', 'observability', 'tracing', 'custom'],
    builtin: true,
    docs: 'The @span decorator wraps any function in a named trace span, giving you fine-grained observability over custom code sections.',
    source: `from flowyml import span

# Decorator style
@span("data_preprocessing")
def preprocess(df):
    """This function is tracked as a named span."""
    df = df.dropna()
    df = df.drop_duplicates()
    return df

# Context manager style
from flowyml import trace_genai

@trace_genai("recommendation_pipeline")
def get_recommendations(user_id):
    with span("fetch_user_profile"):
        profile = db.get_user(user_id)

    with span("generate_candidates"):
        candidates = model.predict(profile)

    with span("rerank_results"):
        ranked = reranker.score(candidates)

    return ranked[:10]

results = get_recommendations("user_123")
print(f"✅ {len(results)} recommendations generated")`,
  },
  // ═══════════════════════════════════════
  //  DATA PREP
  // ═══════════════════════════════════════
  {
    id: 'load-csv',
    name: 'Load CSV',
    category: 'data-prep',
    description: 'Load a CSV file into a pandas DataFrame',
    tags: ['pandas', 'csv', 'import'],
    builtin: true,
    source: `import pandas as pd

df = pd.read_csv("data.csv")

print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Dtypes:\\n{df.dtypes}")
print(f"\\nMissing values:\\n{df.isnull().sum()}")
df.head()`,
  },
  {
    id: 'data-cleaning',
    name: 'Data Cleaning',
    category: 'data-prep',
    description: 'Clean and preprocess a DataFrame',
    tags: ['cleaning', 'preprocessing', 'missing'],
    builtin: true,
    source: `# Data Cleaning Pipeline
df = df.drop_duplicates()

# Handle missing values
print(f"Missing values:\\n{df.isnull().sum()}")
df = df.dropna(subset=["important_column"])
df = df.fillna({"numeric_col": df["numeric_col"].median()})

# Fix data types
# df["date_col"] = pd.to_datetime(df["date_col"])
# df["category_col"] = df["category_col"].astype("category")

print(f"✅ Clean shape: {df.shape}")
df.head()`,
  },
  {
    id: 'feature-engineering',
    name: 'Feature Engineering',
    category: 'data-prep',
    description: 'Create and transform features for ML',
    tags: ['features', 'encoding', 'scaling'],
    builtin: true,
    source: `from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np

# Numeric features - scaling
scaler = StandardScaler()
numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

# Categorical features - encoding
le = LabelEncoder()
# df["encoded_col"] = le.fit_transform(df["category_col"])

# Create new features
# df["feature_ratio"] = df["col_a"] / df["col_b"]
# df["feature_log"] = np.log1p(df["numeric_col"])

df.head()`,
  },
  // ═══════════════════════════════════════
  //  ML / MODELS
  // ═══════════════════════════════════════
  {
    id: 'train-test-split',
    name: 'Train/Test Split',
    category: 'ml',
    description: 'Split data into training and test sets',
    tags: ['split', 'train', 'test', 'validation'],
    builtin: true,
    source: `from sklearn.model_selection import train_test_split

X = df.drop(columns=["target"])
y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {X_train.shape}, Test: {X_test.shape}")`,
  },
  {
    id: 'model-training',
    name: 'Model Training',
    category: 'ml',
    description: 'Train and evaluate an ML model',
    tags: ['sklearn', 'training', 'classification'],
    builtin: true,
    source: `from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"\\n{classification_report(y_test, y_pred)}")`,
  },
  {
    id: 'hyperparameter-tuning',
    name: 'Hyperparameter Tuning',
    category: 'ml',
    description: 'Grid/Random search for optimal hyperparameters',
    tags: ['tuning', 'grid-search', 'optimization'],
    builtin: true,
    source: `from sklearn.model_selection import RandomizedSearchCV
from sklearn.ensemble import GradientBoostingClassifier

param_dist = {
    "n_estimators": [50, 100, 200, 500],
    "max_depth": [3, 5, 7, 10, None],
    "learning_rate": [0.01, 0.05, 0.1, 0.2],
    "subsample": [0.6, 0.8, 1.0],
}

search = RandomizedSearchCV(
    GradientBoostingClassifier(),
    param_dist,
    n_iter=20,
    cv=5,
    scoring="f1_weighted",
    random_state=42,
    n_jobs=-1,
)

search.fit(X_train, y_train)
print(f"🏆 Best F1: {search.best_score_:.4f}")
print(f"📊 Best params: {search.best_params_}")`,
  },
  // ═══════════════════════════════════════
  //  VISUALIZATION
  // ═══════════════════════════════════════
  {
    id: 'plot-distribution',
    name: 'Distribution Plots',
    category: 'viz',
    description: 'Visualize data distributions with histograms',
    tags: ['matplotlib', 'histogram', 'distribution'],
    builtin: true,
    source: `import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle("Data Distributions", fontsize=14, fontweight="bold")

numeric_cols = df.select_dtypes(include="number").columns[:4]
for ax, col in zip(axes.flatten(), numeric_cols):
    sns.histplot(df[col], kde=True, ax=ax, color="#6366f1")
    ax.set_title(col, fontsize=11)
    ax.set_xlabel("")

plt.tight_layout()
plt.show()`,
  },
  {
    id: 'correlation-heatmap',
    name: 'Correlation Heatmap',
    category: 'viz',
    description: 'Interactive correlation matrix visualization',
    tags: ['correlation', 'heatmap', 'seaborn'],
    builtin: true,
    source: `import matplotlib.pyplot as plt
import seaborn as sns

corr = df.select_dtypes(include="number").corr()

plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, square=True, linewidths=0.5)
plt.title("Feature Correlation Matrix", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.show()`,
  },
  {
    id: 'fml-confusion-matrix',
    name: 'Confusion Matrix',
    category: 'viz',
    description: 'Beautiful confusion matrix visualization',
    tags: ['confusion', 'classification', 'evaluation'],
    builtin: true,
    source: `import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=model.classes_)

fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(ax=ax, cmap="Blues", values_format="d")
ax.set_title("Confusion Matrix", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.show()`,
  },
  {
    id: 'fml-feature-importance',
    name: 'Feature Importance',
    category: 'viz',
    description: 'Visualize model feature importances',
    tags: ['importance', 'features', 'interpretability'],
    builtin: true,
    source: `import matplotlib.pyplot as plt
import pandas as pd

# Get feature importances
importances = pd.Series(
    model.feature_importances_,
    index=X_train.columns,
).sort_values(ascending=True)

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
importances.tail(15).plot(kind="barh", ax=ax, color="#6366f1")
ax.set_title("Top 15 Feature Importances", fontsize=14, fontweight="bold")
ax.set_xlabel("Importance")
plt.tight_layout()
plt.show()`,
  },
  // ═══════════════════════════════════════
  //  PRODUCTION
  // ═══════════════════════════════════════
  {
    id: 'prod-config',
    name: 'Production Config',
    category: 'production',
    description: 'Pydantic settings with env vars and secrets management',
    tags: ['config', 'pydantic', 'env', 'secrets'],
    builtin: true,
    source: `from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr

class AppConfig(BaseSettings):
    """Type-safe configuration with env var support."""
    model_name: str = Field("xgboost_v3", env="MODEL_NAME")
    model_path: str = Field("models/latest.pkl", env="MODEL_PATH")
    api_key: SecretStr = Field(..., env="API_KEY")
    batch_size: int = Field(32, env="BATCH_SIZE")
    max_workers: int = Field(4, env="MAX_WORKERS")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_prefix = "ML_"
        env_file = ".env"

config = AppConfig()
print(f"🔧 Config loaded: model={config.model_name}, batch={config.batch_size}")`,
  },
  {
    id: 'prod-fastapi-serve',
    name: 'Model Serving API',
    category: 'production',
    description: 'FastAPI model serving with health check and metrics',
    tags: ['fastapi', 'serving', 'api', 'deployment'],
    builtin: true,
    source: `from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import time

app = FastAPI(title="ML Model API", version="1.0.0")

# Load model at startup
model = joblib.load("model.pkl")
request_count = 0

class PredictRequest(BaseModel):
    features: list[float]

class PredictResponse(BaseModel):
    prediction: float
    confidence: float
    latency_ms: float

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None, "requests_served": request_count}

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    global request_count
    start = time.perf_counter()
    try:
        pred = model.predict([req.features])[0]
        proba = model.predict_proba([req.features])[0].max()
        request_count += 1
        return PredictResponse(
            prediction=float(pred),
            confidence=float(proba),
            latency_ms=(time.perf_counter() - start) * 1000,
        )
    except Exception as e:
        raise HTTPException(500, str(e))

print("🚀 Run with: uvicorn app:app --host 0.0.0.0 --port 8000")`,
  },
  {
    id: 'prod-docker',
    name: 'Docker Deployment',
    category: 'production',
    description: 'Dockerfile + compose for ML model service',
    tags: ['docker', 'deployment', 'container'],
    builtin: true,
    source: `# Save this as Dockerfile
dockerfile = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
"""

# Save this as docker-compose.yml
compose = """
version: '3.8'
services:
  ml-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=/app/models/latest.pkl
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""

print("🐳 Docker files generated")
print("   Build: docker-compose up --build")`,
  },
  {
    id: 'prod-cicd',
    name: 'CI/CD Pipeline',
    category: 'production',
    description: 'GitHub Actions workflow for model testing and deployment',
    tags: ['cicd', 'github-actions', 'testing', 'automation'],
    builtin: true,
    source: `# Save as .github/workflows/ml-pipeline.yml
workflow = """
name: ML Pipeline
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short

  train:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python train.py
      - uses: actions/upload-artifact@v4
        with: { name: model, path: models/ }

  deploy:
    needs: train
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying model..."
"""

print("⚙️ GitHub Actions workflow generated")
print("   Stages: test → train → deploy")`,
  },
  {
    id: 'prod-monitoring',
    name: 'Model Monitoring',
    category: 'production',
    description: 'Track predictions, latency, and data drift in production',
    tags: ['monitoring', 'metrics', 'prometheus', 'drift'],
    builtin: true,
    source: `import time
import numpy as np
from collections import defaultdict
from datetime import datetime

class ModelMonitor:
    """Production model monitoring with drift detection."""
    
    def __init__(self, baseline_stats=None):
        self.predictions = []
        self.latencies = []
        self.errors = 0
        self.baseline = baseline_stats or {}
        self._feature_stats = defaultdict(list)
    
    def record_prediction(self, features, prediction, latency_ms):
        self.predictions.append({"pred": prediction, "ts": datetime.now().isoformat()})
        self.latencies.append(latency_ms)
        for i, v in enumerate(features):
            self._feature_stats[f"f{i}"].append(v)
    
    def get_metrics(self):
        return {
            "total_predictions": len(self.predictions),
            "avg_latency_ms": np.mean(self.latencies) if self.latencies else 0,
            "p99_latency_ms": np.percentile(self.latencies, 99) if self.latencies else 0,
            "error_rate": self.errors / max(len(self.predictions), 1),
            "prediction_mean": np.mean([p["pred"] for p in self.predictions]) if self.predictions else 0,
        }

monitor = ModelMonitor()
print("📊 Model monitor initialized")
print("   Call monitor.record_prediction(features, pred, latency) after each inference")`,
  },
  {
    id: 'prod-ab-test',
    name: 'A/B Testing Framework',
    category: 'production',
    description: 'Feature flag based experiment framework',
    tags: ['ab-test', 'experiment', 'feature-flag'],
    builtin: true,
    source: `import hashlib
import random
from dataclasses import dataclass, field

@dataclass
class ABExperiment:
    """Simple A/B testing framework for ML models."""
    name: str
    control_model: object = None
    treatment_model: object = None
    traffic_pct: float = 0.5
    results: dict = field(default_factory=lambda: {"control": [], "treatment": []})
    
    def assign_variant(self, user_id: str) -> str:
        hash_val = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        return "treatment" if (hash_val % 100) < (self.traffic_pct * 100) else "control"
    
    def predict(self, user_id: str, features):
        variant = self.assign_variant(user_id)
        model = self.treatment_model if variant == "treatment" else self.control_model
        pred = model.predict([features])[0]
        self.results[variant].append(pred)
        return {"variant": variant, "prediction": pred}
    
    def get_summary(self):
        import numpy as np
        return {
            "control_n": len(self.results["control"]),
            "treatment_n": len(self.results["treatment"]),
            "control_mean": np.mean(self.results["control"]) if self.results["control"] else 0,
            "treatment_mean": np.mean(self.results["treatment"]) if self.results["treatment"] else 0,
        }

experiment = ABExperiment(name="model_v3_vs_v4", traffic_pct=0.2)
print(f"🧪 A/B Test '{experiment.name}' created (20% traffic to treatment)")`,
  },
  // ═══════════════════════════════════════
  //  NLP
  // ═══════════════════════════════════════
  {
    id: 'nlp-text-classification',
    name: 'Text Classification Pipeline',
    category: 'nlp',
    description: 'Full sklearn text classification with TF-IDF',
    tags: ['classification', 'tfidf', 'sklearn', 'text'],
    builtin: true,
    source: `from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

# Example data
texts = ["Great product!", "Terrible service", "Love it", "Worst experience", "Amazing quality"]
labels = [1, 0, 1, 0, 1]

X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)

# Build pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english")),
    ("clf", LogisticRegression(max_iter=1000, C=1.0)),
])

pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

print("📊 Classification Report:")
print(classification_report(y_test, y_pred, target_names=["Negative", "Positive"]))`,
  },
  {
    id: 'nlp-sentiment',
    name: 'Sentiment Analysis',
    category: 'nlp',
    description: 'VADER sentiment scoring with visualization',
    tags: ['sentiment', 'vader', 'nlp', 'analysis'],
    builtin: true,
    source: `from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import pandas as pd

nltk.download("vader_lexicon", quiet=True)
analyzer = SentimentIntensityAnalyzer()

texts = [
    "This product is absolutely amazing!",
    "Terrible experience, would not recommend.",
    "It's okay, nothing special.",
    "Best purchase I've ever made!",
    "Disappointing quality for the price.",
]

results = []
for text in texts:
    scores = analyzer.polarity_scores(text)
    label = "positive" if scores["compound"] > 0.05 else "negative" if scores["compound"] < -0.05 else "neutral"
    results.append({"text": text[:50], "compound": scores["compound"], "label": label})

df = pd.DataFrame(results)
print("🎭 Sentiment Analysis Results:")
print(df.to_string(index=False))`,
  },
  {
    id: 'nlp-topic-modeling',
    name: 'Topic Modeling (LDA)',
    category: 'nlp',
    description: 'Extract topics from text corpus with LDA',
    tags: ['topics', 'lda', 'unsupervised', 'text-mining'],
    builtin: true,
    source: `from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np

# Your corpus
documents = [
    "Machine learning models need training data",
    "Neural networks learn feature representations",
    "Stock prices fluctuate based on market sentiment",
    "Interest rates affect bond yields",
    "Deep learning requires GPU computing power",
]

vectorizer = CountVectorizer(max_features=1000, stop_words="english")
doc_term_matrix = vectorizer.fit_transform(documents)

n_topics = 2
lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
lda.fit(doc_term_matrix)

feature_names = vectorizer.get_feature_names_out()
print("📚 Discovered Topics:")
for idx, topic in enumerate(lda.components_):
    top_words = [feature_names[i] for i in topic.argsort()[-5:]]
    print(f"  Topic {idx + 1}: {', '.join(top_words)}")`,
  },
  {
    id: 'nlp-ner',
    name: 'Named Entity Recognition',
    category: 'nlp',
    description: 'Extract named entities with spaCy',
    tags: ['ner', 'spacy', 'entities', 'extraction'],
    builtin: true,
    source: `import spacy

nlp = spacy.load("en_core_web_sm")

text = """Apple Inc. was founded by Steve Jobs in Cupertino, California.
The company reported $394 billion in revenue for 2022.
Tim Cook serves as the CEO since August 2011."""

doc = nlp(text)

print("🏷️ Named Entities:")
for ent in doc.ents:
    print(f"  {ent.text:25s} → {ent.label_:10s} ({spacy.explain(ent.label_)})")

# Group by entity type
from collections import defaultdict
entities = defaultdict(list)
for ent in doc.ents:
    entities[ent.label_].append(ent.text)

print("\\n📊 Summary:")
for label, ents in entities.items():
    print(f"  {label}: {', '.join(set(ents))}")`,
  },
  {
    id: 'nlp-embeddings',
    name: 'Text Embeddings & Similarity',
    category: 'nlp',
    description: 'Sentence embeddings for semantic similarity',
    tags: ['embeddings', 'similarity', 'sentence-transformers'],
    builtin: true,
    source: `from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

sentences = [
    "Machine learning is a subset of artificial intelligence",
    "AI systems can learn from data",
    "The weather is sunny today",
    "Deep learning uses neural networks",
    "It will rain tomorrow",
]

# TF-IDF based similarity (no GPU required)
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(sentences)
similarity = cosine_similarity(tfidf_matrix)

print("🔗 Semantic Similarity Matrix:")
for i, s1 in enumerate(sentences):
    most_similar = np.argsort(similarity[i])[-2]  # Skip self
    print(f"  '{s1[:40]}...'")
    print(f"    → Most similar: '{sentences[most_similar][:40]}...' (score: {similarity[i][most_similar]:.3f})")`,
  },
  // ═══════════════════════════════════════
  //  TIME SERIES
  // ═══════════════════════════════════════
  {
    id: 'ts-decompose',
    name: 'Seasonal Decomposition',
    category: 'time-series',
    description: 'STL decomposition with trend, seasonal, and residual components',
    tags: ['decomposition', 'seasonal', 'trend', 'statsmodels'],
    builtin: true,
    source: `import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose
import matplotlib.pyplot as plt

# Generate sample time series
np.random.seed(42)
dates = pd.date_range("2023-01-01", periods=365, freq="D")
trend = np.linspace(100, 150, 365)
seasonal = 10 * np.sin(2 * np.pi * np.arange(365) / 365)
noise = np.random.normal(0, 3, 365)
ts = pd.Series(trend + seasonal + noise, index=dates, name="value")

# Decompose
result = seasonal_decompose(ts, model="additive", period=30)

fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
result.observed.plot(ax=axes[0], title="Observed")
result.trend.plot(ax=axes[1], title="Trend")
result.seasonal.plot(ax=axes[2], title="Seasonal")
result.resid.plot(ax=axes[3], title="Residual")
plt.tight_layout()
plt.show()`,
  },
  {
    id: 'ts-arima',
    name: 'ARIMA Forecast',
    category: 'time-series',
    description: 'Auto ARIMA model selection and forecasting',
    tags: ['arima', 'forecast', 'statsmodels', 'prediction'],
    builtin: true,
    source: `import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
import matplotlib.pyplot as plt

# Generate sample data
np.random.seed(42)
dates = pd.date_range("2023-01-01", periods=200, freq="D")
values = np.cumsum(np.random.randn(200)) + 100
ts = pd.Series(values, index=dates)

# Stationarity test
adf = adfuller(ts)
print(f"📊 ADF Statistic: {adf[0]:.4f}")
print(f"   p-value: {adf[1]:.4f}")
print(f"   Stationary: {'Yes ✅' if adf[1] < 0.05 else 'No ❌ (differencing needed)'}")

# Fit ARIMA
model = ARIMA(ts, order=(2, 1, 2))
fitted = model.fit()
print(f"\\n📈 Model: ARIMA(2,1,2)")
print(f"   AIC: {fitted.aic:.2f}")

# Forecast
forecast = fitted.forecast(steps=30)

fig, ax = plt.subplots(figsize=(12, 5))
ts.plot(ax=ax, label="Observed")
forecast.plot(ax=ax, label="Forecast (30d)", color="red", linestyle="--")
ax.set_title("ARIMA Forecast", fontsize=14, fontweight="bold")
ax.legend()
plt.tight_layout()
plt.show()`,
  },
  {
    id: 'ts-anomaly',
    name: 'Anomaly Detection',
    category: 'time-series',
    description: 'Isolation Forest for time series anomaly detection',
    tags: ['anomaly', 'isolation-forest', 'outlier', 'detection'],
    builtin: true,
    source: `import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt

# Generate time series with anomalies
np.random.seed(42)
n = 300
dates = pd.date_range("2023-01-01", periods=n, freq="D")
normal = np.sin(2 * np.pi * np.arange(n) / 30) * 10 + 50 + np.random.normal(0, 2, n)

# Inject anomalies
anomaly_idx = [50, 120, 200, 250]
normal[anomaly_idx] += np.array([30, -25, 35, -30])

df = pd.DataFrame({"date": dates, "value": normal})

# Create features for Isolation Forest
df["rolling_mean"] = df["value"].rolling(7).mean()
df["rolling_std"] = df["value"].rolling(7).std()
df["diff"] = df["value"].diff()
features = df[["value", "rolling_mean", "rolling_std", "diff"]].dropna()

# Detect anomalies
iso_forest = IsolationForest(contamination=0.02, random_state=42)
df.loc[features.index, "anomaly"] = iso_forest.fit_predict(features)

anomalies = df[df["anomaly"] == -1]
print(f"🔍 Detected {len(anomalies)} anomalies")

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(df["date"], df["value"], label="Normal", alpha=0.7)
ax.scatter(anomalies["date"], anomalies["value"], color="red", s=100, zorder=5, label="Anomaly")
ax.set_title("Time Series Anomaly Detection", fontsize=14, fontweight="bold")
ax.legend()
plt.tight_layout()
plt.show()`,
  },
  {
    id: 'ts-rolling-features',
    name: 'Rolling Feature Engineering',
    category: 'time-series',
    description: 'Create rolling window features for ML models',
    tags: ['features', 'rolling', 'engineering', 'lag'],
    builtin: true,
    source: `import pandas as pd
import numpy as np

# Sample time series
np.random.seed(42)
df = pd.DataFrame({
    "date": pd.date_range("2023-01-01", periods=365, freq="D"),
    "value": np.cumsum(np.random.randn(365)) + 100,
})

# Rolling features
for window in [7, 14, 30]:
    df[f"rolling_mean_{window}d"] = df["value"].rolling(window).mean()
    df[f"rolling_std_{window}d"] = df["value"].rolling(window).std()
    df[f"rolling_min_{window}d"] = df["value"].rolling(window).min()
    df[f"rolling_max_{window}d"] = df["value"].rolling(window).max()

# Lag features
for lag in [1, 7, 14]:
    df[f"lag_{lag}d"] = df["value"].shift(lag)

# Rate of change
df["pct_change_1d"] = df["value"].pct_change()
df["pct_change_7d"] = df["value"].pct_change(7)

# Expanding features
df["expanding_mean"] = df["value"].expanding().mean()
df["expanding_std"] = df["value"].expanding().std()

print(f"📊 Generated {len(df.columns) - 2} features from 1 time series")
print(f"   Columns: {list(df.columns[2:])}")
df.dropna(inplace=True)
print(f"   Final shape: {df.shape}")`,
  },
  {
    id: 'ts-prophet',
    name: 'Prophet Forecast',
    category: 'time-series',
    description: 'Facebook Prophet quick forecast with holidays',
    tags: ['prophet', 'forecast', 'facebook', 'holidays'],
    builtin: true,
    source: `import pandas as pd
import numpy as np

# Generate sample data in Prophet format
np.random.seed(42)
df = pd.DataFrame({
    "ds": pd.date_range("2022-01-01", periods=365, freq="D"),
    "y": np.sin(2 * np.pi * np.arange(365) / 365) * 20 + 100 + np.random.normal(0, 5, 365) + np.linspace(0, 30, 365),
})

from prophet import Prophet

model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,
)
model.fit(df)

# Forecast 90 days ahead
future = model.make_future_dataframe(periods=90)
forecast = model.predict(future)

fig = model.plot(forecast)
fig.suptitle("Prophet Forecast", fontsize=14, fontweight="bold")

# Component plots
fig2 = model.plot_components(forecast)

print(f"📈 Forecast generated: {len(forecast)} data points")
print(f"   Trend: {forecast['trend'].iloc[-1]:.1f}")`,
  },
  // ═══════════════════════════════════════
  //  DEEP LEARNING
  // ═══════════════════════════════════════
  {
    id: 'dl-pytorch-training',
    name: 'PyTorch Training Loop',
    category: 'deep-learning',
    description: 'Complete PyTorch training with validation and checkpointing',
    tags: ['pytorch', 'training', 'neural-network', 'gpu'],
    builtin: true,
    source: `import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Simple model
class Net(nn.Module):
    def __init__(self, input_dim, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(hidden, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, 1), nn.Sigmoid(),
        )
    def forward(self, x):
        return self.net(x)

# Setup
device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
model = Net(input_dim=10).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.BCELoss()

# Training loop
for epoch in range(10):
    model.train()
    train_loss = 0
    # for batch_x, batch_y in train_loader:
    #     batch_x, batch_y = batch_x.to(device), batch_y.to(device)
    #     optimizer.zero_grad()
    #     loss = criterion(model(batch_x).squeeze(), batch_y)
    #     loss.backward()
    #     optimizer.step()
    #     train_loss += loss.item()
    print(f"Epoch {epoch+1}/10 — device: {device}")

print(f"🧠 Model: {sum(p.numel() for p in model.parameters()):,} params on {device}")`,
  },
  {
    id: 'dl-transfer-learning',
    name: 'Transfer Learning',
    category: 'deep-learning',
    description: 'Fine-tune pretrained ResNet for custom classification',
    tags: ['transfer-learning', 'resnet', 'fine-tune', 'pretrained'],
    builtin: true,
    source: `import keras
from keras import layers

# Load pretrained ResNet50 (without top classification layer)
base_model = keras.applications.ResNet50(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3),
)

# Freeze base model
base_model.trainable = False

# Add custom classification head
model = keras.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.3),
    layers.Dense(256, activation="relu"),
    layers.Dropout(0.2),
    layers.Dense(10, activation="softmax"),  # 10 classes
])

model.compile(
    optimizer=keras.optimizers.Adam(1e-4),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

print(f"🧠 Transfer Learning Model:")
print(f"   Base: ResNet50 ({base_model.count_params():,} params, frozen)")
print(f"   Total: {model.count_params():,} params")
print(f"   Trainable: {sum(p.numpy().size for p in model.trainable_weights):,} params")`,
  },
  {
    id: 'dl-hyperopt',
    name: 'Hyperparameter Tuning (Optuna)',
    category: 'deep-learning',
    description: 'Optuna-based hyperparameter optimization',
    tags: ['optuna', 'hyperparameter', 'tuning', 'optimization'],
    builtin: true,
    source: `import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import numpy as np

def objective(trial):
    """Optuna objective function."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 20),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
    }
    
    model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy")
    return scores.mean()

# Run optimization
study = optuna.create_study(direction="maximize", study_name="rf_tuning")
study.optimize(objective, n_trials=50, show_progress_bar=True)

print(f"🏆 Best trial:")
print(f"   Accuracy: {study.best_value:.4f}")
print(f"   Params: {study.best_params}")`,
  },
  {
    id: 'dl-explainability',
    name: 'Model Explainability (SHAP)',
    category: 'deep-learning',
    description: 'SHAP values for model interpretability',
    tags: ['shap', 'explainability', 'interpretability', 'xai'],
    builtin: true,
    source: `import shap
import matplotlib.pyplot as plt

# Assuming model and X_test are defined
explainer = shap.TreeExplainer(model)  # For tree-based models
shap_values = explainer.shap_values(X_test)

# Summary plot — feature importance
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, X_test, show=False)
plt.title("SHAP Feature Importance", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.show()

# Waterfall plot for a single prediction
plt.figure(figsize=(10, 6))
shap.plots.waterfall(shap.Explanation(
    values=shap_values[0],
    base_values=explainer.expected_value,
    data=X_test.iloc[0],
    feature_names=X_test.columns.tolist(),
), show=False)
plt.title("SHAP Explanation — Single Prediction")
plt.tight_layout()
plt.show()

print(f"📊 Top 5 important features:")
importance = abs(shap_values).mean(axis=0)
for idx in importance.argsort()[-5:][::-1]:
    print(f"   {X_test.columns[idx]}: {importance[idx]:.4f}")`,
  },
  {
    id: 'dl-gpu-check',
    name: 'GPU & Device Check',
    category: 'deep-learning',
    description: 'Check CUDA/MPS availability and system resources',
    tags: ['gpu', 'cuda', 'mps', 'device', 'hardware'],
    builtin: true,
    source: `import sys
import platform

print("🖥️ System Info:")
print(f"   Python: {sys.version.split()[0]}")
print(f"   Platform: {platform.platform()}")
print(f"   Arch: {platform.machine()}")

# PyTorch
try:
    import torch
    print(f"\\n🔥 PyTorch: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
    print(f"   MPS available: {torch.backends.mps.is_available()}")
except ImportError:
    print("\\n⚠️ PyTorch not installed")

# Keras/TensorFlow
try:
    import keras
    print(f"\\n🧠 Keras: {keras.__version__}")
    devices = keras.distribution.list_devices()
    print(f"   Devices: {devices}")
except ImportError:
    print("\\n⚠️ Keras not installed")

# Check available memory
import os
try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"\\n💾 RAM: {mem.total / 1e9:.1f} GB total, {mem.available / 1e9:.1f} GB available")
except ImportError:
    pass`,
  },
  // ═══════════════════════════════════════
  //  DATA ENGINEERING
  // ═══════════════════════════════════════
  {
    id: 'de-etl-pipeline',
    name: 'ETL Pipeline',
    category: 'data-engineering',
    description: 'Extract/Transform/Load pipeline with error handling',
    tags: ['etl', 'pipeline', 'data-engineering'],
    builtin: true,
    source: `import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("etl")

class ETLPipeline:
    def __init__(self, name):
        self.name = name
        self.stats = {"extracted": 0, "transformed": 0, "loaded": 0, "errors": 0}
    
    def extract(self, source: str) -> pd.DataFrame:
        log.info(f"📥 Extracting from {source}")
        df = pd.read_csv(source)
        self.stats["extracted"] = len(df)
        return df
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        log.info(f"🔄 Transforming {len(df)} rows")
        df = df.dropna().drop_duplicates()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        self.stats["transformed"] = len(df)
        return df
    
    def load(self, df: pd.DataFrame, dest: str):
        log.info(f"📤 Loading {len(df)} rows to {dest}")
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(dest, index=False)
        self.stats["loaded"] = len(df)
    
    def run(self, source, dest):
        try:
            df = self.extract(source)
            df = self.transform(df)
            self.load(df, dest)
            log.info(f"✅ ETL complete: {self.stats}")
        except Exception as e:
            self.stats["errors"] += 1
            log.error(f"❌ ETL failed: {e}")
            raise

pipeline = ETLPipeline("daily_ingest")
print(f"🔧 ETL Pipeline '{pipeline.name}' ready")`,
  },
  {
    id: 'de-data-quality',
    name: 'Data Quality Suite',
    category: 'data-engineering',
    description: 'Great Expectations-style data validation checks',
    tags: ['data-quality', 'validation', 'assertions', 'testing'],
    builtin: true,
    source: `import pandas as pd
import numpy as np

class DataQualityChecker:
    """Simple data quality validation framework."""
    
    def __init__(self, df: pd.DataFrame, name: str = "dataset"):
        self.df = df
        self.name = name
        self.results = []
    
    def expect_no_nulls(self, columns=None):
        cols = columns or self.df.columns
        for col in cols:
            nulls = self.df[col].isnull().sum()
            self.results.append({"check": f"no_nulls({col})", "passed": nulls == 0, "detail": f"{nulls} nulls"})
        return self
    
    def expect_unique(self, column):
        dupes = self.df[column].duplicated().sum()
        self.results.append({"check": f"unique({column})", "passed": dupes == 0, "detail": f"{dupes} duplicates"})
        return self
    
    def expect_values_in(self, column, allowed):
        invalid = ~self.df[column].isin(allowed)
        self.results.append({"check": f"values_in({column})", "passed": invalid.sum() == 0, "detail": f"{invalid.sum()} invalid"})
        return self
    
    def expect_range(self, column, min_val=None, max_val=None):
        violations = 0
        if min_val is not None: violations += (self.df[column] < min_val).sum()
        if max_val is not None: violations += (self.df[column] > max_val).sum()
        self.results.append({"check": f"range({column}, {min_val}-{max_val})", "passed": violations == 0, "detail": f"{violations} violations"})
        return self
    
    def report(self):
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"\\n📊 Data Quality Report: {self.name}")
        print(f"   {'✅' if passed == total else '⚠️'} {passed}/{total} checks passed\\n")
        for r in self.results:
            icon = "✅" if r["passed"] else "❌"
            print(f"   {icon} {r['check']}: {r['detail']}")
        return passed == total

# Usage
checker = DataQualityChecker(df, "my_dataset")
checker.expect_no_nulls(["id", "name"]).expect_unique("id").expect_range("age", 0, 120)
all_passed = checker.report()`,
  },
  {
    id: 'de-duckdb',
    name: 'DuckDB Analytics',
    category: 'data-engineering',
    description: 'In-memory SQL analytics with DuckDB',
    tags: ['duckdb', 'sql', 'analytics', 'olap'],
    builtin: true,
    source: `import duckdb
import pandas as pd

# Create in-memory DuckDB connection
con = duckdb.connect()

# Query pandas DataFrames directly with SQL!
df = pd.DataFrame({
    "product": ["A", "B", "A", "C", "B", "A"],
    "revenue": [100, 200, 150, 300, 180, 120],
    "region": ["US", "EU", "US", "EU", "US", "EU"],
})

# SQL analytics on DataFrames
result = con.execute("""
    SELECT 
        product,
        region,
        SUM(revenue) as total_revenue,
        AVG(revenue) as avg_revenue,
        COUNT(*) as orders
    FROM df
    GROUP BY product, region
    ORDER BY total_revenue DESC
""").fetchdf()

print("📊 Revenue by Product & Region:")
print(result.to_string(index=False))

# Window functions
ranked = con.execute("""
    SELECT *, 
        RANK() OVER (PARTITION BY region ORDER BY revenue DESC) as rank
    FROM df
""").fetchdf()
print("\\n🏆 Rankings by Region:")
print(ranked.to_string(index=False))`,
  },
  {
    id: 'de-sqlalchemy',
    name: 'SQLAlchemy Database',
    category: 'data-engineering',
    description: 'Connect to databases with SQLAlchemy and pandas',
    tags: ['sqlalchemy', 'database', 'postgresql', 'mysql'],
    builtin: true,
    source: `from sqlalchemy import create_engine, text
import pandas as pd

# Connection string examples
# PostgreSQL: "postgresql://user:pass@host:5432/dbname"
# MySQL:      "mysql+pymysql://user:pass@host:3306/dbname"
# SQLite:     "sqlite:///local.db"

engine = create_engine("sqlite:///analytics.db", echo=False)

# Read SQL to DataFrame
df = pd.read_sql("SELECT * FROM users LIMIT 1000", engine)
print(f"📊 Loaded {len(df)} rows")

# Write DataFrame to SQL
df.to_sql("users_backup", engine, if_exists="replace", index=False)

# Parameterized queries (safe from SQL injection)
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT * FROM users WHERE age > :min_age AND region = :region"),
        {"min_age": 25, "region": "US"}
    )
    filtered = pd.DataFrame(result.fetchall(), columns=result.keys())
    print(f"   Filtered: {len(filtered)} rows")`,
  },
  {
    id: 'de-schema-evolution',
    name: 'Schema Evolution Handler',
    category: 'data-engineering',
    description: 'Handle schema changes gracefully between data versions',
    tags: ['schema', 'evolution', 'migration', 'compatibility'],
    builtin: true,
    source: `import pandas as pd
from dataclasses import dataclass

@dataclass
class SchemaChange:
    change_type: str  # "added", "removed", "type_changed", "renamed"
    column: str
    detail: str

def detect_schema_changes(old_df: pd.DataFrame, new_df: pd.DataFrame) -> list[SchemaChange]:
    """Detect schema differences between two DataFrames."""
    changes = []
    old_cols = set(old_df.columns)
    new_cols = set(new_df.columns)
    
    for col in new_cols - old_cols:
        changes.append(SchemaChange("added", col, f"New column (dtype: {new_df[col].dtype})"))
    for col in old_cols - new_cols:
        changes.append(SchemaChange("removed", col, f"Column removed (was: {old_df[col].dtype})"))
    for col in old_cols & new_cols:
        if old_df[col].dtype != new_df[col].dtype:
            changes.append(SchemaChange("type_changed", col, f"{old_df[col].dtype} → {new_df[col].dtype}"))
    return changes

def apply_schema_migration(df, changes, defaults=None):
    """Apply schema changes with defaults for new columns."""
    defaults = defaults or {}
    for change in changes:
        if change.change_type == "added" and change.column not in df.columns:
            df[change.column] = defaults.get(change.column, None)
        elif change.change_type == "removed" and change.column in df.columns:
            df = df.drop(columns=[change.column])
    return df

print("🔧 Schema evolution utilities loaded")
print("   Use detect_schema_changes(old_df, new_df) to find differences")
print("   Use apply_schema_migration(df, changes) to migrate data")`,
  },
  // ═══════════════════════════════════════
  //  DATA PREP (expanded)
  // ═══════════════════════════════════════
  {
    id: 'dp-advanced-imputation',
    name: 'Advanced Imputation',
    category: 'data-prep',
    description: 'KNN and iterative imputer comparison',
    tags: ['imputation', 'missing-values', 'knn', 'iterative'],
    builtin: true,
    source: `from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
import pandas as pd
import numpy as np

# Compare imputation strategies
strategies = {
    "Mean": SimpleImputer(strategy="mean"),
    "Median": SimpleImputer(strategy="median"),
    "KNN (k=5)": KNNImputer(n_neighbors=5),
    "Iterative": IterativeImputer(max_iter=10, random_state=42),
}

print(f"📊 Missing values before imputation:")
print(df.isnull().sum()[df.isnull().sum() > 0])

results = {}
for name, imputer in strategies.items():
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    imputed = pd.DataFrame(
        imputer.fit_transform(df[numeric_cols]),
        columns=numeric_cols, index=df.index,
    )
    results[name] = imputed
    print(f"  ✅ {name}: {imputed.isnull().sum().sum()} remaining nulls")`,
  },
  {
    id: 'dp-feature-selection',
    name: 'Feature Selection',
    category: 'data-prep',
    description: 'Mutual information + recursive feature elimination',
    tags: ['feature-selection', 'rfe', 'mutual-info', 'dimensionality'],
    builtin: true,
    source: `from sklearn.feature_selection import mutual_info_classif, RFE, SelectKBest
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import numpy as np

# Mutual Information
mi_scores = mutual_info_classif(X_train, y_train, random_state=42)
mi_ranking = pd.Series(mi_scores, index=X_train.columns).sort_values(ascending=False)

print("📊 Mutual Information Scores:")
for feat, score in mi_ranking.head(10).items():
    bar = "█" * int(score * 50)
    print(f"  {feat:25s} {score:.4f} {bar}")

# Recursive Feature Elimination
model = RandomForestClassifier(n_estimators=100, random_state=42)
rfe = RFE(model, n_features_to_select=10, step=1)
rfe.fit(X_train, y_train)

selected = X_train.columns[rfe.support_].tolist()
print(f"\\n🏆 RFE Selected Features ({len(selected)}):")
for f in selected:
    print(f"  ✅ {f}")`,
  },
  {
    id: 'dp-outlier-treatment',
    name: 'Outlier Treatment',
    category: 'data-prep',
    description: 'IQR, Z-score, and Isolation Forest comparison',
    tags: ['outliers', 'iqr', 'zscore', 'detection'],
    builtin: true,
    source: `import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy import stats

def detect_outliers_iqr(df, column, factor=1.5):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    mask = (df[column] < Q1 - factor * IQR) | (df[column] > Q3 + factor * IQR)
    return mask

def detect_outliers_zscore(df, column, threshold=3):
    z_scores = np.abs(stats.zscore(df[column].dropna()))
    mask = pd.Series(False, index=df.index)
    mask[df[column].dropna().index] = z_scores > threshold
    return mask

# Compare methods on numeric columns
for col in df.select_dtypes(include=[np.number]).columns:
    iqr_out = detect_outliers_iqr(df, col).sum()
    z_out = detect_outliers_zscore(df, col).sum()
    print(f"  {col:20s} IQR: {iqr_out:4d} outliers | Z-score: {z_out:4d} outliers")

# Isolation Forest (multivariate)
iso = IsolationForest(contamination=0.05, random_state=42)
numeric = df.select_dtypes(include=[np.number]).dropna()
iso_labels = iso.fit_predict(numeric)
print(f"\\n🔍 Isolation Forest: {(iso_labels == -1).sum()} multivariate outliers")`,
  },
  {
    id: 'dp-smote',
    name: 'Imbalanced Data (SMOTE)',
    category: 'data-prep',
    description: 'SMOTE + random oversampling for class imbalance',
    tags: ['smote', 'imbalanced', 'oversampling', 'augmentation'],
    builtin: true,
    source: `from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from collections import Counter
import pandas as pd

print(f"📊 Original class distribution:")
print(f"   {dict(Counter(y_train))}")

# SMOTE — Synthetic Minority Oversampling
smote = SMOTE(random_state=42)
X_smote, y_smote = smote.fit_resample(X_train, y_train)
print(f"\\n🔄 After SMOTE:")
print(f"   {dict(Counter(y_smote))} ({len(X_smote)} samples)")

# Random Oversampling
ros = RandomOverSampler(random_state=42)
X_ros, y_ros = ros.fit_resample(X_train, y_train)
print(f"\\n🎲 After Random Oversampling:")
print(f"   {dict(Counter(y_ros))} ({len(X_ros)} samples)")

# Combination: SMOTE + Undersampling
from imblearn.combine import SMOTETomek
smt = SMOTETomek(random_state=42)
X_combined, y_combined = smt.fit_resample(X_train, y_train)
print(f"\\n⚖️ After SMOTE + Tomek:")
print(f"   {dict(Counter(y_combined))} ({len(X_combined)} samples)")`,
  },
];

function RecipeCard({ recipe, onInsert, onEdit, onDelete, onToggleFavorite, onShare, isFavorite, usageCount }) {
  const [expanded, setExpanded] = useState(false);
  const [ratingHover, setRatingHover] = useState(0);
  const cat = CATEGORIES.find(c => c.id === recipe.category) || CATEGORIES[4];
  const CatIcon = cat.icon;

  const handleDragStart = (e) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'recipe',
      source: recipe.source,
      name: recipe.name,
      cellType: 'code',
    }));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleRate = async (score) => {
    try {
      await fetch(`/api/recipes/${recipe.id}/rate?rating=${score}`, { method: 'POST' });
    } catch (e) { console.error('Rate failed', e); }
  };

  const handleFork = async () => {
    try {
      const res = await fetch(`/api/recipes/${recipe.id}/fork`, { method: 'POST' });
      const data = await res.json();
      if (data.forked) alert(`Forked as: ${data.name}`);
    } catch (e) { console.error('Fork failed', e); }
  };

  const avgRating = recipe.avg_rating || 0;
  const totalRatings = recipe.ratings ? Object.keys(recipe.ratings).length : 0;

  return (
    <div className="recipe-card" draggable onDragStart={handleDragStart}>
      {/* Category color strip */}
      <div className="recipe-card-stripe" style={{ background: cat.color }} />

      <div className="recipe-card-body">
        <div className="recipe-card-header" onClick={() => setExpanded(!expanded)}>
          <div className="recipe-card-left">
            <div className="recipe-icon" style={{ color: cat.color, background: `${cat.color}15` }}>
              <CatIcon size={14} />
            </div>
            <div className="recipe-info">
              <span className="recipe-name">{recipe.name}</span>
              <span className="recipe-desc">{recipe.description}</span>
            </div>
          </div>

          <div className="recipe-card-right">
            {/* Version badge */}
            {recipe.version && recipe.version > 1 && (
              <span style={{
                fontSize: 8, padding: '1px 4px', borderRadius: 4,
                background: 'var(--accent-muted)', color: 'var(--accent)',
                fontWeight: 600,
              }} title={`Version ${recipe.version}`}>
                v{recipe.version}
              </span>
            )}

            {/* Fork count */}
            {recipe.fork_count > 0 && (
              <span style={{
                fontSize: 8, padding: '1px 4px', borderRadius: 4,
                background: 'rgba(168,85,247,0.12)', color: '#a855f7',
                display: 'flex', alignItems: 'center', gap: 2, fontWeight: 600,
              }} title={`${recipe.fork_count} forks`}>
                <GitBranch size={8} /> {recipe.fork_count}
              </span>
            )}

            {/* Usage badge */}
            {usageCount > 0 && (
              <div className="recipe-usage-badge" title={`Used ${usageCount} times`}>
                <TrendingUp size={9} />
                <span>{usageCount}</span>
              </div>
            )}

            {/* Shared indicator */}
            {recipe.shared && (
              <div className="recipe-shared-badge" title={`Shared by ${recipe.shared_by || 'team'}`}>
                <Share2 size={9} />
              </div>
            )}

            <button
              className="recipe-action-btn"
              onClick={(e) => { e.stopPropagation(); onToggleFavorite?.(recipe.id); }}
              title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
            >
              {isFavorite ? <Star size={11} fill="var(--warning)" color="var(--warning)" /> : <StarOff size={11} />}
            </button>
            <button
              className="recipe-action-btn insert"
              onClick={(e) => { e.stopPropagation(); onInsert?.(recipe); }}
              title="Insert into notebook"
            >
              <Plus size={11} />
            </button>
          </div>
        </div>

        {/* Forked-from attribution */}
        {recipe.forked_from && (
          <div style={{
            fontSize: 9, padding: '2px 8px', color: 'var(--fg-tertiary)',
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <GitBranch size={9} style={{ color: '#a855f7' }} />
            Forked from <span style={{ fontWeight: 600, color: 'var(--fg-secondary)' }}>{recipe.forked_from.name}</span>
            {recipe.forked_from.author && <span> by {recipe.forked_from.author}</span>}
          </div>
        )}

        {/* Tags */}
        {recipe.tags && recipe.tags.length > 0 && (
          <div className="recipe-tags">
            {recipe.tags.map(tag => (
              <span key={tag} className="recipe-tag">{tag}</span>
            ))}
          </div>
        )}

        {/* Star rating (for shared recipes) */}
        {recipe.shared && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px',
            fontSize: 10, color: 'var(--fg-secondary)',
          }}>
            {[1, 2, 3, 4, 5].map(s => (
              <button
                key={s}
                onClick={(e) => { e.stopPropagation(); handleRate(s); }}
                onMouseEnter={() => setRatingHover(s)}
                onMouseLeave={() => setRatingHover(0)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: 0, fontSize: 12, lineHeight: 1,
                  color: s <= (ratingHover || avgRating) ? '#fbbf24' : 'var(--fg-dim)',
                }}
              >
                ★
              </button>
            ))}
            {totalRatings > 0 && (
              <span style={{ fontSize: 9, color: 'var(--fg-tertiary)', marginLeft: 2 }}>
                {avgRating.toFixed(1)} ({totalRatings})
              </span>
            )}
          </div>
        )}

        {/* Expanded preview */}
        {expanded && (
          <div className="recipe-preview">
            <pre className="recipe-code">
              <code dangerouslySetInnerHTML={{ __html: highlightPython(recipe.source) }} />
            </pre>
            <div className="recipe-preview-actions">
              <button className="recipe-insert-btn" onClick={() => onInsert?.(recipe)}>
                <Plus size={10} /> Insert Cell
              </button>
              <button className="recipe-copy-btn" onClick={() => navigator.clipboard.writeText(recipe.source)}>
                <Copy size={10} /> Copy
              </button>
              {/* Fork button (for shared recipes) */}
              {recipe.shared && (
                <button className="recipe-edit-btn" onClick={(e) => { e.stopPropagation(); handleFork(); }}>
                  <GitBranch size={10} /> Fork
                </button>
              )}
              {!recipe.builtin && (
                <>
                  <button className="recipe-edit-btn" onClick={() => onEdit?.(recipe)}>
                    <Edit3 size={10} /> Edit
                  </button>
                  {onShare && (
                    <button className="recipe-share-btn" onClick={() => onShare?.(recipe.id)}>
                      <Share2 size={10} /> Share
                    </button>
                  )}
                  <button className="recipe-delete-btn" onClick={() => onDelete?.(recipe.id)}>
                    <Trash2 size={10} />
                  </button>
                </>
              )}
            </div>

            {/* Documentation */}
            {recipe.documentation && (
              <div className="recipe-docs">
                <span className="recipe-docs-label">Documentation</span>
                <p>{recipe.documentation}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Drag handle */}
      <div className="recipe-drag-handle">
        <GripVertical size={10} />
      </div>
    </div>
  );
}

/* ── Sort options ────────────────────────────────────────────────── */

const SORT_OPTIONS = [
  { id: 'popular', label: 'Popular', icon: TrendingUp },
  { id: 'name', label: 'A-Z', icon: null },
  { id: 'recent', label: 'Recent', icon: null },
];

export default function CellRecipes({ onInsertRecipe }) {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [sortBy, setSortBy] = useState('popular');
  const [favorites, setFavorites] = useState(() => {
    try { return JSON.parse(localStorage.getItem('fml-recipe-favorites') || '[]'); } catch { return []; }
  });
  const [showCreate, setShowCreate] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState(null);
  const [newRecipe, setNewRecipe] = useState({ name: '', category: 'custom', description: '', tags: '', source: '', documentation: '' });
  const [customRecipes, setCustomRecipes] = useState(() => {
    try { return JSON.parse(localStorage.getItem('fml-custom-recipes') || '[]'); } catch { return []; }
  });
  const [usageCounts, setUsageCounts] = useState(() => {
    try { return JSON.parse(localStorage.getItem('fml-recipe-usage') || '{}'); } catch { return {}; }
  });

  // Load custom recipes and usage from backend
  useEffect(() => {
    fetch('/api/recipes')
      .then(r => r.ok ? r.json() : { recipes: [], usage: {} })
      .then(data => {
        if (data.recipes?.length) {
          setCustomRecipes(data.recipes);
        }
        if (data.usage) {
          setUsageCounts(prev => ({ ...prev, ...data.usage }));
        }
      })
      .catch(() => {});
  }, []);

  // Merge builtin + custom
  const allRecipes = useMemo(() => {
    return [...BUILTIN_RECIPES, ...customRecipes];
  }, [customRecipes]);

  // Filter and sort recipes
  const filteredRecipes = useMemo(() => {
    let result = allRecipes;

    // Category filter
    if (activeCategory === 'favorites') {
      result = result.filter(r => favorites.includes(r.id));
    } else if (activeCategory === 'shared') {
      result = result.filter(r => r.shared);
    } else if (activeCategory !== 'all') {
      result = result.filter(r => r.category === activeCategory);
    }

    // Search filter
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(r =>
        r.name.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        r.tags?.some(t => t.toLowerCase().includes(q))
      );
    }

    // Sort
    if (sortBy === 'popular') {
      result = [...result].sort((a, b) => (usageCounts[b.id] || 0) - (usageCounts[a.id] || 0));
    } else if (sortBy === 'name') {
      result = [...result].sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'recent') {
      result = [...result].sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
    }

    return result;
  }, [allRecipes, activeCategory, search, favorites, sortBy, usageCounts]);

  const toggleFavorite = useCallback((id) => {
    setFavorites(prev => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id];
      localStorage.setItem('fml-recipe-favorites', JSON.stringify(next));
      return next;
    });
  }, []);

  const handleInsert = useCallback((recipe) => {
    // Track usage
    const newUsage = { ...usageCounts, [recipe.id]: (usageCounts[recipe.id] || 0) + 1 };
    setUsageCounts(newUsage);
    localStorage.setItem('fml-recipe-usage', JSON.stringify(newUsage));

    // Track on backend
    fetch(`/api/recipes/${recipe.id}/use`, { method: 'POST' }).catch(() => {});

    if (onInsertRecipe) {
      onInsertRecipe({
        cell_type: 'code',
        source: recipe.source,
        name: recipe.name,
      });
    }
  }, [onInsertRecipe, usageCounts]);

  const handleShare = useCallback(async (recipeId) => {
    try {
      const res = await fetch(`/api/recipes/share/${recipeId}`, { method: 'POST' });
      const data = await res.json();
      if (data.shared) {
        // Could show a toast here
      }
    } catch { /* ignore */ }
  }, []);

  const handleCreate = useCallback(() => {
    const recipe = {
      id: editingRecipe?.id || `custom-${Date.now()}`,
      name: newRecipe.name || 'Untitled Recipe',
      category: newRecipe.category,
      description: newRecipe.description,
      tags: newRecipe.tags.split(',').map(t => t.trim()).filter(Boolean),
      source: newRecipe.source || '# Your code here\n',
      documentation: newRecipe.documentation || '',
      builtin: false,
      updated_at: new Date().toISOString(),
    };

    const updated = editingRecipe
      ? customRecipes.map(r => r.id === editingRecipe.id ? recipe : r)
      : [...customRecipes, recipe];

    setCustomRecipes(updated);
    localStorage.setItem('fml-custom-recipes', JSON.stringify(updated));

    // Save to backend
    fetch('/api/recipes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(recipe),
    }).catch(() => {});

    setNewRecipe({ name: '', category: 'custom', description: '', tags: '', source: '', documentation: '' });
    setEditingRecipe(null);
    setShowCreate(false);
  }, [newRecipe, customRecipes, editingRecipe]);

  const handleEdit = useCallback((recipe) => {
    setNewRecipe({
      name: recipe.name,
      category: recipe.category,
      description: recipe.description || '',
      tags: (recipe.tags || []).join(', '),
      source: recipe.source || '',
      documentation: recipe.documentation || '',
    });
    setEditingRecipe(recipe);
    setShowCreate(true);
  }, []);

  const handleDelete = useCallback((id) => {
    const updated = customRecipes.filter(r => r.id !== id);
    setCustomRecipes(updated);
    localStorage.setItem('fml-custom-recipes', JSON.stringify(updated));
    fetch(`/api/recipes/${id}`, { method: 'DELETE' }).catch(() => {});
  }, [customRecipes]);

  const handleExport = useCallback(async () => {
    const data = JSON.stringify(customRecipes, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'flowyml-recipes.json'; a.click();
    URL.revokeObjectURL(url);
  }, [customRecipes]);

  const handleImport = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const recipes = JSON.parse(text);
        if (Array.isArray(recipes)) {
          const merged = [...customRecipes];
          const existingIds = new Set(merged.map(r => r.id));
          recipes.forEach(r => {
            if (!existingIds.has(r.id)) {
              merged.push(r);
              existingIds.add(r.id);
            }
          });
          setCustomRecipes(merged);
          localStorage.setItem('fml-custom-recipes', JSON.stringify(merged));
          // Sync to backend
          fetch('/api/recipes/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipes, overwrite: false }),
          }).catch(() => {});
        }
      } catch { /* ignore */ }
    };
    input.click();
  }, [customRecipes]);

  return (
    <div className="cell-recipes">
      {/* Search + actions bar */}
      <div className="recipe-search-bar">
        <div className="recipe-search">
          <Search size={11} />
          <input
            placeholder="Search recipes..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="recipe-toolbar">
          <button className="recipe-toolbar-btn" onClick={handleImport} title="Import recipes">
            <Download size={11} />
          </button>
          <button className="recipe-toolbar-btn" onClick={handleExport} title="Export recipes">
            <Upload size={11} />
          </button>
          <button className="recipe-toolbar-btn create" onClick={() => { setEditingRecipe(null); setShowCreate(!showCreate); }} title="Create recipe">
            <Plus size={11} />
          </button>
        </div>
      </div>

      {/* Sort toggle */}
      <div className="recipe-sort-bar">
        {SORT_OPTIONS.map(opt => (
          <button
            key={opt.id}
            className={`recipe-sort-btn ${sortBy === opt.id ? 'active' : ''}`}
            onClick={() => setSortBy(opt.id)}
          >
            {opt.icon && <opt.icon size={9} />}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Category filter */}
      <div className="recipe-categories">
        <button
          className={`recipe-cat-btn ${activeCategory === 'all' ? 'active' : ''}`}
          onClick={() => setActiveCategory('all')}
        >
          All ({allRecipes.length})
        </button>
        <button
          className={`recipe-cat-btn fav ${activeCategory === 'favorites' ? 'active' : ''}`}
          onClick={() => setActiveCategory('favorites')}
        >
          <Star size={9} /> ({favorites.length})
        </button>
        {CATEGORIES.map(cat => {
          const count = allRecipes.filter(r => r.category === cat.id || (cat.id === 'shared' && r.shared)).length;
          if (count === 0 && cat.id !== 'shared') return null;
          const CatIcon = cat.icon;
          return (
            <button
              key={cat.id}
              className={`recipe-cat-btn ${activeCategory === cat.id ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat.id)}
              style={activeCategory === cat.id ? { borderColor: cat.color, color: cat.color } : {}}
            >
              <CatIcon size={9} /> {cat.label.split(' ')[0]} ({count})
            </button>
          );
        })}
      </div>

      {/* Create/Edit recipe form */}
      {showCreate && (
        <div className="recipe-create-form">
          <div className="recipe-form-header">
            <Package size={12} />
            <span>{editingRecipe ? 'Edit Recipe' : 'New Recipe'}</span>
            <button className="btn-icon" onClick={() => { setShowCreate(false); setEditingRecipe(null); }} style={{ marginLeft: 'auto', width: 18, height: 18 }}>
              <X size={10} />
            </button>
          </div>
          <input
            className="recipe-form-input"
            placeholder="Recipe name"
            value={newRecipe.name}
            onChange={e => setNewRecipe(p => ({ ...p, name: e.target.value }))}
          />
          <select
            className="recipe-form-input"
            value={newRecipe.category}
            onChange={e => setNewRecipe(p => ({ ...p, category: e.target.value }))}
          >
            {CATEGORIES.filter(c => c.id !== 'shared').map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
          <input
            className="recipe-form-input"
            placeholder="Description"
            value={newRecipe.description}
            onChange={e => setNewRecipe(p => ({ ...p, description: e.target.value }))}
          />
          <input
            className="recipe-form-input"
            placeholder="Tags (comma-separated)"
            value={newRecipe.tags}
            onChange={e => setNewRecipe(p => ({ ...p, tags: e.target.value }))}
          />
          <textarea
            className="recipe-form-textarea"
            placeholder="# Paste your code here..."
            value={newRecipe.source}
            onChange={e => setNewRecipe(p => ({ ...p, source: e.target.value }))}
            rows={8}
          />
          <textarea
            className="recipe-form-textarea docs"
            placeholder="Documentation (optional markdown)..."
            value={newRecipe.documentation}
            onChange={e => setNewRecipe(p => ({ ...p, documentation: e.target.value }))}
            rows={3}
          />
          <button className="recipe-form-submit" onClick={handleCreate}>
            <Check size={11} /> {editingRecipe ? 'Save Changes' : 'Create Recipe'}
          </button>
        </div>
      )}

      {/* Recipe list */}
      <div className="recipe-list">
        {filteredRecipes.length === 0 ? (
          <div className="recipe-empty">
            <Package size={20} />
            <span>{search ? 'No matching recipes' : 'No recipes in this category'}</span>
            <p>Drag recipes into the notebook or click + to insert</p>
          </div>
        ) : (
          filteredRecipes.map(recipe => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onInsert={handleInsert}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onShare={handleShare}
              onToggleFavorite={toggleFavorite}
              isFavorite={favorites.includes(recipe.id)}
              usageCount={usageCounts[recipe.id] || 0}
            />
          ))
        )}
      </div>

      {/* Leaderboard (shared tab) */}
      {activeCategory === 'shared' && <RecipeLeaderboard />}

      {/* Footer hint */}
      <div className="recipe-hint">
        <GripVertical size={9} />
        <span>Drag recipes into notebook or click + to insert</span>
      </div>
    </div>
  );
}

/**
 * RecipeLeaderboard — Shows top-rated and most-forked recipes.
 */
function RecipeLeaderboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/recipes/leaderboard')
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data || (data.top_rated?.length === 0 && data.most_forked?.length === 0)) {
    return null;
  }

  return (
    <div style={{
      margin: '6px 8px', padding: '8px', borderRadius: 8,
      background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--fg-primary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
        🏆 Recipe Leaderboard
        <span style={{ fontSize: 9, color: 'var(--fg-tertiary)', fontWeight: 400 }}>
          ({data.total_shared} shared)
        </span>
      </div>

      {/* Top Rated */}
      {data.top_rated?.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 9, color: 'var(--accent)', fontWeight: 600, marginBottom: 3 }}>⭐ Top Rated</div>
          {data.top_rated.slice(0, 5).map((r, i) => (
            <div key={r.id} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0',
              fontSize: 10, color: 'var(--fg-secondary)',
            }}>
              <span style={{ width: 12, fontWeight: 700, color: i < 3 ? '#fbbf24' : 'var(--fg-dim)' }}>{i + 1}</span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.name}
              </span>
              <span style={{ fontSize: 9, color: '#fbbf24' }}>★ {r.avg_rating?.toFixed(1)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Most Forked */}
      {data.most_forked?.length > 0 && (
        <div>
          <div style={{ fontSize: 9, color: '#a855f7', fontWeight: 600, marginBottom: 3 }}>🔀 Most Forked</div>
          {data.most_forked.slice(0, 5).map((r, i) => (
            <div key={r.id} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0',
              fontSize: 10, color: 'var(--fg-secondary)',
            }}>
              <span style={{ width: 12, fontWeight: 700, color: i < 3 ? '#a855f7' : 'var(--fg-dim)' }}>{i + 1}</span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.name}
              </span>
              <span style={{ fontSize: 9, color: '#a855f7' }}>{r.fork_count} forks</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
