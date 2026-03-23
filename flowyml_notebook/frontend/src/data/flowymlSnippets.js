/**
 * FlowyML Quick-Insert snippet templates.
 * Covers ALL FlowyML features: Steps, Pipelines, Branches, Assets,
 * Parallel, Observability, Evals, Docker, Stacks, Notifications,
 * Drift Detection, Checkpointing, Retry, Serving, and more.
 *
 * EVERY snippet that produces or consumes data uses @step with
 * explicit inputs/outputs for full artifact lineage & DAG formation.
 */

export const FLOWYML_SNIPPETS = [
  // ═══════════════════════════════════════════════════════════════
  //  CORE — Steps, Pipelines, Context, Branches
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-step',
    label: 'Step',
    icon: '⚡',
    shortDesc: '@step with typed I/O for DAG',
    category: 'core',
    name: 'flowyml_step',
    source: `from flowyml import step

@step(
    inputs=["data/raw"],       # ← consumed artifacts (drives DAG edges)
    outputs=["data/processed"],  # ← produced artifacts
    cache=True,
)
def process_data(raw_data):
    """Process and clean input data."""  # TODO: update docstring
    import pandas as pd
    df = pd.DataFrame(raw_data)
    
    # TODO: Add your processing logic
    df = df.dropna()
    df = df.drop_duplicates()
    
    print(f"✅ Processed {len(df)} rows")
    return df`,
  },
  {
    id: 'fml-pipeline',
    label: 'Pipeline',
    icon: '🔗',
    shortDesc: 'Pipeline + context + step chain',
    category: 'core',
    name: 'flowyml_pipeline',
    source: `from flowyml import Pipeline, step, context

# Shared configuration — all steps receive matching params
ctx = context(
    data_path="data.csv",
    learning_rate=0.01,
    epochs=50,
)

# Build & run — steps are resolved in DAG order automatically
pipeline = Pipeline("my_pipeline", context=ctx, version="1.0.0")
# pipeline.add_step(load_data)      # outputs=["data/raw"]
# pipeline.add_step(preprocess)     # inputs=["data/raw"], outputs=["data/clean"]
# pipeline.add_step(train)          # inputs=["data/clean"], outputs=["model/trained"]
# pipeline.add_step(evaluate)       # inputs=["model/trained"], outputs=["metrics/eval"]

# result = pipeline.run()
# print(f"{'✅' if result.success else '❌'} Pipeline {'completed' if result.success else 'failed'}")`,
  },
  {
    id: 'fml-branch',
    label: 'Branch',
    icon: '🔀',
    shortDesc: 'If/Switch control flow',
    category: 'core',
    name: 'flowyml_branch',
    source: `from flowyml import step, If, Switch

@step(inputs=["metrics/eval"], outputs=["deploy/status"])
def deploy_model(metrics):
    print("🚀 Deploying model to production!")
    return {"status": "deployed"}

@step(inputs=["metrics/eval"], outputs=["retrain/status"])
def retrain_model(metrics):
    print("🔄 Model needs retraining")
    return {"status": "retraining"}

def check_accuracy(ctx):
    """Deploy only if accuracy > 0.9"""
    metrics = ctx.steps["evaluate"].outputs["metrics/eval"]
    return metrics.data.get("accuracy", 0) > 0.9

# Add to pipeline:
# pipeline.add_control_flow(
#     If(condition=check_accuracy, then_step=deploy_model, else_step=retrain_model)
# )`,
  },
  {
    id: 'fml-context',
    label: 'Context',
    icon: '🔧',
    shortDesc: 'Shared config params',
    category: 'core',
    name: 'flowyml_context',
    source: `from flowyml import context

ctx = context(
    # Data settings
    data_path="data.csv",
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

print(f"🔧 Context: {len(ctx.__dict__) if hasattr(ctx, '__dict__') else 'N/A'} params configured")`,
  },
  {
    id: 'fml-map-task',
    label: 'Map Task',
    icon: '🗺️',
    shortDesc: 'Fan-out parallel map',
    category: 'core',
    name: 'flowyml_map_task',
    source: `from flowyml import map_task, step

@step(outputs=["data/items"])
def get_items():
    return [{"id": i, "value": i * 10} for i in range(20)]

@map_task(inputs=["data/items"], outputs=["results/processed"])
def process_item(item):
    """Runs on each item in parallel — auto-collected into list."""
    result = item["value"] ** 2
    print(f"  Processed item {item['id']}: {result}")
    return {"id": item["id"], "result": result}`,
  },
  {
    id: 'fml-subpipeline',
    label: 'Sub-Pipeline',
    icon: '📎',
    shortDesc: 'Compose nested pipelines',
    category: 'core',
    name: 'flowyml_subpipeline',
    source: `from flowyml import Pipeline, step, sub_pipeline

# Reusable preprocessing sub-pipeline
preprocessing = Pipeline("preprocessing")

@step(inputs=["data/raw"], outputs=["data/clean"])
def clean(df):
    return df.dropna()

preprocessing.add_step(clean)

# Use in parent pipeline
# main_pipeline.add_step(sub_pipeline(preprocessing, name="preprocess"))`,
  },
  {
    id: 'fml-template',
    label: 'Template',
    icon: '📋',
    shortDesc: 'Pipeline from template',
    category: 'core',
    name: 'flowyml_template',
    source: `from flowyml import create_from_template, list_templates

print("📋 Available templates:", list_templates())

pipeline = create_from_template(
    "etl",
    name="my_etl",
    extractor=lambda: {"raw": "data"},
    transformer=lambda data: {"clean": data},
    loader=lambda data: print(f"Loaded: {data}"),
)

result = pipeline.run()
print(f"✅ ETL pipeline {'completed' if result.success else 'failed'}")`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  ASSETS — Dataset, Model, Metrics, FeatureSet, Report
  //  ★ ALL wrapped in @step with proper artifact I/O for lineage
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-dataset',
    label: 'Dataset',
    icon: '📊',
    shortDesc: 'Step that registers a tracked Dataset',
    category: 'assets',
    name: 'flowyml_dataset',
    source: `from flowyml import step, Dataset
import pandas as pd

@step(
    outputs=["data/my_dataset"],  # ← registered artifact for lineage
)
def create_dataset():
    """Load & register a tracked Dataset artifact."""
    df = pd.read_csv("data.csv")  # TODO: your data source
    
    dataset = Dataset.create(
        data=df.to_dict("records"),
        name="my_dataset",
        properties={
            "source": "data.csv",
            "rows": len(df),
            "columns": list(df.columns),
            "target": "label",  # TODO: update
        },
        tags={"domain": "ml", "version": "1.0"},
    )
    
    print(f"📊 Dataset: {dataset.name} — {len(df)} rows × {len(df.columns)} cols")
    return dataset`,
  },
  {
    id: 'fml-model',
    label: 'Model',
    icon: '🤖',
    shortDesc: 'Step that trains & registers a Model',
    category: 'assets',
    name: 'flowyml_model',
    source: `from flowyml import step, Model

@step(
    inputs=["data/my_dataset"],     # ← consumes dataset artifact
    outputs=["model/trained"],      # ← produces model artifact
)
def train_model(dataset):
    """Train and register a Model artifact."""
    from sklearn.ensemble import RandomForestClassifier
    
    # TODO: Prepare your data
    # X_train, y_train = dataset.to_xy(target="label")
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    # model.fit(X_train, y_train)
    
    model_asset = Model.create(
        data=model,
        name="my_model",
        properties={
            "framework": "sklearn",
            "algorithm": "RandomForest",
            "n_estimators": 100,
        },
    )
    
    print(f"🤖 Model: {model_asset.name} ({model_asset.properties.get('framework')})")
    return model_asset`,
  },
  {
    id: 'fml-metrics',
    label: 'Metrics',
    icon: '📈',
    shortDesc: 'Step that evaluates & logs Metrics',
    category: 'assets',
    name: 'flowyml_metrics',
    source: `from flowyml import step, Metrics

@step(
    inputs=["model/trained", "data/my_dataset"],  # ← needs model + data
    outputs=["metrics/eval"],                      # ← produces metrics artifact
)
def evaluate_model(model, dataset):
    """Evaluate model and register Metrics artifact."""
    from sklearn.metrics import accuracy_score, f1_score
    
    # TODO: Replace with your evaluation
    # y_pred = model.data.predict(X_test)
    
    metrics = Metrics.create(
        data={
            "accuracy": 0.94,   # TODO: float(accuracy_score(y_test, y_pred)),
            "f1_score": 0.91,   # TODO: float(f1_score(y_test, y_pred)),
        },
        name="eval_metrics",
        properties={"dataset": "test_set", "model": "my_model"},
    )
    
    for k, v in metrics.data.items():
        print(f"   📊 {k}: {v:.4f}")
    return metrics`,
  },
  {
    id: 'fml-featureset',
    label: 'FeatureSet',
    icon: '🔩',
    shortDesc: 'Step that engineers & registers Features',
    category: 'assets',
    name: 'flowyml_featureset',
    source: `from flowyml import step, FeatureSet
import pandas as pd

@step(
    inputs=["data/my_dataset"],        # ← consumes raw dataset
    outputs=["features/engineered"],   # ← produces feature artifact
)
def engineer_features(dataset):
    """Create and register a FeatureSet artifact."""
    df = pd.DataFrame(dataset.data if hasattr(dataset, 'data') else dataset)
    
    # TODO: Add your feature engineering
    features_df = pd.DataFrame({
        "user_tenure_days": [120, 30, 365],
        "activity_score": [0.8, 0.2, 0.95],
        "purchase_frequency": [5, 1, 12],
    })
    
    feature_set = FeatureSet.create(
        data=features_df.to_dict("list"),
        name="my_features",
        properties={
            "feature_count": len(features_df.columns),
            "entity": "user",
            "frequency": "daily",
        },
    )
    
    print(f"🔩 FeatureSet: {feature_set.name} — {len(features_df.columns)} features")
    return feature_set`,
  },
  {
    id: 'fml-report',
    label: 'Report',
    icon: '📝',
    shortDesc: 'Step that generates a pipeline Report',
    category: 'assets',
    name: 'flowyml_report',
    source: `from flowyml import step, Report

@step(
    inputs=["metrics/eval", "model/trained"],  # ← needs eval results + model
    outputs=["report/summary"],                 # ← produces report artifact
)
def generate_report(metrics, model):
    """Generate and register a Report artifact."""
    report = Report.create(
        data={
            "title": "Model Training Report",
            "sections": [
                {"heading": "Data Summary", "content": f"Trained on dataset"},
                {"heading": "Performance", "content": f"Accuracy: {metrics.data.get('accuracy', 'N/A')}"},
                {"heading": "Model Info", "content": f"Model: {model.name}"},
                {"heading": "Next Steps", "content": "A/B test in production"},
            ],
        },
        name="training_report",
        properties={"pipeline": "training", "author": "data-team"},
    )
    
    print(f"📝 Report: {report.name}")
    return report`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  EXPERIMENT TRACKING & REGISTRY — wrapped in @step
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-experiment',
    label: 'Experiment',
    icon: '🧪',
    shortDesc: 'Step that logs an Experiment run',
    category: 'tracking',
    name: 'flowyml_experiment',
    source: `from flowyml import step, Experiment

@step(
    inputs=["model/trained", "metrics/eval"],  # ← needs model + metrics
    outputs=["experiment/run"],                 # ← produces experiment artifact
)
def log_experiment(model, metrics):
    """Log an experiment run with metrics and model."""
    experiment = Experiment(name="my_experiment", project="ml-team")
    
    with experiment.run(name="run_v1") as run:
        run.log_params({"lr": 0.1, "epochs": 100, "model": model.name})
        run.log_metrics(metrics.data)
        run.log_artifact("model", model)
    
    print(f"🧪 Experiment logged: {experiment.name}")
    return run`,
  },
  {
    id: 'fml-registry',
    label: 'Registry',
    icon: '📦',
    shortDesc: 'Step that registers model version',
    category: 'tracking',
    name: 'flowyml_registry',
    source: `from flowyml import step, ModelRegistry, ModelStage

@step(
    inputs=["model/trained", "metrics/eval", "experiment/run"],  # ← full lineage
    outputs=["registry/model_v1"],                                # ← registered version
)
def register_model(model, metrics, experiment_run):
    """Register model version in the Model Registry."""
    registry = ModelRegistry()
    
    version = registry.register(
        name="my_model",
        model=model,
        metrics=metrics.data,
        description="Model with engineered features",
    )
    
    # Promote: None → Staging → Production
    registry.transition(
        name="my_model",
        version=version.version,
        stage=ModelStage.STAGING,
    )
    
    print(f"📦 Model registered: v{version.version} [{version.stage}]")
    return version`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  PARALLEL, RETRY, CACHING, CHECKPOINTING
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-parallel',
    label: 'Parallel',
    icon: '⚙️',
    shortDesc: 'Concurrent execution',
    category: 'resilience',
    name: 'flowyml_parallel',
    source: `from flowyml import step, parallel_map, BatchExecutor

@step(
    inputs=["data/my_dataset"],       # ← consumes dataset
    outputs=["results/parallel"],     # ← produces parallel results
)
def parallel_process(dataset):
    """Process data chunks concurrently."""
    data_chunks = dataset.data if hasattr(dataset, 'data') else dataset
    
    def process_chunk(chunk):
        return chunk ** 2
    
    results = parallel_map(process_chunk, data_chunks, max_workers=4)
    print(f"⚙️ Processed {len(results)} results in parallel")
    return results`,
  },
  {
    id: 'fml-retry',
    label: 'Retry',
    icon: '🔄',
    shortDesc: 'Retry + circuit breaker',
    category: 'resilience',
    name: 'flowyml_retry',
    source: `from flowyml import retry, CircuitBreaker, FallbackHandler, step

@retry(max_retries=3, backoff_factor=2.0)
@step(outputs=["data/external"])
def fetch_external_data():
    """Retries up to 3x with exponential backoff."""
    import requests
    resp = requests.get("https://api.example.com/data", timeout=10)
    resp.raise_for_status()
    return resp.json()

# Circuit breaker — stops after N failures
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)

@breaker
def call_ml_service(payload):
    return ml_client.predict(payload)

# Fallback for graceful degradation
fallback = FallbackHandler(
    primary=call_ml_service,
    fallback=lambda x: {"prediction": "default", "confidence": 0.0},
)`,
  },
  {
    id: 'fml-checkpoint',
    label: 'Checkpoint',
    icon: '💾',
    shortDesc: 'Save & resume pipelines',
    category: 'resilience',
    name: 'flowyml_checkpoint',
    source: `from flowyml import checkpoint_enabled_pipeline

pipeline = checkpoint_enabled_pipeline(
    "long_training",
    checkpoint_dir="./checkpoints",
    save_interval=5,  # Save every 5 steps
)

# Add your steps...
# pipeline.add_step(load_data)
# pipeline.add_step(preprocess)
# pipeline.add_step(train)

# Automatically resumes from last checkpoint on failure
result = pipeline.run(resume=True)
print(f"💾 Pipeline {'resumed' if result.resumed else 'started'} — {result.status}")`,
  },
  {
    id: 'fml-cache',
    label: 'Cache',
    icon: '🗄️',
    shortDesc: 'Smart caching strategies',
    category: 'resilience',
    name: 'flowyml_cache',
    source: `from flowyml import step, memoize, SmartCache

# Content-based caching — invalidates when input changes
@step(inputs=["data/raw"], outputs=["data/features"], cache=True)
def compute_features(df):
    """Cached based on df content hash."""
    return expensive_feature_engineering(df)

# Decorator-based memoization with TTL
@memoize(ttl=3600)
def get_model_predictions(model_id, input_data):
    return model.predict(input_data)

# Smart cache — auto-selects strategy
cache = SmartCache(max_size=1000, ttl=3600)
cache.set("my_key", expensive_result)
cached = cache.get("my_key")`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  OBSERVABILITY — Tracing, Drift, Notifications
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-trace',
    label: 'GenAI Trace',
    icon: '🔍',
    shortDesc: 'LLM/GenAI tracing',
    category: 'observe',
    name: 'flowyml_trace',
    source: `from flowyml import step, trace_genai, span

@step(
    inputs=["data/prompts"],       # ← prompt dataset
    outputs=["results/ai_output"], # ← traced AI outputs
)
@trace_genai(name="my_ai_workflow")
def ai_pipeline(prompts):
    """Auto-traces LLM calls within this function."""
    import openai
    results = []
    for prompt in prompts:
        with span("llm_call") as s:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
            )
            s.set_attribute("tokens", response.usage.total_tokens)
            results.append(response.choices[0].message.content)
    return results`,
  },
  {
    id: 'fml-openai',
    label: 'OpenAI Trace',
    icon: '🧠',
    shortDesc: 'Auto-trace OpenAI calls',
    category: 'observe',
    name: 'flowyml_openai_trace',
    source: `from flowyml import patch_openai, TracedOpenAI
import openai

# Monkey-patch for zero-config tracing
patch_openai()

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Explain ML pipelines"}],
)
# All calls automatically tracked with tokens, latency, cost!

# Or use the traced client directly
# traced = TracedOpenAI(experiment="chatbot_v2")`,
  },
  {
    id: 'fml-langchain',
    label: 'LangChain',
    icon: '🦜',
    shortDesc: 'Trace LangChain/LangGraph',
    category: 'observe',
    name: 'flowyml_langchain_trace',
    source: `from flowyml import FlowyMLCallbackHandler, trace_graph, observe

# LangChain — auto-trace with callback
handler = FlowyMLCallbackHandler(experiment="rag_pipeline")
# chain = LLMChain(llm=llm, prompt=prompt_template, callbacks=[handler])

# LangGraph — trace entire graph execution
@trace_graph(name="agent_workflow")
def run_agent(state):
    graph = build_agent_graph()
    return graph.invoke(state)

# Simple decorator for any function
@observe(name="rag_query")
def rag_pipeline(query):
    docs = retriever.get_relevant_documents(query)
    return llm.invoke(docs)`,
  },
  {
    id: 'fml-drift',
    label: 'Drift Detection',
    icon: '📉',
    shortDesc: 'Data drift monitoring',
    category: 'observe',
    name: 'flowyml_drift',
    source: `from flowyml import step, detect_drift, compute_stats

@step(
    inputs=["data/my_dataset"],      # ← reference data
    outputs=["metrics/drift_report"],  # ← drift metrics artifact
)
def check_drift(reference_data):
    """Detect data drift against production data."""
    import pandas as pd
    new_data_df = pd.read_csv("production_data.csv")  # TODO: your source
    reference_df = pd.DataFrame(reference_data.data if hasattr(reference_data, 'data') else reference_data)
    
    drift_report = detect_drift(
        reference=reference_df,
        current=new_data_df,
        features=list(reference_df.columns),
    )
    
    print("🔍 Drift Detection Report:")
    for feature, result in drift_report.items():
        status = "⚠️ DRIFT" if result["drifted"] else "✅ OK"
        print(f"   {feature}: {status} (p={result['p_value']:.4f})")
    return drift_report`,
  },
  {
    id: 'fml-notifications',
    label: 'Notifications',
    icon: '🔔',
    shortDesc: 'Slack/Email/Console alerts',
    category: 'observe',
    name: 'flowyml_notifications',
    source: `from flowyml import configure_notifications, get_notifier

configure_notifications(
    slack_webhook="https://hooks.slack.com/services/...",  # TODO
    email_to="team@company.com",
    email_from="ml-pipelines@company.com",
)

notifier = get_notifier()

notifier.send(
    channel="slack",
    title="🚀 Model Deployed",
    message="churn_predictor v3 → production\\nAccuracy: 94.2%",
    level="success",
)

# Auto-notify on pipeline events:
# pipeline = Pipeline("training", on_complete=notifier.slack, on_failure=notifier.email)`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  GENAI — Prompt Store, RAG, Agent Trace, Token Tracking, Guardrails
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-prompt-store',
    label: 'Prompt Store',
    icon: '💬',
    shortDesc: 'Versioned prompt templates',
    category: 'genai',
    name: 'flowyml_prompt_store',
    source: `from flowyml import step, PromptStore, PromptTemplate

@step(
    outputs=["prompts/my_templates"],  # ← versioned prompt artifact
)
def create_prompts():
    """Create and version prompt templates."""
    store = PromptStore(name="my_prompts", version="1.0")
    
    store.add(PromptTemplate(
        name="summarize",
        template="""Summarize the following text in {style} style:
---
{text}
---
Provide a {length} summary.""",
        variables=["text", "style", "length"],
        metadata={"task": "summarization", "model": "gpt-4"},
    ))
    
    store.add(PromptTemplate(
        name="classify",
        template="Classify this text into one of: {categories}\\n\\nText: {text}",
        variables=["text", "categories"],
        metadata={"task": "classification"},
    ))
    
    print(f"💬 Prompt Store: {store.name} — {len(store.templates)} templates")
    return store`,
  },
  {
    id: 'fml-rag',
    label: 'RAG Pipeline',
    icon: '🔎',
    shortDesc: 'Retrieval-Augmented Generation',
    category: 'genai',
    name: 'flowyml_rag',
    source: `from flowyml import step, RAGPipeline, VectorStore, Embedder

@step(
    inputs=["data/my_dataset"],           # ← source documents
    outputs=["results/rag_responses"],    # ← RAG answers artifact
)
def run_rag(documents):
    """Run a RAG pipeline: embed → retrieve → generate."""
    embedder = Embedder(model="text-embedding-3-small")
    vector_store = VectorStore(embedder=embedder)
    
    # Index documents
    vector_store.add_documents(documents.data if hasattr(documents, 'data') else documents)
    
    # Build RAG pipeline
    rag = RAGPipeline(
        retriever=vector_store.as_retriever(top_k=5),
        generator_model="gpt-4",
        system_prompt="Answer based only on the provided context.",
    )
    
    queries = ["What is the main finding?", "Summarize the methodology"]
    results = [rag.query(q) for q in queries]
    
    for q, r in zip(queries, results):
        print(f"  🔎 Q: {q}")
        print(f"     A: {r.answer[:80]}...")
    return results`,
  },
  {
    id: 'fml-agent-trace',
    label: 'Agent Trace',
    icon: '🤝',
    shortDesc: 'Trace autonomous agent runs',
    category: 'genai',
    name: 'flowyml_agent_trace',
    source: `from flowyml import step, trace_agent, AgentTracer

@step(
    inputs=["prompts/my_templates"],      # ← prompt templates
    outputs=["results/agent_trace"],      # ← agent trace artifact
)
@trace_agent(name="my_agent")
def run_agent(prompts):
    """Trace an autonomous agent with tool calls, reasoning, and actions."""
    tracer = AgentTracer(experiment="agent_v1")
    
    with tracer.trace("research_task") as t:
        # Step 1: Plan
        t.log_thought("I need to research the topic first")
        
        # Step 2: Tool use
        t.log_tool_call("search", {"query": "ML pipeline best practices"})
        t.log_tool_result("search", {"results": ["..."]})
        
        # Step 3: Synthesize
        t.log_thought("Now I'll synthesize the findings")
        answer = "Based on research, best practices include..."
        t.log_output(answer)
    
    print(f"🤝 Agent trace: {tracer.total_steps} steps, {tracer.total_tokens} tokens")
    return tracer.get_trace()`,
  },
  {
    id: 'fml-token-tracker',
    label: 'Token Tracker',
    icon: '🪙',
    shortDesc: 'Track LLM token usage & cost',
    category: 'genai',
    name: 'flowyml_token_tracker',
    source: `from flowyml import step, TokenTracker, CostCalculator

@step(
    inputs=["results/ai_output"],         # ← AI outputs to audit
    outputs=["metrics/token_usage"],       # ← usage metrics artifact
)
def track_tokens(ai_results):
    """Track token consumption and estimate costs."""
    tracker = TokenTracker()
    
    # Register pricing (per 1K tokens)
    calc = CostCalculator({
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    })
    
    summary = tracker.summarize()
    cost = calc.estimate(summary)
    
    print(f"🪙 Token Usage:")
    print(f"   Input:  {summary.get('input_tokens', 0):,} tokens")
    print(f"   Output: {summary.get('output_tokens', 0):,} tokens")
    print("   Cost:   $" + f"{cost:.4f}")
    return {"usage": summary, "cost": cost}`,
  },
  {
    id: 'fml-guardrails',
    label: 'Guardrails',
    icon: '🛡️',
    shortDesc: 'LLM output safety & validation',
    category: 'genai',
    name: 'flowyml_guardrails',
    source: `from flowyml import step, Guardrails, OutputValidator

@step(
    inputs=["results/ai_output"],           # ← raw LLM outputs
    outputs=["results/validated_output"],    # ← validated outputs artifact
)
def apply_guardrails(raw_outputs):
    """Validate and sanitize LLM outputs."""
    guards = Guardrails([
        OutputValidator.no_pii(),           # Block PII leakage
        OutputValidator.no_harmful(),       # Block harmful content
        OutputValidator.json_schema({       # Enforce JSON structure
            "type": "object",
            "required": ["answer", "confidence"],
        }),
        OutputValidator.max_length(2000),   # Length limit
        OutputValidator.no_hallucination(   # Grounding check
            reference_docs=True
        ),
    ])
    
    validated = []
    for output in raw_outputs:
        result = guards.validate(output)
        status = "✅" if result.passed else "❌"
        print(f"   {status} {result.summary}")
        validated.append(result)
    
    print(f"🛡️ {sum(1 for v in validated if v.passed)}/{len(validated)} passed")
    return validated`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  EVALS — LLM Evaluation
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-eval',
    label: 'LLM Eval',
    icon: '✅',
    shortDesc: 'Score LLM outputs',
    category: 'evals',
    name: 'flowyml_eval',
    source: `from flowyml import step, evaluate, EvalDataset, make_scorer

@step(
    inputs=["results/ai_output"],  # ← LLM outputs to evaluate
    outputs=["metrics/llm_eval"],  # ← evaluation scores artifact
)
def eval_llm(outputs):
    """Score LLM outputs with eval scorers."""
    dataset = EvalDataset([
        {"input": "What is ML?", "expected": "Machine Learning is..."},
        {"input": "Explain NLP", "expected": "NLP stands for..."},
    ])
    
    def my_model_fn(input_text):
        # TODO: Replace with your actual model
        return "Generated response..."
    
    relevance = make_scorer("relevance", model="gpt-4")
    coherence = make_scorer("coherence", model="gpt-4")
    
    results = evaluate(
        model_fn=my_model_fn,
        dataset=dataset,
        scorers=[relevance, coherence],
    )
    
    print(f"✅ Evaluation: {len(results)} samples scored")
    return results`,
  },
  // ═══════════════════════════════════════════════════════════════
  //  DEPLOYMENT — Docker, Serving, Stacks, Scheduling
  //  ★ These consume model/pipeline artifacts for deployment
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fml-docker',
    label: 'Docker',
    icon: '🐳',
    shortDesc: 'Containerize pipeline',
    category: 'deploy',
    name: 'flowyml_docker',
    source: `from flowyml import step, DockerBuilder, ContainerConfig

@step(
    inputs=["model/trained", "registry/model_v1"],  # ← consumes model artifacts
    outputs=["deploy/docker_image"],                  # ← produces docker image ref
)
def build_docker(model, registry_version):
    """Build a production Docker image for the pipeline."""
    builder = DockerBuilder(
        model=model,
        config=ContainerConfig(
            base_image="python:3.12-slim",
            requirements=["flowyml", "pandas", "scikit-learn"],
            port=8080,
            healthcheck="/health",
        ),
    )
    
    dockerfile = builder.generate_dockerfile()
    print("🐳 Generated Dockerfile:")
    print(dockerfile[:200])
    
    # builder.build(tag="my-pipeline:latest")
    # builder.push(registry="gcr.io/my-project/my-pipeline:latest")
    return {"image": "my-pipeline:latest", "dockerfile": dockerfile}`,
  },
  {
    id: 'fml-serving',
    label: 'API Serving',
    icon: '🌐',
    shortDesc: 'Deploy as REST API',
    category: 'deploy',
    name: 'flowyml_serving',
    source: `from flowyml import step, serve_model, ModelServer

@step(
    inputs=["model/trained", "registry/model_v1"],  # ← model to serve
    outputs=["deploy/serving_endpoint"],              # ← API endpoint artifact
)
def deploy_serving(model, registry_version):
    """Deploy model as a REST API endpoint."""
    server = ModelServer(
        model=model,
        name="churn_predictor",
        version=registry_version.version if hasattr(registry_version, 'version') else "v1",
        port=8080,
        middleware=["cors", "rate_limit", "auth"],
    )
    
    # Endpoints:
    #   POST /predict        — single prediction
    #   POST /predict/batch  — batch predictions
    #   GET  /health         — health check
    #   GET  /info           — model metadata
    
    # server.start()
    print(f"🌐 Model server configured: {server.name}:{server.port}")
    return {"endpoint": f"http://localhost:{server.port}", "name": server.name}`,
  },
  {
    id: 'fml-stacks',
    label: 'Stack',
    icon: '🏗️',
    shortDesc: 'Infrastructure stack config',
    category: 'deploy',
    name: 'flowyml_stacks',
    source: `from flowyml import Stack, StackComponent

# Define your infrastructure stack
stack = Stack(
    name="production",
    orchestrator=StackComponent("kubernetes", config={
        "cluster": "ml-cluster",
        "namespace": "pipelines",
    }),
    artifact_store=StackComponent("s3", config={
        "bucket": "ml-artifacts",
        "region": "us-east-1",
    }),
    experiment_tracker=StackComponent("mlflow", config={
        "tracking_uri": "http://mlflow:5000",
    }),
    model_registry=StackComponent("flowyml", config={
        "registry_url": "https://registry.flowyml.com",
    }),
    compute=StackComponent("kubernetes", config={
        "gpu_type": "nvidia-t4",
        "max_replicas": 4,
    }),
)

# Activate this stack for your pipeline
# pipeline.set_stack(stack)
print(f"🏗️ Stack '{stack.name}' configured with {len(stack.components)} components")`,
  },
  {
    id: 'fml-schedule',
    label: 'Schedule',
    icon: '📅',
    shortDesc: 'Cron/interval scheduling',
    category: 'deploy',
    name: 'flowyml_schedule',
    source: `from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Daily at 2am
scheduler.schedule_cron(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    cron="0 2 * * *",
)

# Every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: etl_pipeline.run(),
    hours=6,
)

# Weekly Monday 3am
scheduler.schedule_cron(
    name="weekly_retrain",
    pipeline_func=lambda: training_pipeline.run(),
    cron="0 3 * * MON",
)

# scheduler.start()
print("📅 Scheduler configured with", len(scheduler.jobs), "jobs")`,
  },
  {
    id: 'fml-deploy-k8s',
    label: 'Kubernetes',
    icon: '☸️',
    shortDesc: 'Deploy to Kubernetes',
    category: 'deploy',
    name: 'flowyml_kubernetes',
    source: `from flowyml import step, KubernetesDeployer, DeployConfig

@step(
    inputs=["deploy/docker_image"],    # ← consumes docker image
    outputs=["deploy/k8s_endpoint"],   # ← produces k8s deployment artifact
)
def deploy_k8s(docker_image):
    """Deploy pipeline as Kubernetes job/serving endpoint."""
    deployer = KubernetesDeployer(
        config=DeployConfig(
            cluster="ml-cluster",
            namespace="production",
            replicas=3,
            resources={
                "cpu": "2",
                "memory": "4Gi",
                "gpu": "1",
            },
            autoscale={
                "min_replicas": 2,
                "max_replicas": 10,
                "target_cpu": 70,
            },
        ),
    )
    
    # deployer.deploy_image(docker_image["image"])
    print(f"☸️ Kubernetes deployment configured: {docker_image.get('image', 'N/A')}")
    return {"endpoint": "https://ml.example.com", "replicas": 3}`,
  },
];

