import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Activity, Clock, Shield, Zap, Database, Package,
  BarChart2, AlertTriangle, CheckCircle, ChevronDown,
  ChevronRight, Play, RefreshCw, Download, Search, Trash2,
  Loader2, Info, AlertCircle, Cpu, HardDrive, Monitor,
  Hash, Copy, Terminal, Wrench, ArrowRight, TrendingUp,
  FileText, Settings, ExternalLink, XCircle
} from 'lucide-react';

const API = '/api';

const TABS = [
  { id: 'profiler', label: 'Profile', icon: Activity },
  { id: 'benchmark', label: 'Bench', icon: BarChart2 },
  { id: 'quality', label: 'Quality', icon: Shield },
  { id: 'lint', label: 'Lint', icon: Zap },
  { id: 'history', label: 'History', icon: Clock },
  { id: 'env', label: 'Env', icon: Package },
];

/* ===== Helpers ===== */

function fmt(n, digits = 2) {
  if (n == null) return '—';
  if (typeof n !== 'number') return String(n);
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toFixed(digits);
}

function fmtBytes(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function fmtTime(seconds) {
  if (seconds == null) return '—';
  if (seconds < 0.001) return (seconds * 1e6).toFixed(0) + ' μs';
  if (seconds < 1) return (seconds * 1000).toFixed(1) + ' ms';
  if (seconds < 60) return seconds.toFixed(2) + ' s';
  return (seconds / 60).toFixed(1) + ' min';
}

function scoreColor(score) {
  if (score >= 80) return 'var(--green, #22c55e)';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

function severityColor(severity) {
  switch (severity) {
    case 'security': return '#ef4444';
    case 'error': return '#ef4444';
    case 'performance': return '#f59e0b';
    case 'warning': return '#f59e0b';
    case 'style': return '#6366f1';
    case 'info': return '#64748b';
    default: return '#64748b';
  }
}

function severityIcon(severity) {
  switch (severity) {
    case 'security': return Shield;
    case 'error': return XCircle;
    case 'performance': return TrendingUp;
    case 'warning': return AlertTriangle;
    case 'style': return FileText;
    case 'info': return Info;
    default: return Info;
  }
}

const Spinner = ({ size = 14 }) => (
  <Loader2 size={size} className="animate-spin" style={{ color: 'var(--accent-light, #818cf8)' }} />
);

const ErrorBanner = ({ message, onRetry }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '8px 12px', borderRadius: 8,
    background: 'rgba(239, 68, 68, 0.08)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    fontSize: '0.72rem', color: '#fca5a5',
  }}>
    <AlertCircle size={13} style={{ color: '#ef4444', flexShrink: 0 }} />
    <span style={{ flex: 1 }}>{message}</span>
    {onRetry && (
      <button onClick={onRetry} style={{
        background: 'rgba(239, 68, 68, 0.15)', border: 'none',
        borderRadius: 4, padding: '2px 8px', color: '#fca5a5',
        cursor: 'pointer', fontSize: '0.65rem',
      }}>Retry</button>
    )}
  </div>
);

const EmptyState = ({ icon: Icon, message }) => (
  <div style={{
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', gap: 8, padding: '32px 16px',
    color: 'var(--fg-dim, #4b5563)',
  }}>
    <Icon size={28} style={{ opacity: 0.4 }} />
    <span style={{ fontSize: '0.75rem', textAlign: 'center' }}>{message}</span>
  </div>
);

