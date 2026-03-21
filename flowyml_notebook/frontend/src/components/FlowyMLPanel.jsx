import React, { useState, useEffect, useCallback } from 'react';
import {
  X, Workflow, FlaskConical, Package, Rocket, Clock, Database,
  BarChart3, GitBranch, Server, Layers, Play, ChevronRight,
  Upload, Tag, Box, TrendingUp, Settings, Shield, Zap, Globe, 
  FileCode, Container, Cpu, ArrowRight, CheckCircle2, AlertCircle,
  RefreshCcw, Eye, MoreHorizontal, Loader2, Info, ChevronDown
} from 'lucide-react';

const PANEL_TABS = [
  { id: 'pipelines', label: 'Pipelines', icon: Workflow },
  { id: 'deploy', label: 'Deploy', icon: Rocket },
  { id: 'experiments', label: 'Experiments', icon: FlaskConical },
  { id: 'assets', label: 'Assets', icon: Package },
  { id: 'schedule', label: 'Schedule', icon: Clock },
];

export default function FlowyMLPanel({ onClose, connected, onAction }) {
  const [activeTab, setActiveTab] = useState('pipelines');

  const handleAction = useCallback((action, payload) => {
    if (onAction) onAction(action, payload);
  }, [onAction]);

  return (
    <div className="flowyml-panel">
      {/* Header */}
      <div className="flowyml-panel-header">
        <h3 className="flex items-center gap-2">
          <Zap size={16} />
          FlowyML
        </h3>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="badge success">● Connected</span>
          ) : (
            <span className="badge warning">● Local Mode</span>
          )}
          <button className="btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="panel-tabs">
        {PANEL_TABS.map(tab => (
          <button key={tab.id}
            className={`panel-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}>
            <tab.icon size={13} style={{ display: 'inline', marginRight: 4, verticalAlign: -2 }} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="panel-content">
        {activeTab === 'pipelines' && <PipelinesTab onAction={handleAction} />}
        {activeTab === 'deploy' && <DeployTab onAction={handleAction} />}
        {activeTab === 'experiments' && <ExperimentsTab />}
        {activeTab === 'assets' && <AssetsTab />}
        {activeTab === 'schedule' && <ScheduleTab onAction={handleAction} />}
      </div>
    </div>
  );
}

/* ===== Pipelines Tab — Real Data ===== */
function PipelinesTab({ onAction }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(false);

  const fetchPipelines = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/production/pipelines');
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error('Failed to fetch pipelines:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPipelines(); }, [fetchPipelines]);

  const handlePromote = async () => {
    setPromoting(true);
    try {
      const res = await fetch('/api/production/promote', { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        onAction('notify', { message: `Pipeline promoted: ${result.path}`, type: 'success' });
        fetchPipelines();
      }
    } catch (e) {
      onAction('notify', { message: `Promotion failed: ${e.message}`, type: 'error' });
    } finally {
      setPromoting(false);
    }
  };

  return (
    <div>
      {/* Quick Actions */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Quick Actions</div>
        <div className="grid grid-cols-2 gap-2">
          <QuickAction icon={FileCode} label="Export Pipeline" desc="Clean .py file"
            onClick={() => onAction('export', { format: 'pipeline' })} />
          <QuickAction icon={Play} label="Run All" desc="Execute notebook"
            onClick={() => onAction('execute-all')} />
          <QuickAction icon={GitBranch} label="View DAG" desc="Dependency graph"
            onClick={() => onAction('show-dag')} />
          <QuickAction icon={BarChart3} label="HTML Report" desc="Share results"
            onClick={() => onAction('export', { format: 'html' })} />
        </div>
      </div>

      {/* Pipeline promotion */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Promote to Pipeline</div>
        <div className="p-3 rounded-lg border border-white/5 bg-white/[0.02]">
          <p className="text-xs text-gray-500 mb-3">
            Convert this notebook into a production FlowyML pipeline with proper imports, error handling, and a main guard.
          </p>
          <button className="btn btn-primary w-full justify-center" onClick={handlePromote} disabled={promoting}>
            {promoting ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
            {promoting ? 'Promoting...' : 'Promote Notebook → Pipeline'}
          </button>
        </div>
      </div>

      {/* Pipeline Data from Backend */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          Pipeline Cells
          <button className="btn-icon" style={{ width: 20, height: 20 }} onClick={fetchPipelines}>
            <RefreshCcw size={11} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center p-4 text-gray-500 text-xs">
            <Loader2 size={14} className="animate-spin mr-2" /> Loading...
          </div>
        ) : data && data.step_cells && data.step_cells.length > 0 ? (
          <>
            {data.step_cells.map((cell, i) => (
              <div key={cell.cell_id} className="pipeline-card">
                <div className="flex items-center justify-between">
                  <span className="name">{cell.name}</span>
                  <div className="flex items-center gap-1">
                    {cell.has_step && <span className="badge info">@step</span>}
                    {cell.has_pipeline && <span className="badge info">Pipeline</span>}
                  </div>
                </div>
                <div className="meta">
                  <span>{cell.executed ? '✓ Executed' : '○ Not run'}</span>
                  {cell.last_executed && <span>{new Date(cell.last_executed).toLocaleTimeString()}</span>}
                </div>
              </div>
            ))}
          </>
        ) : (
          <div className="p-3 text-center text-gray-600 text-xs">
            <Info size={14} className="mx-auto mb-1 text-gray-500" />
            No @step or Pipeline() cells found.<br />
            Add <code className="text-indigo-400">@step</code> decorators to your cells to build pipelines.
          </div>
        )}
      </div>

      {/* Promoted Pipelines from disk */}
      {data?.promoted_pipelines?.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Promoted Pipelines</div>
          {data.promoted_pipelines.map((p, i) => (
            <PipelineCard key={i} name={p.name} status={p.status} steps={p.steps}
              lastRun={new Date(p.last_run).toLocaleString()} />
          ))}
        </div>
      )}
    </div>
  );
}

function QuickAction({ icon: Icon, label, desc, onClick }) {
  return (
    <button className="text-left p-2.5 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all cursor-pointer group"
      onClick={onClick}>
      <Icon size={14} className="text-gray-500 group-hover:text-indigo-400 mb-1 transition-colors" />
      <div className="text-xs font-medium text-gray-300">{label}</div>
      <div className="text-[10px] text-gray-600">{desc}</div>
    </button>
  );
}

function PipelineCard({ name, status, steps, lastRun }) {
  const statusConfig = {
    success: { icon: CheckCircle2, color: 'text-emerald-400', badge: 'success' },
    error: { icon: AlertCircle, color: 'text-rose-400', badge: 'error' },
    running: { icon: RefreshCcw, color: 'text-purple-400 animate-spin', badge: 'info' },
  };
  const cfg = statusConfig[status] || statusConfig.success;
  return (
    <div className="pipeline-card">
      <div className="flex items-center justify-between">
        <span className="name">{name}</span>
        <span className={`badge ${cfg.badge}`}>
          <cfg.icon size={10} className={cfg.color} /> {status}
        </span>
      </div>
      <div className="meta">
        <span>{steps} steps</span>
        <span>{lastRun}</span>
      </div>
    </div>
  );
}

/* ===== Deploy Tab — Real Data ===== */
function DeployTab({ onAction }) {
  const [deploying, setDeploying] = useState(null);
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/production/experiments');
        if (res.ok) {
          const data = await res.json();
          setModels(data.models || []);
        }
      } catch (e) { /* ignore */ }
      finally { setLoadingModels(false); }
    })();
  }, []);

  const handleDeploy = async (mode) => {
    setDeploying(mode);
    try {
      const res = await fetch(`/api/production/deploy?mode=${mode}`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        onAction('notify', { message: `${result.status}: ${result.model_name} (${mode})`, type: 'success' });
      } else {
        const err = await res.json();
        onAction('notify', { message: err.detail || 'Deploy failed', type: 'error' });
      }
    } catch (e) {
      onAction('notify', { message: `Deploy failed: ${e.message}`, type: 'error' });
    } finally {
      setDeploying(null);
    }
  };

  return (
    <div>
      {/* One-Click Deploy */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Production Deployment</div>
        <div className="space-y-2">
          <DeployOption
            icon={Globe} title="Deploy as API" desc="REST endpoint via FlowyML Serving"
            badge="recommended" loading={deploying === 'api'}
            onClick={() => handleDeploy('api')} />
          <DeployOption
            icon={Container} title="Docker Container" desc="Containerized notebook execution"
            loading={deploying === 'docker'}
            onClick={() => handleDeploy('docker')} />
          <DeployOption
            icon={Cpu} title="Batch Pipeline" desc="Scheduled production pipeline"
            loading={deploying === 'batch'}
            onClick={() => handleDeploy('batch')} />
        </div>
      </div>

      {/* Stack Configuration */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          <span>FlowyML Stacks</span>
          <span className="text-[10px] text-gray-600 font-normal normal-case tracking-normal">Infrastructure</span>
        </div>
        <div className="space-y-1.5">
          <StackCard icon={Database} name="Data Layer" stack="PostgreSQL + DuckDB" />
          <StackCard icon={Server} name="Compute" stack="Local / Kubernetes" />
          <StackCard icon={Package} name="Artifact Store" stack="S3 / GCS / Local" />
          <StackCard icon={BarChart3} name="Experiment Tracker" stack="MLflow / W&B" />
          <StackCard icon={Shield} name="Model Registry" stack="FlowyML Registry" />
          <StackCard icon={Layers} name="Orchestrator" stack="FlowyML Scheduler" />
        </div>
      </div>

      {/* Model Deploy — Real Data */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Detected Models</div>
        {loadingModels ? (
          <div className="flex items-center justify-center p-4 text-gray-500 text-xs">
            <Loader2 size={14} className="animate-spin mr-2" /> Scanning namespace...
          </div>
        ) : models.length > 0 ? (
          models.map((model, i) => (
            <div key={i} className="p-3 rounded-lg border border-white/5 bg-white/[0.02] mb-2">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                <Box size={12} className="text-cyan-400" />
                Variable: <code className="text-cyan-400">{model.name}</code>
              </div>
              <div className="flex gap-2 text-xs mb-3">
                <span className="badge info">{model.type}</span>
                {model.module && <span className="badge info">{model.module.split('.')[0]}</span>}
              </div>
              {model.params && (
                <div className="text-[10px] text-gray-600 mb-2 font-mono">
                  {Object.entries(model.params).slice(0, 4).map(([k, v]) => `${k}=${v}`).join(', ')}
                </div>
              )}
              <div className="flex gap-2">
                <button className="btn btn-primary flex-1 justify-center text-xs"
                  onClick={() => handleDeploy('api')} disabled={deploying}>
                  {deploying === 'api' ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />} Deploy Local
                </button>
                <button className="btn btn-ghost flex-1 justify-center text-xs border border-white/10"
                  onClick={() => handleDeploy('docker')} disabled={deploying}>
                  {deploying === 'docker' ? <Loader2 size={12} className="animate-spin" /> : <Globe size={12} />} Docker
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="p-3 text-center text-gray-600 text-xs">
            <Info size={14} className="mx-auto mb-1 text-gray-500" />
            No models detected in namespace.<br />
            Train a model (e.g. sklearn) and it will appear here.
          </div>
        )}
      </div>
    </div>
  );
}

function DeployOption({ icon: Icon, title, desc, badge, loading, onClick }) {
  return (
    <button className="w-full text-left p-3 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all cursor-pointer group flex items-start gap-3"
      onClick={onClick} disabled={loading}>
      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
        {loading ? <Loader2 size={16} className="text-indigo-400 animate-spin" /> : <Icon size={16} className="text-indigo-400" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-200">{title}</span>
          {badge && <span className="badge info">{badge}</span>}
        </div>
        <div className="text-xs text-gray-500 mt-0.5">{desc}</div>
      </div>
      <ArrowRight size={14} className="text-gray-600 group-hover:text-indigo-400 mt-1 transition-colors" />
    </button>
  );
}

function StackCard({ icon: Icon, name, stack }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-white/[0.02]`}
      onClick={() => setExpanded(!expanded)}>
      <Icon size={14} className="text-gray-500" />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-gray-300">{name}</div>
        <div className="text-[10px] text-gray-600">{stack}</div>
      </div>
      <ChevronDown size={12} className={`text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
    </div>
  );
}

/* ===== Experiments Tab — Real Data ===== */
function ExperimentsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/production/experiments');
        if (res.ok) setData(await res.json());
      } catch (e) { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-gray-500 text-xs">
        <Loader2 size={14} className="animate-spin mr-2" /> Loading experiments...
      </div>
    );
  }

  const hasData = data?.has_data;
  const models = data?.models || [];
  const metrics = data?.metrics || {};
  const metricEntries = Object.entries(metrics);

  return (
    <div>
      {/* Metric summary cards — Real Data */}
      {metricEntries.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Metrics</div>
          <div className="grid grid-cols-2 gap-2">
            {metricEntries.slice(0, 6).map(([key, value]) => (
              <div key={key} className="metric-card">
                <div className="metric-label">{key}</div>
                <div className="metric-value text-cyan-400">
                  {typeof value === 'number' ? (value < 1 ? value.toFixed(4) : value.toFixed(2)) : String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model runs — Real Data */}
      {models.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Trained Models</div>
          {models.map((model, i) => (
            <div key={i} className="experiment-row">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-300">{model.name}</div>
                <div className="text-[10px] text-gray-600 mt-0.5">
                  {model.type} ({model.module?.split('.')[0]})
                </div>
                {model.params && (
                  <div className="text-[10px] text-gray-600 mt-0.5 font-mono">
                    {Object.entries(model.params).slice(0, 5).map(([k, v]) => `${k}=${v}`).join(', ')}
                  </div>
                )}
              </div>
              <div className="text-right">
                <span className="badge info">{model.type}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {!hasData && (
        <div className="p-6 text-center">
          <FlaskConical size={24} className="mx-auto mb-2 text-gray-600" />
          <div className="text-sm text-gray-400 mb-1">No experiments yet</div>
          <div className="text-xs text-gray-600">
            Train models and log metrics in your cells.<br />
            They will automatically appear here.
          </div>
          <div className="mt-3 p-2 rounded-lg bg-white/[0.02] border border-white/5 text-[10px] text-gray-500 font-mono text-left">
            from sklearn.ensemble import RandomForestClassifier<br />
            model = RandomForestClassifier(n_estimators=100)<br />
            model.fit(X_train, y_train)<br />
            metrics = {'{'}accuracy: model.score(X_test, y_test){'}'}
          </div>
        </div>
      )}
    </div>
  );
}

/* ===== Assets Tab — Real Data ===== */
function AssetsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAssets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/production/assets');
      if (res.ok) setData(await res.json());
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAssets(); }, [fetchAssets]);

  const iconMap = {
    dataset: { icon: Database, cls: 'dataset' },
    model: { icon: Cpu, cls: 'model' },
    metrics: { icon: TrendingUp, cls: 'metrics' },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-gray-500 text-xs">
        <Loader2 size={14} className="animate-spin mr-2" /> Scanning namespace...
      </div>
    );
  }

  const assets = data?.assets || [];

  return (
    <div>
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          Kernel Assets
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-gray-600 font-normal normal-case tracking-normal">{assets.length}</span>
            <button className="btn-icon" style={{ width: 20, height: 20 }} onClick={fetchAssets}>
              <RefreshCcw size={11} />
            </button>
          </div>
        </div>

        {assets.length > 0 ? (
          assets.map((asset, i) => {
            const cfg = iconMap[asset.type] || iconMap.dataset;
            return (
              <div key={i} className="asset-card">
                <div className={`asset-icon ${cfg.cls}`}>
                  <cfg.icon size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-300 truncate">{asset.name}</div>
                  <div className="text-[10px] text-gray-600">
                    {asset.subtype || asset.type} · {asset.size}
                    {asset.rows !== undefined && ` · ${asset.rows.toLocaleString()} rows`}
                    {asset.columns !== undefined && ` × ${asset.columns} cols`}
                    {asset.shape && ` · shape ${JSON.stringify(asset.shape)}`}
                  </div>
                </div>
                <span className="badge info">{asset.type}</span>
              </div>
            );
          })
        ) : (
          <div className="p-4 text-center">
            <Package size={20} className="mx-auto mb-2 text-gray-600" />
            <div className="text-xs text-gray-500">
              No assets in kernel namespace.<br />
              Create DataFrames, arrays, or models to see them here.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ===== Schedule Tab ===== */
function ScheduleTab({ onAction }) {
  const [cron, setCron] = useState('0 6 * * *');
  const [scheduleType, setScheduleType] = useState('cron');
  const [schedules, setSchedules] = useState([]);
  const [scheduling, setScheduling] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/production/schedules');
        if (res.ok) {
          const data = await res.json();
          setSchedules(data.schedules || []);
        }
      } catch (e) { /* ignore */ }
    })();
  }, []);

  const handleSchedule = async () => {
    setScheduling(true);
    try {
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cron: scheduleType === 'cron' ? cron : null }),
      });
      if (res.ok) {
        const result = await res.json();
        onAction('notify', { message: 'Pipeline scheduled successfully', type: 'success' });
        setSchedules(prev => [...prev, { name: `Schedule ${prev.length + 1}`, cron, status: 'active' }]);
      }
    } catch (e) {
      onAction('notify', { message: `Scheduling failed: ${e.message}`, type: 'error' });
    } finally {
      setScheduling(false);
    }
  };

  return (
    <div>
      <div className="sidebar-section">
        <div className="sidebar-section-title">Schedule Notebook</div>
        <div className="p-3 rounded-lg border border-white/5 bg-white/[0.02]">
          <div className="flex gap-1 mb-3">
            <button className={`chart-type-btn ${scheduleType === 'cron' ? 'active' : ''}`}
              onClick={() => setScheduleType('cron')}>Cron</button>
            <button className={`chart-type-btn ${scheduleType === 'interval' ? 'active' : ''}`}
              onClick={() => setScheduleType('interval')}>Interval</button>
            <button className={`chart-type-btn ${scheduleType === 'event' ? 'active' : ''}`}
              onClick={() => setScheduleType('event')}>Event</button>
          </div>

          {scheduleType === 'cron' && (
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Cron Expression</label>
              <input className="sidebar-search" value={cron} onChange={e => setCron(e.target.value)}
                placeholder="0 6 * * *" style={{ marginBottom: 0 }} />
              <div className="flex flex-wrap gap-1.5">
                {['0 6 * * *', '0 */6 * * *', '0 0 * * 1', '*/30 * * * *'].map(c => (
                  <button key={c} className="text-[10px] px-2 py-0.5 rounded bg-white/[0.03] border border-white/5 text-gray-500 hover:text-indigo-400 hover:border-indigo-500/20"
                    onClick={() => setCron(c)}>{c}</button>
                ))}
              </div>
            </div>
          )}

          {scheduleType === 'interval' && (
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Run every</label>
              <div className="flex gap-2">
                <input className="sidebar-search w-20" type="number" defaultValue={6} style={{ marginBottom: 0 }} />
                <select className="sidebar-search flex-1" style={{ marginBottom: 0 }}>
                  <option>hours</option>
                  <option>minutes</option>
                  <option>days</option>
                </select>
              </div>
            </div>
          )}

          {scheduleType === 'event' && (
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Trigger Event</label>
              <select className="sidebar-search" style={{ marginBottom: 0 }}>
                <option>New data uploaded</option>
                <option>Model drift detected</option>
                <option>Pipeline completed</option>
                <option>Manual trigger</option>
              </select>
            </div>
          )}

          <button className="btn btn-primary w-full justify-center mt-3"
            onClick={handleSchedule} disabled={scheduling}>
            {scheduling ? <Loader2 size={14} className="animate-spin" /> : <Clock size={14} />}
            {scheduling ? 'Scheduling...' : 'Schedule Pipeline'}
          </button>
        </div>
      </div>

      {/* Active schedules */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">Active Schedules</div>
        {schedules.length > 0 ? (
          schedules.map((sched, i) => (
            <ScheduleItem key={i} name={sched.name} cron={sched.cron || sched.expression || '—'}
              status={sched.status} nextRun={sched.next_run || '—'} />
          ))
        ) : (
          <div className="p-3 text-center text-gray-600 text-xs">
            <Clock size={14} className="mx-auto mb-1 text-gray-500" />
            No active schedules.<br />
            Schedule your notebook to run automatically.
          </div>
        )}
      </div>
    </div>
  );
}

function ScheduleItem({ name, cron, status, nextRun }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.02] transition-all">
      <div className={`w-2 h-2 rounded-full ${status === 'active' ? 'bg-emerald-400' : 'bg-gray-600'}`} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-gray-300">{name}</div>
        <div className="text-[10px] text-gray-600 font-mono">{cron}</div>
      </div>
      <div className="text-right">
        <div className="text-[10px] text-gray-500">Next run</div>
        <div className="text-xs text-cyan-400 font-mono">{nextRun}</div>
      </div>
    </div>
  );
}