// ═══════════════════════════════════════════════════════════════
//  Quick-Insert subset — shown in the floating bar between cells
//  (the full list is available via CommandPalette and Sidebar)
// ═══════════════════════════════════════════════════════════════
export const QUICK_INSERT_SNIPPETS = FLOWYML_SNIPPETS.filter(s =>
  ['fml-step', 'fml-pipeline', 'fml-branch', 'fml-context',
   'fml-dataset', 'fml-model', 'fml-metrics', 'fml-parallel',
   'fml-docker', 'fml-stacks', 'fml-serving', 'fml-schedule',
   'fml-prompt-store', 'fml-rag', 'fml-guardrails',
  ].includes(s.id)
);

/**
 * Wrap existing code in a @step decorator.
 * Generates proper inputs/outputs for DAG integration.
 */
export function wrapInStep(source, cellName) {
  const funcName = (cellName || 'my_step')
    .replace(/[^a-zA-Z0-9_]/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase() || 'my_step';

  if (/@step/.test(source)) return source;

  const indented = source
    .split('\n')
    .map(line => '    ' + line)
    .join('\n');

  return `from flowyml import step

@step(outputs=["data/${funcName}_output"])
def ${funcName}():
    """TODO: Add description."""
${indented}
`;
}

/**
 * Extract ALL artifacts from cell source code.
 * Parses @step inputs/outputs, .create(name=...), register(name=...), etc.
 * Returns { inputs: string[], outputs: string[], assets: { name, type }[] }
 */
export function extractAllArtifacts(source) {
  if (!source) return { inputs: [], outputs: [], assets: [] };
  
  const inputs = [];
  const outputs = [];
  const assets = [];
  
  // 1. @step / @map_task inputs/outputs
  const inputMatch = source.match(/inputs\s*=\s*\[([^\]]*)\]/);
  const outputMatch = source.match(/outputs\s*=\s*\[([^\]]*)\]/);
  if (inputMatch) {
    inputMatch[1].replace(/["']([^"']+)["']/g, (_, v) => { inputs.push(v); });
  }
  if (outputMatch) {
    outputMatch[1].replace(/["']([^"']+)["']/g, (_, v) => { outputs.push(v); });
  }
  
  // 2. Dataset.create(name="...") → asset
  const datasetMatches = source.matchAll(/Dataset\.create\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of datasetMatches) {
    assets.push({ name: m[1], type: 'dataset', icon: '📊', color: '#22d3ee' });
  }
  
  // 3. Model.create(name="...") → asset
  const modelMatches = source.matchAll(/Model\.create\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of modelMatches) {
    assets.push({ name: m[1], type: 'model', icon: '🤖', color: '#34d399' });
  }
  
  // 4. Metrics.create(name="...") → asset
  const metricsMatches = source.matchAll(/Metrics\.create\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of metricsMatches) {
    assets.push({ name: m[1], type: 'metrics', icon: '📈', color: '#fbbf24' });
  }
  
  // 5. FeatureSet.create(name="...") → asset
  const featureMatches = source.matchAll(/FeatureSet\.create\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of featureMatches) {
    assets.push({ name: m[1], type: 'featureset', icon: '🔩', color: '#fb923c' });
  }
  
  // 6. Report.create(name="...") → asset
  const reportMatches = source.matchAll(/Report\.create\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of reportMatches) {
    assets.push({ name: m[1], type: 'report', icon: '📝', color: '#94a3b8' });
  }
  
  // 7. Experiment(name="...") → asset
  const expMatches = source.matchAll(/Experiment\(\s*name\s*=\s*["']([^"']+)["']/g);
  for (const m of expMatches) {
    assets.push({ name: m[1], type: 'experiment', icon: '🧪', color: '#fb923c' });
  }
  
  // 8. registry.register(name="...") → asset
  const regMatches = source.matchAll(/registry\.register\([^)]*name\s*=\s*["']([^"']+)["']/g);
  for (const m of regMatches) {
    assets.push({ name: m[1], type: 'registry', icon: '📦', color: '#4ade80' });
  }
  
  // 9. DockerBuilder → deploy asset
  if (/DockerBuilder\s*\(/.test(source)) {
    const tagMatch = source.match(/tag\s*=\s*["']([^"']+)["']/);
    assets.push({ name: tagMatch?.[1] || 'docker_image', type: 'docker', icon: '🐳', color: '#38bdf8' });
  }
  
  // 10. ModelServer → serving endpoint
  if (/ModelServer\s*\(/.test(source)) {
    const nameMatch = source.match(/ModelServer\([^)]*name\s*=\s*["']([^"']+)["']/);
    assets.push({ name: nameMatch?.[1] || 'api_endpoint', type: 'serving', icon: '🌐', color: '#34d399' });
  }
  
  return { inputs, outputs, assets };
}

/**
 * Quick-detect which FlowyML constructs are present in source code.
 * Used by CellEditor badges and PipelineDAG node decorators.
 */
export function detectFlowyML(source) {
  if (!source) return null;
  const detections = [];

  // Core
  if (/@step/.test(source)) detections.push('step');
  if (/Pipeline\s*\(/.test(source)) detections.push('pipeline');
  if (/\bcontext\s*\(/.test(source) && /from\s+flowyml/.test(source)) detections.push('context');
  if (/If\s*\(|Switch\s*\(/.test(source)) detections.push('branch');
  if (/map_task/.test(source)) detections.push('map_task');
  if (/sub_pipeline/.test(source)) detections.push('subpipeline');

  // Assets
  if (/Dataset\./.test(source)) detections.push('dataset');
  if (/Model\./.test(source) && /from\s+flowyml/.test(source)) detections.push('model');
  if (/Metrics\./.test(source)) detections.push('metrics');
  if (/FeatureSet\./.test(source)) detections.push('featureset');
  if (/Report\./.test(source) && /from\s+flowyml/.test(source)) detections.push('report');

  // Tracking
  if (/Experiment\s*\(/.test(source)) detections.push('experiment');
  if (/ModelRegistry\s*\(/.test(source)) detections.push('registry');

  // Resilience
  if (/parallel_map|ParallelExecutor|BatchExecutor/.test(source)) detections.push('parallel');
  if (/@retry|CircuitBreaker|FallbackHandler/.test(source)) detections.push('retry');
  if (/checkpoint_enabled_pipeline|PipelineCheckpoint/.test(source)) detections.push('checkpoint');
  if (/SmartCache|@memoize|memoize\(/.test(source)) detections.push('cache');

  // Observability
  if (/trace_genai|@trace_genai|span\(/.test(source)) detections.push('trace');
  if (/patch_openai|TracedOpenAI/.test(source)) detections.push('openai_trace');
  if (/FlowyMLCallbackHandler|trace_graph|@observe/.test(source)) detections.push('langchain');
  if (/detect_drift|compute_stats/.test(source)) detections.push('drift');
  if (/configure_notifications|get_notifier/.test(source)) detections.push('notifications');

  // Evals
  if (/evaluate\s*\(|EvalDataset/.test(source)) detections.push('eval');

  // Deployment
  if (/DockerBuilder|ContainerConfig/.test(source)) detections.push('docker');
  if (/serve_model|ModelServer/.test(source)) detections.push('serving');
  if (/Stack\s*\(|StackComponent/.test(source)) detections.push('stack');
  if (/PipelineScheduler/.test(source)) detections.push('schedule');
  if (/KubernetesDeployer|DeployConfig/.test(source)) detections.push('kubernetes');

  return detections.length > 0 ? detections : null;
}

/**
 * ARTIFACT_TYPES: visual config for artifact nodes in the DAG.
 */
export const ARTIFACT_TYPES = {
  data:       { icon: '📊', label: 'Data', color: '#22d3ee', shape: 'hexagon' },
  model:      { icon: '🤖', label: 'Model', color: '#34d399', shape: 'hexagon' },
  metrics:    { icon: '📈', label: 'Metrics', color: '#fbbf24', shape: 'diamond' },
  features:   { icon: '🔩', label: 'Features', color: '#fb923c', shape: 'diamond' },
  report:     { icon: '📝', label: 'Report', color: '#94a3b8', shape: 'diamond' },
  experiment: { icon: '🧪', label: 'Experiment', color: '#fb923c', shape: 'circle' },
  registry:   { icon: '📦', label: 'Registry', color: '#4ade80', shape: 'circle' },
  deploy:     { icon: '🚀', label: 'Deploy', color: '#818cf8', shape: 'circle' },
  results:    { icon: '📋', label: 'Results', color: '#c084fc', shape: 'diamond' },
  retrain:    { icon: '🔄', label: 'Retrain', color: '#f472b6', shape: 'diamond' },
};

/**
 * Derive the artifact type from its key prefix.
 * e.g. "data/my_dataset" → "data", "model/trained" → "model"
 */
export function getArtifactType(artifactKey) {
  const prefix = artifactKey.split('/')[0];
  return ARTIFACT_TYPES[prefix] || ARTIFACT_TYPES.data;
}

/**
 * Map detection type to a display badge for DAG nodes and cell toolbar.
 */
export const DETECTION_BADGES = {
  // Core
  step:        { label: '@step',       color: '#818cf8', icon: '⚡' },
  pipeline:    { label: 'Pipeline',    color: '#a78bfa', icon: '🔗' },
  context:     { label: 'Context',     color: '#38bdf8', icon: '🔧' },
  branch:      { label: 'Branch',      color: '#f472b6', icon: '🔀' },
  map_task:    { label: 'MapTask',     color: '#c084fc', icon: '🗺️' },
  subpipeline: { label: 'SubPipeline', color: '#a78bfa', icon: '📎' },
  // Assets
  dataset:     { label: 'Dataset',     color: '#22d3ee', icon: '📊' },
  model:       { label: 'Model',       color: '#34d399', icon: '🤖' },
  metrics:     { label: 'Metrics',     color: '#fbbf24', icon: '📈' },
  featureset:  { label: 'FeatureSet',  color: '#fb923c', icon: '🔩' },
  report:      { label: 'Report',      color: '#94a3b8', icon: '📝' },
  // Tracking
  experiment:  { label: 'Experiment',  color: '#fb923c', icon: '🧪' },
  registry:    { label: 'Registry',    color: '#4ade80', icon: '📦' },
  // Resilience
  parallel:    { label: 'Parallel',    color: '#c084fc', icon: '⚙️' },
  retry:       { label: 'Retry',       color: '#fbbf24', icon: '🔄' },
  checkpoint:  { label: 'Checkpoint',  color: '#60a5fa', icon: '💾' },
  cache:       { label: 'Cache',       color: '#94a3b8', icon: '🗄️' },
  // Observe
  trace:       { label: 'Trace',       color: '#818cf8', icon: '🔍' },
  openai_trace: { label: 'OpenAI',    color: '#22d3ee', icon: '🧠' },
  langchain:   { label: 'LangChain',   color: '#34d399', icon: '🦜' },
  drift:       { label: 'Drift',       color: '#f87171', icon: '📉' },
  notifications: { label: 'Alerts',   color: '#fbbf24', icon: '🔔' },
  // Evals
  eval:        { label: 'Eval',        color: '#2dd4bf', icon: '✅' },
  // Deploy
  docker:      { label: 'Docker',      color: '#38bdf8', icon: '🐳' },
  serving:     { label: 'Serving',     color: '#34d399', icon: '🌐' },
  stack:       { label: 'Stack',       color: '#a78bfa', icon: '🏗️' },
  schedule:    { label: 'Schedule',    color: '#60a5fa', icon: '📅' },
  kubernetes:  { label: 'K8s',         color: '#818cf8', icon: '☸️' },
};
