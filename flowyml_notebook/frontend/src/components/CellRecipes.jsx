import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Package, Search, Plus, Star, StarOff, Download, Upload, Edit3,
  Trash2, Copy, ChevronRight, ChevronDown, Code, Database,
  BarChart2, Zap, Puzzle, GitBranch, GripVertical, X,
  FolderPlus, Tag, Check, ExternalLink, RefreshCw, TrendingUp,
  Share2, Eye
} from 'lucide-react';

// Built-in recipe categories
const CATEGORIES = [
  { id: 'flowyml-core', label: 'Core', icon: Zap, color: 'var(--accent)' },
  { id: 'flowyml-assets', label: 'Assets', icon: Database, color: 'var(--cyan)' },
  { id: 'flowyml-parallel', label: 'Parallel', icon: Zap, color: '#a855f7' },
  { id: 'flowyml-observe', label: 'Observability', icon: Eye, color: '#f59e0b' },
  { id: 'flowyml-evals', label: 'Evals', icon: TrendingUp, color: '#10b981' },
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