const StatCard = ({ label, value, icon: Icon, color, sub }) => (
  <div style={{
    padding: '10px 12px', borderRadius: 8,
    background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
    border: '1px solid var(--border, rgba(255,255,255,0.05))',
    display: 'flex', flexDirection: 'column', gap: 2,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      {Icon && <Icon size={12} style={{ color: color || 'var(--fg-dim)', opacity: 0.7 }} />}
      <span style={{ fontSize: '0.62rem', color: 'var(--fg-dim, #6b7280)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
    </div>
    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: color || 'var(--fg-primary, #e5e7eb)', fontFamily: "'JetBrains Mono', monospace" }}>
      {value}
    </div>
    {sub && <div style={{ fontSize: '0.6rem', color: 'var(--fg-dim, #6b7280)' }}>{sub}</div>}
  </div>
);

/* ===== Main Component ===== */

export default function ToolsPanel({ onClose, cells, variables, focusedCellId, onUpdateCell }) {
  const [activeTab, setActiveTab] = useState('profiler');

  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      background: 'var(--bg-primary, #0f1117)',
      borderLeft: '1px solid var(--border, rgba(255,255,255,0.06))',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px 0', flexShrink: 0,
        background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(168,85,247,0.06) 50%, rgba(14,165,233,0.05) 100%)',
        borderBottom: '1px solid var(--border, rgba(255,255,255,0.06))',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Wrench size={14} style={{ color: 'var(--accent-light, #818cf8)' }} />
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--fg-primary, #e5e7eb)' }}>
              Dev Tools
            </span>
            {focusedCellId && (
              <span style={{
                fontSize: '0.6rem', padding: '1px 6px', borderRadius: 4,
                background: 'rgba(99,102,241,0.12)', color: 'var(--accent-light, #818cf8)',
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {focusedCellId.slice(0, 8)}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="btn-icon"
            style={{ width: 26, height: 26, borderRadius: 6 }}
            title="Close panel"
          >
            <X size={14} />
          </button>
        </div>

        {/* Tab strip */}
        <div style={{ display: 'flex', gap: 1, overflowX: 'auto', flexShrink: 0 }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 4, padding: '7px 4px', border: 'none',
                  borderBottom: isActive ? '2px solid var(--accent-light, #818cf8)' : '2px solid transparent',
                  background: isActive ? 'rgba(99,102,241,0.08)' : 'transparent',
                  color: isActive ? 'var(--accent-light, #818cf8)' : 'var(--fg-dim, #6b7280)',
                  fontSize: '0.65rem', fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer', transition: 'all 0.15s ease',
                  borderRadius: '6px 6px 0 0',
                }}
              >
                <Icon size={12} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: 0, minHeight: 0 }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            style={{ padding: 12 }}
          >
            {activeTab === 'profiler' && <ProfilerTab cellId={focusedCellId} />}
            {activeTab === 'benchmark' && <BenchmarkTab cellId={focusedCellId} />}
            {activeTab === 'quality' && <DataQualityTab variables={variables} />}
            {activeTab === 'lint' && <LintTab cellId={focusedCellId} onUpdateCell={onUpdateCell} />}
            {activeTab === 'history' && <HistoryTab cells={cells} />}
            {activeTab === 'env' && <EnvironmentTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════
   1. PROFILER TAB
   ═══════════════════════════════════════════════ */

function ProfilerTab({ cellId }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const runProfile = useCallback(async () => {
    if (!cellId) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/cells/${cellId}/profile`, { method: 'POST' });
      if (!res.ok) throw new Error(`Profile failed (${res.status})`);
      const data = await res.json();
      // Backend returns {profile: {wall_time_s, ...}, output: {...}}
      const p = data.profile || data;
      const mapped = {
        wall_time: p.wall_time_s || p.wall_time || 0,
        cpu_time: p.cpu_time_s || p.cpu_time || 0,
        memory_delta: (p.memory_delta_mb || p.memory_delta || 0) * 1024 * 1024,
        peak_memory: (p.peak_memory_mb || p.peak_memory || 0) * 1024 * 1024,
        top_functions: p.top_functions || [],
        function_calls: p.function_calls || 0,
      };
      setResult(mapped);
      setHistory(prev => [{ ...mapped, timestamp: new Date().toISOString() }, ...prev].slice(0, 20));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [cellId]);

  if (!cellId) return <EmptyState icon={Activity} message="Select a cell to profile its execution" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Run button */}
      <button
        onClick={runProfile}
        disabled={loading}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          padding: '8px 14px', borderRadius: 8, border: 'none',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(168,85,247,0.15) 100%)',
          color: 'var(--accent-light, #818cf8)', fontSize: '0.75rem', fontWeight: 600,
          cursor: loading ? 'wait' : 'pointer',
          transition: 'all 0.15s ease',
        }}
      >
        {loading ? <Spinner size={13} /> : <Play size={13} />}
        {loading ? 'Profiling…' : 'Profile Cell'}
      </button>

      {error && <ErrorBanner message={error} onRetry={runProfile} />}

      {/* Results */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {/* Timing stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <StatCard label="Wall Time" value={fmtTime(result.wall_time)} icon={Clock} color="#818cf8" />
            <StatCard label="CPU Time" value={fmtTime(result.cpu_time)} icon={Cpu} color="#22d3ee" />
            <StatCard label="Memory Delta" value={fmtBytes(result.memory_delta)} icon={HardDrive}
              color={result.memory_delta > 10 * 1024 * 1024 ? '#f59e0b' : '#22c55e'} />
            <StatCard label="Peak Memory" value={fmtBytes(result.peak_memory)} icon={TrendingUp} color="#a78bfa" />
          </div>

          {/* Top functions table */}
          {result.top_functions && result.top_functions.length > 0 && (
            <div style={{
              borderRadius: 8, overflow: 'hidden',
              border: '1px solid var(--border, rgba(255,255,255,0.05))',
            }}>
              <div style={{
                padding: '6px 10px', fontSize: '0.68rem', fontWeight: 600,
                color: 'var(--fg-muted, #9ca3af)',
                background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
                borderBottom: '1px solid var(--border, rgba(255,255,255,0.05))',
              }}>
                Hot Functions
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto' }}>
                {result.top_functions.map((fn, i) => (
                  <div key={i} style={{
                    display: 'grid', gridTemplateColumns: '1fr auto auto',
                    gap: 8, padding: '5px 10px', alignItems: 'center',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    fontSize: '0.66rem',
                  }}>
                    <span style={{
                      color: 'var(--fg-primary, #e5e7eb)',
                      fontFamily: "'JetBrains Mono', monospace",
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }} title={fn.name}>
                      {fn.name}
                    </span>
                    <span style={{ color: '#818cf8', fontFamily: "'JetBrains Mono', monospace" }}>
                      {fmtTime(fn.cumulative_time || fn.time)}
                    </span>
                    <span style={{ color: 'var(--fg-dim, #6b7280)', fontFamily: "'JetBrains Mono', monospace" }}>
                      {fn.calls || fn.ncalls || '—'}×
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* History toggle */}
          {history.length > 1 && (
            <div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--fg-dim, #6b7280)', fontSize: '0.65rem',
                }}
              >
                {showHistory ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                Profile History ({history.length})
              </button>
              {showHistory && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 3 }}
                >
                  {history.map((h, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '4px 8px', borderRadius: 6,
                      background: i === 0 ? 'rgba(99,102,241,0.06)' : 'transparent',
                      fontSize: '0.62rem', color: 'var(--fg-muted, #9ca3af)',
                      cursor: 'pointer',
                    }} onClick={() => setResult(h)}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#818cf8' }}>
                        {fmtTime(h.wall_time)}
                      </span>
                      <span style={{ color: 'var(--fg-dim)' }}>{fmtBytes(h.memory_delta)}</span>
                      <span style={{ marginLeft: 'auto', color: 'var(--fg-dim)' }}>
                        {new Date(h.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </motion.div>
              )}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════
   2. BENCHMARK TAB
   ═══════════════════════════════════════════════ */

function BenchmarkTab({ cellId }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState(5);
  const [warmup, setWarmup] = useState(1);

  const runBenchmark = useCallback(async () => {
    if (!cellId) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(
        `${API}/cells/${cellId}/benchmark?runs=${runs}&warmup=${warmup}`,
        { method: 'POST' }
      );
      if (!res.ok) throw new Error(`Benchmark failed (${res.status})`);
      const data = await res.json();
      // Backend returns {benchmark: {mean_s, ...}, output: {...}, regressions: [...]}
      const b = data.benchmark || data;
      setResult({
        mean: b.mean_s || b.mean || 0,
        median: b.median_s || b.median || 0,
        std: b.std_s || b.std || 0,
        min: b.min_s || b.min || 0,
        max: b.max_s || b.max || 0,
        run_times: b.all_times || b.run_times || [],
        runs: b.runs || 0,
        regressions: data.regressions || [],
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [cellId, runs, warmup]);

  if (!cellId) return <EmptyState icon={BarChart2} message="Select a cell to benchmark its execution" />;

  const maxTime = result?.run_times ? Math.max(...result.run_times) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Config row */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <label style={{ fontSize: '0.65rem', color: 'var(--fg-dim)' }}>
          Runs
          <input
            type="number" min={1} max={100} value={runs}
            onChange={e => setRuns(+e.target.value || 5)}
            style={{
              width: 42, marginLeft: 4, padding: '3px 5px',
              borderRadius: 4, border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'var(--bg-secondary, rgba(255,255,255,0.03))',
              color: 'var(--fg-primary)', fontSize: '0.7rem',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          />
        </label>
        <label style={{ fontSize: '0.65rem', color: 'var(--fg-dim)' }}>
          Warmup
          <input
            type="number" min={0} max={10} value={warmup}
            onChange={e => setWarmup(+e.target.value || 0)}
            style={{
              width: 42, marginLeft: 4, padding: '3px 5px',
              borderRadius: 4, border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'var(--bg-secondary, rgba(255,255,255,0.03))',
              color: 'var(--fg-primary)', fontSize: '0.7rem',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          />
        </label>
        <button
          onClick={runBenchmark}
          disabled={loading}
          style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 14px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, rgba(34,211,238,0.15) 0%, rgba(99,102,241,0.15) 100%)',
            color: '#22d3ee', fontSize: '0.72rem', fontWeight: 600,
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          {loading ? <Spinner size={12} /> : <Play size={12} />}
          {loading ? 'Running…' : 'Benchmark'}
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={runBenchmark} />}

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {/* Timing stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
            <StatCard label="Mean" value={fmtTime(result.mean)} icon={BarChart2} color="#818cf8" />
            <StatCard label="Median" value={fmtTime(result.median)} icon={Activity} color="#22d3ee" />
            <StatCard label="Std Dev" value={fmtTime(result.std)} icon={TrendingUp} color="#a78bfa" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <StatCard label="Min" value={fmtTime(result.min)} icon={ChevronDown} color="#22c55e" />
            <StatCard label="Max" value={fmtTime(result.max)} icon={ChevronDown} color="#f59e0b" />
          </div>

          {/* Run times sparkline bar chart */}
          {result.run_times && result.run_times.length > 0 && (
            <div style={{
              padding: '10px 12px', borderRadius: 8,
              background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
              border: '1px solid var(--border, rgba(255,255,255,0.05))',
            }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--fg-dim)', marginBottom: 8, fontWeight: 600 }}>
                Run Times
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 60 }}>
                {result.run_times.map((t, i) => {
                  const pct = maxTime > 0 ? (t / maxTime) * 100 : 50;
                  const isMin = t === result.min;
                  const isMax = t === result.max;
                  return (
                    <motion.div
                      key={i}
                      initial={{ height: 0 }}
                      animate={{ height: `${Math.max(pct, 4)}%` }}
                      transition={{ duration: 0.3, delay: i * 0.05 }}
                      title={`Run ${i + 1}: ${fmtTime(t)}`}
                      style={{
                        flex: 1, borderRadius: '3px 3px 0 0',
                        background: isMax
                          ? 'linear-gradient(to top, rgba(245,158,11,0.3), rgba(245,158,11,0.6))'
                          : isMin
                            ? 'linear-gradient(to top, rgba(34,197,94,0.3), rgba(34,197,94,0.6))'
                            : 'linear-gradient(to top, rgba(99,102,241,0.2), rgba(99,102,241,0.5))',
                        cursor: 'default',
                        position: 'relative',
                      }}
                    />
                  );
                })}
              </div>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                marginTop: 4, fontSize: '0.55rem', color: 'var(--fg-dim)',
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                <span>1</span>
                <span>{result.run_times.length}</span>
              </div>
            </div>
          )}

          {/* Regression warning */}
          {result.regressions?.length > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 12px', borderRadius: 8,
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              fontSize: '0.7rem', color: '#fbbf24',
            }}>
              <AlertTriangle size={14} style={{ flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 600 }}>Regression Detected</div>
                <div style={{ fontSize: '0.62rem', color: '#f59e0b', marginTop: 2 }}>
                  {result.regressions[0]?.message || 'Performance variance exceeds threshold'}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════
   3. DATA QUALITY TAB
   ═══════════════════════════════════════════════ */

function DataQualityTab({ variables }) {
  const dfVars = useMemo(() => {
    if (!variables) return [];
    return Object.entries(variables)
      .filter(([, v]) => v.type === 'DataFrame' || v.type === 'dataframe' || v.dtype === 'DataFrame')
      .map(([name, v]) => ({ name, ...v }));
  }, [variables]);

  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState({});
  const [error, setError] = useState(null);

  const validate = useCallback(async (varName) => {
    setSelected(varName); setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/data-quality/${varName}`);
      if (!res.ok) throw new Error(`Validation failed (${res.status})`);
      const data = await res.json();
      // Backend returns {report: {overall_score, warnings, columns: [...]}, output: {...}}
      const r = data.report || data;
      const mapped = {
        score: r.overall_score ?? r.score ?? 0,
        warnings: r.warnings || [],
        column_issues: {},
        shape: r.shape || [0, 0],
        memory_mb: r.memory_mb || 0,
        duplicate_rows: r.duplicate_rows || 0,
      };
      // Build column_issues from columns array
      if (r.columns) {
        for (const col of r.columns) {
          if (col.issues && col.issues.length > 0) {
            mapped.column_issues[col.column] = col.issues;
          }
        }
      }
      setResult(prev => ({ ...prev, [varName]: mapped }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  if (dfVars.length === 0) {
    return <EmptyState icon={Database} message="No DataFrames in the current namespace. Run a cell that creates a DataFrame." />;
  }

  const activeResult = selected ? result[selected] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* DataFrame list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {dfVars.map(v => {
          const r = result[v.name];
          const isActive = selected === v.name;
          return (
            <button
              key={v.name}
              onClick={() => validate(v.name)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px', borderRadius: 8,
                border: isActive ? '1px solid rgba(99,102,241,0.3)' : '1px solid var(--border, rgba(255,255,255,0.05))',
                background: isActive ? 'rgba(99,102,241,0.06)' : 'var(--bg-secondary, rgba(255,255,255,0.02))',
                cursor: 'pointer', width: '100%', textAlign: 'left',
                transition: 'all 0.15s ease',
              }}
            >
              <Database size={13} style={{ color: 'var(--accent-light, #818cf8)', flexShrink: 0 }} />
              <span style={{
                fontSize: '0.72rem', fontWeight: 500,
                color: 'var(--fg-primary, #e5e7eb)',
                fontFamily: "'JetBrains Mono', monospace",
                flex: 1,
              }}>
                {v.name}
              </span>
              {loading && isActive && <Spinner size={12} />}
              {r && <QualityBadge score={r.score} />}
            </button>
          );
        })}
      </div>

      {error && <ErrorBanner message={error} onRetry={() => selected && validate(selected)} />}

      {/* Quality results */}
      {activeResult && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {/* Score ring */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '12px 0' }}>
            <QualityRing score={activeResult.score} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--fg-muted)', fontWeight: 600 }}>
                Data Quality Score
              </div>
              <div style={{
                height: 6, borderRadius: 3,
                background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
              }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${activeResult.score}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  style={{
                    height: '100%', borderRadius: 3,
                    background: `linear-gradient(90deg, ${scoreColor(activeResult.score)}, ${scoreColor(activeResult.score)}dd)`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Warnings */}
          {activeResult.warnings && activeResult.warnings.length > 0 && (
            <div style={{
              padding: '8px 10px', borderRadius: 8,
              background: 'rgba(245,158,11,0.06)',
              border: '1px solid rgba(245,158,11,0.15)',
              display: 'flex', flexDirection: 'column', gap: 4,
            }}>
              {activeResult.warnings.map((w, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.66rem' }}>
                  <AlertTriangle size={11} style={{ color: '#f59e0b', flexShrink: 0, marginTop: 1 }} />
                  <span style={{ color: '#fbbf24' }}>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Per-column issues */}
          {activeResult.column_issues && Object.keys(activeResult.column_issues).length > 0 && (
            <div style={{
              borderRadius: 8, overflow: 'hidden',
              border: '1px solid var(--border, rgba(255,255,255,0.05))',
            }}>
              <div style={{
                padding: '6px 10px', fontSize: '0.68rem', fontWeight: 600,
                color: 'var(--fg-muted, #9ca3af)',
                background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
                borderBottom: '1px solid var(--border, rgba(255,255,255,0.05))',
              }}>
                Column Issues
              </div>
              <div style={{ maxHeight: 220, overflow: 'auto' }}>
                {Object.entries(activeResult.column_issues).map(([col, issues]) => (
                  <ColumnIssueRow key={col} column={col} issues={issues} />
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}

function QualityBadge({ score }) {
  return (
    <span style={{
      fontSize: '0.62rem', fontWeight: 700, padding: '2px 6px',
      borderRadius: 4, fontFamily: "'JetBrains Mono', monospace",
      background: `${scoreColor(score)}18`,
      color: scoreColor(score),
    }}>
      {score}
    </span>
  );
}

function QualityRing({ score }) {
  const size = 56;
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.82rem', fontWeight: 700, color,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        {score}
      </div>
    </div>
  );
}

function ColumnIssueRow({ column, issues }) {
  const [open, setOpen] = useState(false);
  const issueList = Array.isArray(issues) ? issues : [issues];

  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          width: '100%', padding: '5px 10px', border: 'none',
          background: 'none', cursor: 'pointer', textAlign: 'left',
        }}
      >
        {open ? <ChevronDown size={10} style={{ color: 'var(--fg-dim)' }} /> : <ChevronRight size={10} style={{ color: 'var(--fg-dim)' }} />}
        <Hash size={10} style={{ color: '#818cf8' }} />
        <span style={{
          fontSize: '0.66rem', fontFamily: "'JetBrains Mono', monospace",
          color: 'var(--fg-primary, #e5e7eb)', flex: 1,
        }}>
          {column}
        </span>
        <span style={{
          fontSize: '0.58rem', padding: '1px 5px', borderRadius: 3,
          background: 'rgba(245,158,11,0.12)', color: '#f59e0b',
        }}>
          {issueList.length}
        </span>
      </button>
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          style={{ padding: '2px 10px 6px 32px' }}
        >
          {issueList.map((issue, i) => (
            <div key={i} style={{
              fontSize: '0.62rem', color: 'var(--fg-muted, #9ca3af)',
              padding: '2px 0', display: 'flex', alignItems: 'flex-start', gap: 5,
            }}>
              <span style={{ color: '#f59e0b' }}>•</span>
              <span>{typeof issue === 'string' ? issue : issue.message || JSON.stringify(issue)}</span>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════
   4. LINT / CODE ANALYSIS TAB
   ═══════════════════════════════════════════════ */

function LintTab({ cellId, onUpdateCell }) {
  const [loading, setLoading] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const analyze = useCallback(async () => {
    if (!cellId) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/cells/${cellId}/analyze`, { method: 'POST' });
      if (!res.ok) throw new Error(`Analysis failed (${res.status})`);
      const data = await res.json();
      setResult(data.report || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [cellId]);

  const autoFix = useCallback(async () => {
    if (!cellId) return;
    setFixing(true);
    try {
      const res = await fetch(`${API}/cells/${cellId}/auto-fix`, { method: 'POST' });
      if (!res.ok) throw new Error(`Auto-fix failed (${res.status})`);
      const data = await res.json();
      const fixedSrc = data.fixed_source || data.source;
      if (fixedSrc && onUpdateCell) {
        onUpdateCell(cellId, fixedSrc);
      }
      // Re-analyze after fix
      await analyze();
    } catch (e) {
      setError(e.message);
    } finally {
      setFixing(false);
    }
  }, [cellId, onUpdateCell, analyze]);

  if (!cellId) return <EmptyState icon={Zap} message="Select a cell to analyze its code quality" />;

  // Group suggestions by severity
  const grouped = useMemo(() => {
    if (!result?.suggestions) return {};
    const groups = {};
    for (const s of result.suggestions) {
      const sev = s.severity || 'info';
      if (!groups[sev]) groups[sev] = [];
      groups[sev].push(s);
    }
    // Sort by severity priority
    const order = ['security', 'error', 'performance', 'warning', 'style', 'info'];
    const sorted = {};
    for (const key of order) {
      if (groups[key]) sorted[key] = groups[key];
    }
    return sorted;
  }, [result]);

  const totalIssues = result?.suggestions?.length || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Actions */}
      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={analyze}
          disabled={loading}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
            padding: '8px 12px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, rgba(250,204,21,0.12) 0%, rgba(245,158,11,0.1) 100%)',
            color: '#fbbf24', fontSize: '0.72rem', fontWeight: 600,
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          {loading ? <Spinner size={12} /> : <Zap size={12} />}
          {loading ? 'Analyzing…' : 'Analyze Code'}
        </button>
        {totalIssues > 0 && (
          <button
            onClick={autoFix}
            disabled={fixing}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '8px 12px', borderRadius: 8, border: 'none',
              background: 'rgba(34,197,94,0.1)',
              color: '#22c55e', fontSize: '0.72rem', fontWeight: 600,
              cursor: fixing ? 'wait' : 'pointer',
            }}
          >
            {fixing ? <Spinner size={12} /> : <Wrench size={12} />}
            Auto-Fix
          </button>
        )}
      </div>

      {error && <ErrorBanner message={error} onRetry={analyze} />}

      {/* Summary bar */}
      {result && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 10px', borderRadius: 8,
            background: totalIssues === 0 ? 'rgba(34,197,94,0.06)' : 'var(--bg-secondary, rgba(255,255,255,0.02))',
            border: `1px solid ${totalIssues === 0 ? 'rgba(34,197,94,0.15)' : 'var(--border, rgba(255,255,255,0.05))'}`,
          }}
        >
          {totalIssues === 0 ? (
            <>
              <CheckCircle size={13} style={{ color: '#22c55e' }} />
              <span style={{ fontSize: '0.72rem', color: '#22c55e', fontWeight: 500 }}>No issues found</span>
            </>
          ) : (
            <>
              <AlertTriangle size={13} style={{ color: '#f59e0b' }} />
              <span style={{ fontSize: '0.72rem', color: 'var(--fg-muted)', fontWeight: 500 }}>
                {totalIssues} issue{totalIssues !== 1 ? 's' : ''} found
              </span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                {Object.entries(grouped).map(([sev, items]) => (
                  <span key={sev} style={{
                    fontSize: '0.58rem', padding: '1px 5px', borderRadius: 3,
                    background: `${severityColor(sev)}18`,
                    color: severityColor(sev),
                    fontWeight: 600,
                  }}>
                    {items.length} {sev}
                  </span>
                ))}
              </div>
            </>
          )}
        </motion.div>
      )}

      {/* Grouped suggestions */}
      {Object.entries(grouped).map(([severity, items]) => (
        <LintGroup key={severity} severity={severity} items={items} />
      ))}
    </div>
  );
}

function LintGroup({ severity, items }) {
  const [open, setOpen] = useState(true);
  const Icon = severityIcon(severity);
  const color = severityColor(severity);

  return (
    <div style={{
      borderRadius: 8, overflow: 'hidden',
      border: `1px solid ${color}22`,
    }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, width: '100%',
          padding: '6px 10px', border: 'none',
          background: `${color}08`, cursor: 'pointer',
        }}
      >
        {open ? <ChevronDown size={10} style={{ color }} /> : <ChevronRight size={10} style={{ color }} />}
        <Icon size={12} style={{ color }} />
        <span style={{ fontSize: '0.68rem', fontWeight: 600, color, textTransform: 'capitalize', flex: 1, textAlign: 'left' }}>
          {severity}
        </span>
        <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>{items.length}</span>
      </button>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ background: 'var(--bg-secondary, rgba(255,255,255,0.01))' }}
        >
          {items.map((item, i) => (
            <div key={i} style={{
              display: 'flex', gap: 8, padding: '5px 10px',
              borderTop: '1px solid rgba(255,255,255,0.03)',
              alignItems: 'flex-start',
            }}>
              {item.line != null && (
                <span style={{
                  fontSize: '0.6rem', color: 'var(--fg-dim)',
                  fontFamily: "'JetBrains Mono', monospace",
                  minWidth: 24, textAlign: 'right',
                  flexShrink: 0,
                }}>
                  L{item.line}
                </span>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.66rem', color: 'var(--fg-primary, #e5e7eb)' }}>
                  {item.message}
                </div>
                {item.rule && (
                  <span style={{
                    fontSize: '0.55rem', color: `${color}aa`,
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>
                    {item.rule}
                  </span>
                )}
              </div>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════
   5. HISTORY TAB
   ═══════════════════════════════════════════════ */

function HistoryTab({ cells }) {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [log, setLog] = useState([]);
  const [error, setError] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [cellTimeline, setCellTimeline] = useState(null);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/execution-history`);
      if (!res.ok) throw new Error(`Failed to fetch history (${res.status})`);
      const data = await res.json();
      // Remap stats from backend fields to frontend-expected fields
      const raw = data.stats || data;
      setStats({
        total_executions: raw.total_executions ?? 0,
        success_rate: (raw.success_rate_pct != null ? raw.success_rate_pct / 100 : raw.success_rate) ?? 0,
        total_time: raw.total_time_s ?? raw.total_time ?? 0,
        most_executed_cell: raw.most_executed_cell || null,
        most_executed_count: raw.most_executed_count || null,
      });
      // Map log entries to have consistent field names
      const logEntries = data.log || data.recent || [];
      setLog(logEntries.map(e => ({
        cell_id: e.cell_id,
        success: e.success,
        duration: e.duration_s ?? e.duration ?? 0,
        timestamp: e.timestamp,
      })));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCellTimeline = useCallback(async (cellId) => {
    setSelectedCell(cellId); setLoadingTimeline(true);
    try {
      const res = await fetch(`${API}/execution-history/${cellId}`);
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const tlData = await res.json();
      // Backend returns {timeline: {snapshots: [...]}} — remap to {executions: [...]}
      const tl = tlData.timeline || tlData;
      setCellTimeline({
        executions: (tl.snapshots || tl.executions || []).map(s => ({
          success: s.success,
          duration: s.duration_s ?? s.duration ?? 0,
          timestamp: s.timestamp,
        })),
      });
    } catch {
      setCellTimeline(null);
    } finally {
      setLoadingTimeline(false);
    }
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Refresh */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={fetchHistory}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', borderRadius: 6, border: 'none',
            background: 'rgba(99,102,241,0.08)', color: 'var(--accent-light, #818cf8)',
            fontSize: '0.65rem', cursor: 'pointer',
          }}
        >
          {loading ? <Spinner size={11} /> : <RefreshCw size={11} />}
          Refresh
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchHistory} />}

      {/* Stats cards */}
      {stats && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}
        >
          <StatCard label="Total Executions" value={stats.total_executions ?? '—'} icon={Play} color="#818cf8" />
          <StatCard
            label="Success Rate"
            value={stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : '—'}
            icon={CheckCircle}
            color={stats.success_rate >= 0.9 ? '#22c55e' : stats.success_rate >= 0.7 ? '#f59e0b' : '#ef4444'}
          />
          <StatCard label="Total Time" value={fmtTime(stats.total_time)} icon={Clock} color="#22d3ee" />
          <StatCard
            label="Most Executed"
            value={stats.most_executed_cell ? stats.most_executed_cell.slice(0, 8) : '—'}
            icon={Activity}
            color="#a78bfa"
            sub={stats.most_executed_count ? `${stats.most_executed_count} runs` : undefined}
          />
        </motion.div>
      )}

      {/* Recent log */}
      {log.length > 0 && (
        <div style={{
          borderRadius: 8, overflow: 'hidden',
          border: '1px solid var(--border, rgba(255,255,255,0.05))',
        }}>
          <div style={{
            padding: '6px 10px', fontSize: '0.68rem', fontWeight: 600,
            color: 'var(--fg-muted, #9ca3af)',
            background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
            borderBottom: '1px solid var(--border, rgba(255,255,255,0.05))',
          }}>
            Recent Executions
          </div>
          <div style={{ maxHeight: 240, overflow: 'auto' }}>
            {log.map((entry, i) => (
              <div
                key={i}
                onClick={() => entry.cell_id && fetchCellTimeline(entry.cell_id)}
                style={{
                  display: 'grid', gridTemplateColumns: '6px 1fr auto auto',
                  gap: 8, padding: '5px 10px', alignItems: 'center',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  cursor: entry.cell_id ? 'pointer' : 'default',
                  fontSize: '0.64rem',
                }}
              >
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: entry.status === 'success' || entry.success
                    ? '#22c55e'
                    : entry.status === 'error' || entry.error ? '#ef4444' : '#64748b',
                }} />
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  color: 'var(--fg-primary, #e5e7eb)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {entry.cell_id ? entry.cell_id.slice(0, 10) : '—'}
                </span>
                <span style={{ color: '#818cf8', fontFamily: "'JetBrains Mono', monospace" }}>
                  {fmtTime(entry.duration || entry.time)}
                </span>
                <span style={{ color: 'var(--fg-dim)', fontSize: '0.58rem' }}>
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cell timeline */}
      {selectedCell && (
        <div style={{
          borderRadius: 8, overflow: 'hidden',
          border: '1px solid rgba(99,102,241,0.2)',
        }}>
          <div style={{
            padding: '6px 10px', fontSize: '0.68rem', fontWeight: 600,
            color: 'var(--accent-light, #818cf8)',
            background: 'rgba(99,102,241,0.06)',
            borderBottom: '1px solid rgba(99,102,241,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span>
              Timeline: <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{selectedCell.slice(0, 10)}</span>
            </span>
            <button onClick={() => { setSelectedCell(null); setCellTimeline(null); }} style={{
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-dim)',
            }}>
              <X size={12} />
            </button>
          </div>
          {loadingTimeline ? (
            <div style={{ padding: 16, display: 'flex', justifyContent: 'center' }}><Spinner /></div>
          ) : cellTimeline && cellTimeline.executions ? (
            <div style={{ maxHeight: 160, overflow: 'auto' }}>
              {cellTimeline.executions.map((exec, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '4px 10px', fontSize: '0.62rem',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: '50%',
                    background: exec.success ? '#22c55e' : '#ef4444',
                  }} />
                  <span style={{ color: '#818cf8', fontFamily: "'JetBrains Mono', monospace" }}>
                    {fmtTime(exec.duration)}
                  </span>
                  <span style={{ color: 'var(--fg-dim)', marginLeft: 'auto', fontSize: '0.58rem' }}>
                    {exec.timestamp ? new Date(exec.timestamp).toLocaleString() : `Run #${i + 1}`}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 12, fontSize: '0.65rem', color: 'var(--fg-dim)', textAlign: 'center' }}>
              No timeline data available
            </div>
          )}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════
   6. ENVIRONMENT TAB
   ═══════════════════════════════════════════════ */

function EnvironmentTab() {
  const [loading, setLoading] = useState(true);
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [exporting, setExporting] = useState(false);
  const [installPkg, setInstallPkg] = useState('');
  const [installing, setInstalling] = useState(false);
  const [installMsg, setInstallMsg] = useState(null);

  const fetchSnapshot = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/environment/snapshot`);
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      setSnapshot(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSnapshot(); }, [fetchSnapshot]);

  const exportRequirements = useCallback(async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/environment/requirements`, { method: 'POST' });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const data = await res.json();
      // Copy to clipboard or trigger download
      if (data.content) {
        navigator.clipboard.writeText(data.content);
        setInstallMsg({ type: 'success', text: 'Requirements copied to clipboard!' });
      } else if (data.path) {
        setInstallMsg({ type: 'success', text: `Saved to ${data.path}` });
      }
    } catch (e) {
      setInstallMsg({ type: 'error', text: e.message });
    } finally {
      setExporting(false);
      setTimeout(() => setInstallMsg(null), 3000);
    }
  }, []);

  const installPackage = useCallback(async (action = 'install') => {
    if (!installPkg.trim()) return;
    setInstalling(true); setInstallMsg(null);
    try {
      const res = await fetch(`${API}/environment/packages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, package: installPkg.trim() }),
      });
      if (!res.ok) throw new Error(`${action} failed (${res.status})`);
      const data = await res.json();
      setInstallMsg({ type: 'success', text: data.message || `${action} complete` });
      setInstallPkg('');
      fetchSnapshot(); // Refresh packages
    } catch (e) {
      setInstallMsg({ type: 'error', text: e.message });
    } finally {
      setInstalling(false);
    }
  }, [installPkg, fetchSnapshot]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 32, color: 'var(--fg-dim)' }}>
        <Spinner size={16} />
        <span style={{ fontSize: '0.75rem' }}>Loading environment…</span>
      </div>
    );
  }

  if (error) return <ErrorBanner message={error} onRetry={fetchSnapshot} />;
  if (!snapshot) return <EmptyState icon={Package} message="Environment snapshot not available" />;

  const packages = snapshot.packages || [];
  const filteredPkgs = search
    ? packages.filter(p => (p.name || p).toLowerCase().includes(search.toLowerCase()))
    : packages;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* System info */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        <StatCard label="Python" value={snapshot.python_version || '—'} icon={Terminal} color="#818cf8" />
        <StatCard label="OS" value={snapshot.os || '—'} icon={Monitor} color="#22d3ee" />
        <StatCard label="Architecture" value={snapshot.architecture || snapshot.arch || '—'} icon={Cpu} color="#a78bfa" />
        <StatCard label="CPU Cores" value={snapshot.cpu_count || '—'} icon={Settings} color="#22c55e" />
      </div>

      {/* GPU info */}
      {snapshot.gpu && (
        <div style={{
          padding: '8px 12px', borderRadius: 8,
          background: 'rgba(168,85,247,0.06)',
          border: '1px solid rgba(168,85,247,0.15)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Cpu size={14} style={{ color: '#a78bfa' }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--fg-primary)', fontWeight: 500 }}>
              {snapshot.gpu.name || 'GPU'}
            </div>
            {snapshot.gpu.memory && (
              <div style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>
                {fmtBytes(snapshot.gpu.memory)} VRAM
              </div>
            )}
          </div>
        </div>
      )}

      {/* Install / uninstall */}
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <input
          value={installPkg}
          onChange={e => setInstallPkg(e.target.value)}
          placeholder="Package name…"
          onKeyDown={e => e.key === 'Enter' && installPackage('install')}
          style={{
            flex: 1, padding: '5px 8px', borderRadius: 6,
            border: '1px solid var(--border, rgba(255,255,255,0.1))',
            background: 'var(--bg-secondary, rgba(255,255,255,0.03))',
            color: 'var(--fg-primary)', fontSize: '0.68rem',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        />
        <button
          onClick={() => installPackage('install')}
          disabled={installing || !installPkg.trim()}
          style={{
            padding: '5px 8px', borderRadius: 6, border: 'none',
            background: 'rgba(34,197,94,0.12)', color: '#22c55e',
            fontSize: '0.65rem', fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 3,
          }}
        >
          {installing ? <Spinner size={10} /> : <Download size={10} />}
          Install
        </button>
        <button
          onClick={() => installPackage('uninstall')}
          disabled={installing || !installPkg.trim()}
          style={{
            padding: '5px 8px', borderRadius: 6, border: 'none',
            background: 'rgba(239,68,68,0.08)', color: '#ef4444',
            fontSize: '0.65rem', fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 3,
          }}
        >
          <Trash2 size={10} />
        </button>
      </div>

      {/* Install message */}
      {installMsg && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '5px 10px', borderRadius: 6,
            fontSize: '0.65rem',
            background: installMsg.type === 'success' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
            color: installMsg.type === 'success' ? '#22c55e' : '#ef4444',
            border: `1px solid ${installMsg.type === 'success' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}
        >
          {installMsg.text}
        </motion.div>
      )}

      {/* Packages list */}
      <div style={{
        borderRadius: 8, overflow: 'hidden',
        border: '1px solid var(--border, rgba(255,255,255,0.05))',
      }}>
        <div style={{
          padding: '6px 10px',
          background: 'var(--bg-secondary, rgba(255,255,255,0.02))',
          borderBottom: '1px solid var(--border, rgba(255,255,255,0.05))',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <Package size={11} style={{ color: 'var(--fg-dim)' }} />
          <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--fg-muted, #9ca3af)', flex: 1 }}>
            Packages ({packages.length})
          </span>
          <button
            onClick={exportRequirements}
            disabled={exporting}
            style={{
              display: 'flex', alignItems: 'center', gap: 3,
              padding: '2px 7px', borderRadius: 4, border: 'none',
              background: 'rgba(99,102,241,0.1)', color: 'var(--accent-light, #818cf8)',
              fontSize: '0.6rem', cursor: 'pointer',
            }}
          >
            {exporting ? <Spinner size={9} /> : <Download size={9} />}
            Export
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: '4px 8px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <div style={{ position: 'relative' }}>
            <Search size={11} style={{
              position: 'absolute', left: 7, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--fg-dim)',
            }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Filter packages…"
              style={{
                width: '100%', padding: '4px 8px 4px 24px',
                borderRadius: 4, border: '1px solid transparent',
                background: 'rgba(255,255,255,0.03)',
                color: 'var(--fg-primary)', fontSize: '0.65rem',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            />
          </div>
        </div>

        {/* Package list */}
        <div style={{ maxHeight: 260, overflow: 'auto' }}>
          {filteredPkgs.map((pkg, i) => {
            const name = typeof pkg === 'string' ? pkg : pkg.name;
            const version = typeof pkg === 'string' ? null : pkg.version;
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '3px 10px',
                borderBottom: '1px solid rgba(255,255,255,0.02)',
                fontSize: '0.64rem',
              }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  color: 'var(--fg-primary, #e5e7eb)',
                }}>
                  {name}
                </span>
                {version && (
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: 'var(--fg-dim, #6b7280)',
                    fontSize: '0.6rem',
                  }}>
                    {version}
                  </span>
                )}
              </div>
            );
          })}
          {filteredPkgs.length === 0 && (
            <div style={{ padding: 12, textAlign: 'center', fontSize: '0.65rem', color: 'var(--fg-dim)' }}>
              {search ? 'No matching packages' : 'No packages found'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
