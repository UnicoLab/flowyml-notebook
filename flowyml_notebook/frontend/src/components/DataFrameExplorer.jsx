import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  ChevronDown, ChevronRight, ChevronLeft,
  Table, Search, Download, Copy, BarChart3,
  PieChart, TrendingUp, Hash, Type as TypeIcon,
  AlertTriangle, Info, Columns, Grid3X3, Sparkles,
  CheckCircle, XCircle, Shield, Loader2, Upload,
  Brain, ScatterChart, Zap, Target, Scale, Box,
  Database, Activity, HardDrive, Wrench, Cpu, Play,
  Code, ArrowRight, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';



const PAGE_SIZE = 25;
const TABS = ['table', 'stats', 'charts', 'correlations', 'quality', 'insights', 'compare', 'smartprep', 'algorithms'];

export default function DataFrameExplorer({ data, metadata, variableName }) {
  const [expanded, setExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState('table');
  const [page, setPage] = useState(0);
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [search, setSearch] = useState('');
  const [selectedCol, setSelectedCol] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [aiInsights, setAiInsights] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [scatterX, setScatterX] = useState(null);
  const [scatterY, setScatterY] = useState(null);
  const [scatterColor, setScatterColor] = useState(null);

  // Parse data
  const rows = useMemo(() => {
    if (typeof data === 'string') {
      try { return JSON.parse(data); } catch { return []; }
    }
    return Array.isArray(data) ? data : [];
  }, [data]);

  const columns = useMemo(() => rows.length > 0 ? Object.keys(rows[0]) : [], [rows]);
  const totalRows = metadata?.rows || rows.length;

  // Client-side stats fallback — compute basic stats from available rows
  const localStats = useMemo(() => {
    if (rows.length === 0) return { stats: {}, histograms: {} };
    const statsObj = {};
    const histObj = {};
    for (const col of columns) {
      const vals = rows.map(r => r[col]).filter(v => v != null && v !== '');
      const nums = vals.filter(v => typeof v === 'number' && !isNaN(v));
      if (nums.length > 0) {
        const sorted = [...nums].sort((a, b) => a - b);
        const mean = nums.reduce((a, b) => a + b, 0) / nums.length;
        const variance = nums.reduce((a, b) => a + (b - mean) ** 2, 0) / nums.length;
        const std = Math.sqrt(variance);
        const q = (p) => { const i = p * (sorted.length - 1); const lo = Math.floor(i); return sorted[lo] + (sorted[Math.ceil(i)] - sorted[lo]) * (i - lo); };
        statsObj[col] = {
          type: 'numeric', count: nums.length, null_count: rows.length - vals.length,
          mean: +mean.toFixed(4), std: +std.toFixed(4),
          min: sorted[0], max: sorted[sorted.length - 1],
          q25: +q(0.25).toFixed(4), median: +q(0.5).toFixed(4), q75: +q(0.75).toFixed(4),
          zeros: nums.filter(v => v === 0).length,
          negative: nums.filter(v => v < 0).length,
        };
        // Histogram
        const binCount = Math.min(20, Math.max(5, Math.floor(nums.length / 5)));
        const minVal = sorted[0], maxVal = sorted[sorted.length - 1];
        const binWidth = (maxVal - minVal) / binCount || 1;
        const counts = new Array(binCount).fill(0);
        const edges = Array.from({ length: binCount + 1 }, (_, i) => +(minVal + i * binWidth).toFixed(4));
        for (const v of nums) {
          const idx = Math.min(Math.floor((v - minVal) / binWidth), binCount - 1);
          counts[idx]++;
        }
        histObj[col] = { counts, bin_edges: edges };
      } else {
        // Categorical
        const freq = {};
        for (const v of vals) { const k = String(v); freq[k] = (freq[k] || 0) + 1; }
        const topEntries = Object.entries(freq).sort((a, b) => b[1] - a[1]);
        const topValues = Object.fromEntries(topEntries.slice(0, 10));
        statsObj[col] = {
          type: 'categorical', count: vals.length, null_count: rows.length - vals.length,
          unique: topEntries.length,
          top_values: topValues,
          most_common: topEntries[0]?.[0] || null,
          most_common_pct: topEntries[0] ? +((topEntries[0][1] / vals.length) * 100).toFixed(1) : 0,
        };
      }
    }
    return { stats: statsObj, histograms: histObj };
  }, [rows, columns]);

  const stats = profile?.stats || (Object.keys(metadata?.stats || {}).length > 0 ? metadata.stats : localStats.stats);
  const histograms = profile?.histograms || (Object.keys(metadata?.histograms || {}).length > 0 ? metadata.histograms : localStats.histograms);
  const dtypes = profile?.dtypes || metadata?.dtypes || {};

  // Fetch full profiling data from backend
  useEffect(() => {
    if (variableName && ['stats', 'charts', 'correlations', 'quality', 'insights', 'compare'].includes(activeTab)) {
      setLoadingProfile(true);
      fetch(`/api/explore/${variableName}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setProfile(d); })
        .catch(() => {})
        .finally(() => setLoadingProfile(false));
    }
  }, [variableName, activeTab]);

  // Filter
  const filtered = useMemo(() => {
    if (!search) return rows;
    const q = search.toLowerCase();
    return rows.filter(row =>
      Object.values(row).some(v => String(v).toLowerCase().includes(q))
    );
  }, [rows, search]);

  // Sort
  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const va = a[sortCol], vb = b[sortCol];
      if (va == null) return 1; if (vb == null) return -1;
      const cmp = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortCol, sortDir]);

  // Paginate
  const pageCount = Math.ceil(sorted.length / PAGE_SIZE);
  const pageRows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = useCallback((col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
    setPage(0);
  }, [sortCol]);

  const copyToClipboard = () => {
    const csv = [columns.join(','), ...rows.map(r => columns.map(c => JSON.stringify(r[c] ?? '')).join(','))].join('\n');
    navigator.clipboard.writeText(csv);
  };

  const fetchAIInsights = async () => {
    if (!variableName || loadingAI) return;
    setLoadingAI(true);
    try {
      const res = await fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variable_name: variableName }),
      });
      if (res.ok) setAiInsights(await res.json());
    } catch (e) { /* ignore */ }
    finally { setLoadingAI(false); }
  };

  if (!rows.length) {
    const emptyColumns = metadata?.columns || columns;
    const emptyDtypes = metadata?.dtypes || {};
    return (
      <div className="df-container">
        <div className="df-header">
          <div className="df-header-info">
            <Table size={13} style={{ color: 'var(--fg-dim)' }} />
            <span style={{ color: 'var(--fg-muted)', fontWeight: 500 }}>
              {variableName || 'DataFrame'}
            </span>
            <span style={{ color: 'var(--fg-dim)' }}>0 × {emptyColumns?.length || 0}</span>
          </div>
        </div>
        <div style={{
          padding: '16px 20px',
          background: 'var(--bg-secondary)',
          textAlign: 'center',
        }}>
          <div style={{
            color: 'var(--fg-dim)',
            fontSize: '0.8rem',
            marginBottom: emptyColumns?.length > 0 ? 12 : 0,
          }}>
            Empty DataFrame — no rows to display
          </div>
          {emptyColumns?.length > 0 && (
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center',
            }}>
              {emptyColumns.map(col => (
                <span key={col} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '2px 8px', borderRadius: 6, fontSize: '0.65rem',
                  background: 'rgba(99,102,241,0.08)', color: 'var(--fg-muted)',
                  border: '1px solid rgba(99,102,241,0.12)',
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {col}
                  {emptyDtypes[col] && (
                    <span style={{ color: 'var(--fg-dim)', fontSize: '0.55rem' }}>
                      {emptyDtypes[col]}
                    </span>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  const tabIcons = {
    table: Table, stats: BarChart3, charts: PieChart,
    correlations: Grid3X3, quality: Shield,
    insights: Brain, compare: ScatterChart,
    smartprep: Wrench, algorithms: Cpu,
  };

  const numericCols = useMemo(() => columns.filter(c => stats[c]?.type === 'numeric'), [columns, stats]);

  return (
    <div className="df-container">
      {/* Header */}
      <div className="df-header">
        <div className="df-header-info">
          <button onClick={() => setExpanded(!expanded)} className="btn-icon" style={{ width: 24, height: 24 }}>
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          <Table size={13} style={{ color: 'var(--accent-light)' }} />
          <span style={{ color: 'var(--fg-primary)', fontWeight: 500 }}>
            {variableName || 'DataFrame'}
          </span>
          <span style={{ color: 'var(--fg-dim)' }}>{totalRows.toLocaleString()} × {columns.length}</span>
          {search && <span style={{ color: 'var(--accent-light)' }}>({filtered.length} matches)</span>}
        </div>
        <div className="df-header-actions">
          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 2, marginRight: 8 }}>
            {TABS.map(tab => {
              const Icon = tabIcons[tab] || Table;
              return (
                <button
                  key={tab}
                  className={`df-tab-btn ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                >
                  <Icon size={11} />
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              );
            })}
          </div>
          {activeTab === 'table' && (
            <input
              className="df-search"
              placeholder="Search..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
            />
          )}
          {/* AI Insights button */}
          {variableName && (
            <button
              className="df-tab-btn"
              style={{ background: loadingAI ? 'var(--accent-bg)' : aiInsights ? 'rgba(99,102,241,0.15)' : undefined }}
              onClick={fetchAIInsights}
              title="Get AI-powered insights"
              disabled={loadingAI}
            >
              {loadingAI ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
              AI
            </button>
          )}
          <button className="btn-icon" title="Copy as CSV" onClick={copyToClipboard} style={{ width: 28, height: 28 }}>
            <Copy size={12} />
          </button>
        </div>
      </div>

      {/* AI Insights Panel */}
      {aiInsights && (
        <div className="df-ai-panel">
          <div className="df-ai-header">
            <Sparkles size={13} style={{ color: 'var(--purple)' }} />
            <span>AI Insights</span>
            <button className="btn-icon" style={{ width: 20, height: 20, marginLeft: 'auto' }}
              onClick={() => setAiInsights(null)}>×</button>
          </div>
          <div className="df-ai-content">
            {aiInsights.summary && (
              <div className="df-ai-section">
                <strong>Summary</strong>
                <p>{aiInsights.summary}</p>
              </div>
            )}
            {aiInsights.insights && aiInsights.insights.length > 0 && (
              <div className="df-ai-section">
                <strong>Key Insights</strong>
                <ul>{aiInsights.insights.map((i, idx) => <li key={idx}>{i}</li>)}</ul>
              </div>
            )}
            {aiInsights.preprocessing && aiInsights.preprocessing.length > 0 && (
              <div className="df-ai-section">
                <strong>Preprocessing Suggestions</strong>
                <ul>{aiInsights.preprocessing.map((p, idx) => <li key={idx}>{p}</li>)}</ul>
              </div>
            )}
            {aiInsights.model_suggestions && aiInsights.model_suggestions.length > 0 && (
              <div className="df-ai-section">
                <strong>Model Recommendations</strong>
                <ul>{aiInsights.model_suggestions.map((m, idx) => <li key={idx}>{m}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}

      {expanded && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >

          {/* Table Tab */}
          {activeTab === 'table' && (
            <>
              <div className="overflow-auto" style={{ maxHeight: 360 }}>
                <table className="df-table">
                  <thead>
                    <tr>
                      <th style={{ width: 40, textAlign: 'center', color: 'var(--fg-dim)' }}>#</th>
                      {columns.map(col => (
                        <th key={col} onClick={() => handleSort(col)} onDoubleClick={() => setSelectedCol(col)}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            {isNumericType(dtypes[col]) ? <Hash size={9} style={{ opacity: 0.5 }} /> : <TypeIcon size={9} style={{ opacity: 0.5 }} />}
                            {col}
                          </span>
                          {sortCol === col && (
                            <span className="sort-indicator">{sortDir === 'asc' ? '▲' : '▼'}</span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((row, i) => (
                      <tr key={i}>
                        <td style={{ textAlign: 'center', color: 'var(--fg-dim)', fontSize: '0.65rem' }}>
                          {page * PAGE_SIZE + i}
                        </td>
                        {columns.map(col => (
                          <td key={col} className={getCellClass(row[col])}>
                            {formatCell(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {pageCount > 1 && (
                <div className="df-pagination">
                  <span>Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, sorted.length)} of {sorted.length}</span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button disabled={page === 0} onClick={() => setPage(0)}>⟨⟨</button>
                    <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>⟨</button>
                    <span style={{ padding: '0 8px', color: 'var(--fg-muted)' }}>{page + 1}/{pageCount}</span>
                    <button disabled={page >= pageCount - 1} onClick={() => setPage(p => p + 1)}>⟩</button>
                    <button disabled={page >= pageCount - 1} onClick={() => setPage(pageCount - 1)}>⟩⟩</button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Stats Tab */}
          {activeTab === 'stats' && (
            <div className="df-stats-panel">
              {loadingProfile ? (
                <div className="df-loading">
                  <Loader2 size={16} className="animate-spin" />
                  <span>Profiling DataFrame...</span>
                </div>
              ) : (
                <>
                  {/* Overview Deck (Bento Grid) */}
                  <SummaryDeck
                    totalRows={totalRows}
                    columns={columns}
                    stats={stats}
                    profile={profile}
                  />


                  {/* Column cards */}
                  <div className="df-column-grid">
                    {columns.map(col => {
                      const s = stats[col];
                      const hist = histograms[col];
                      if (!s) return null;
                      return (
                        <div key={col} className="df-col-card" onClick={() => setSelectedCol(col)}>
                          <div className="df-col-card-header">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              {s.type === 'numeric'
                                ? <Hash size={12} style={{ color: 'var(--cyan)' }} />
                                : <TypeIcon size={12} style={{ color: 'var(--purple)' }} />
                              }
                              <span className="df-col-name">{col}</span>
                            </div>
                            <span className="df-col-dtype">{dtypes[col] || s.type}</span>
                          </div>

                          {s.type === 'numeric' ? (
                            <>
                              {hist && <MiniHistogram data={hist} />}
                              <div className="df-stat-grid">
                                <StatItem label="mean" value={s.mean} />
                                <StatItem label="std" value={s.std} />
                                <StatItem label="min" value={s.min} />
                                <StatItem label="25%" value={s.q25} />
                                <StatItem label="50%" value={s.median} />
                                <StatItem label="75%" value={s.q75} />
                                <StatItem label="max" value={s.max} />
                                <StatItem label="nulls" value={s.null_count} warn={s.null_count > 0} />
                                {s.skew !== undefined && <StatItem label="skew" value={s.skew} />}
                                {s.kurtosis !== undefined && <StatItem label="kurt" value={s.kurtosis} />}
                              </div>
                            </>
                          ) : (
                            <>
                              {s.top_values && <MiniBarChart data={s.top_values} />}
                              <div className="df-stat-grid">
                                <StatItem label="unique" value={s.unique} />
                                <StatItem label="count" value={s.count} />
                                <StatItem label="nulls" value={s.null_count} warn={s.null_count > 0} />
                                {s.most_common && <StatItem label="top" value={s.most_common} />}
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Charts Tab */}
          {activeTab === 'charts' && (
            <div className="df-stats-panel">
              <div className="df-charts-grid">
                {columns.filter(c => histograms[c]).map(col => (
                  <div key={col} className="df-chart-card">
                    <div className="df-chart-card-title">
                      <BarChart3 size={12} style={{ color: 'var(--accent-light)' }} />
                      {col}
                    </div>
                    <LargeHistogram data={histograms[col]} label={col} />
                    {stats[col] && (
                      <div className="df-chart-stats-row">
                        <span>μ = {stats[col].mean}</span>
                        <span>σ = {stats[col].std}</span>
                        <span>range: [{stats[col].min}, {stats[col].max}]</span>
                      </div>
                    )}
                  </div>
                ))}
                {columns.filter(c => stats[c]?.type === 'categorical' && stats[c]?.top_values).map(col => (
                  <div key={col} className="df-chart-card">
                    <div className="df-chart-card-title">
                      <PieChart size={12} style={{ color: 'var(--purple)' }} />
                      {col}
                    </div>
                    <LargeBarChart data={stats[col].top_values} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Correlations Tab */}
          {activeTab === 'correlations' && (
            <div className="df-stats-panel">
              {loadingProfile ? (
                <div className="df-loading">
                  <Loader2 size={16} className="animate-spin" />
                  <span>Computing correlations...</span>
                </div>
              ) : (() => {
                // Use profile correlations, or compute locally
                const corrData = profile?.correlations || (() => {
                  const numCols = columns.filter(c => stats[c]?.type === 'numeric');
                  if (numCols.length < 2) return null;
                  // Compute Pearson correlation from local rows
                  const means = {};
                  const stds = {};
                  for (const c of numCols) {
                    const vals = rows.map(r => r[c]).filter(v => typeof v === 'number' && !isNaN(v));
                    means[c] = vals.reduce((a, b) => a + b, 0) / vals.length;
                    stds[c] = Math.sqrt(vals.reduce((a, b) => a + (b - means[c]) ** 2, 0) / vals.length) || 1;
                  }
                  const matrix = numCols.map(ci => numCols.map(cj => {
                    if (ci === cj) return 1;
                    const pairs = rows.filter(r => typeof r[ci] === 'number' && typeof r[cj] === 'number');
                    if (pairs.length < 3) return 0;
                    const sum = pairs.reduce((a, r) => a + ((r[ci] - means[ci]) / stds[ci]) * ((r[cj] - means[cj]) / stds[cj]), 0);
                    return +((sum / pairs.length).toFixed(4));
                  }));
                  return { columns: numCols, matrix };
                })();
                return corrData ? (
                  <CorrelationHeatmap correlations={corrData} />
                ) : (
                  <div className="df-empty-state">
                    <Grid3X3 size={24} />
                    <span>Need at least 2 numeric columns for correlation analysis</span>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Data Quality Tab */}
          {activeTab === 'quality' && (
            <div className="df-stats-panel">
              {loadingProfile ? (
                <div className="df-loading">
                  <Loader2 size={16} className="animate-spin" />
                  <span>Analyzing data quality...</span>
                </div>
              ) : (() => {
                const qualityData = profile?.data_quality || (() => {
                  if (rows.length === 0) return null;
                  const totalCells = rows.length * columns.length;
                  let totalNulls = 0;
                  const colNulls = {};
                  for (const col of columns) {
                    const nulls = rows.filter(r => r[col] == null || r[col] === '' || r[col] === undefined).length;
                    colNulls[col] = nulls;
                    totalNulls += nulls;
                  }
                  // Detect duplicates
                  const seen = new Set();
                  let dupes = 0;
                  for (const r of rows) {
                    const key = JSON.stringify(r);
                    if (seen.has(key)) dupes++;
                    seen.add(key);
                  }
                  return {
                    completeness: totalCells > 0 ? +((1 - totalNulls / totalCells) * 100).toFixed(1) : 100,
                    total_nulls: totalNulls,
                    duplicate_rows: dupes,
                    duplicate_pct: +(dupes / rows.length * 100).toFixed(1),
                    columns_with_nulls: Object.values(colNulls).filter(n => n > 0).length,
                    constant_columns: columns.filter(c => {
                      const unique = new Set(rows.map(r => r[c]));
                      return unique.size <= 1;
                    }),
                    high_cardinality: columns.filter(c => {
                      const unique = new Set(rows.map(r => r[c]));
                      return unique.size > 50 && stats[c]?.type === 'categorical';
                    }),
                  };
                })();
                return qualityData ? (
                  <DataQualityPanel quality={qualityData} stats={stats} columns={columns} totalRows={totalRows} />
                ) : (
                  <div className="df-empty-state">
                    <Shield size={24} />
                    <span>No data available for quality analysis</span>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ML Insights Tab */}
          {activeTab === 'insights' && (
            <div className="df-stats-panel">
              {loadingProfile ? (
                <div className="df-loading">
                  <Loader2 size={16} className="animate-spin" />
                  <span>Analyzing data for ML insights...</span>
                </div>
              ) : (
                <MLInsightsPanel
                  mlInsights={profile?.ml_insights || null}
                  stats={stats}
                  columns={columns}
                  rows={rows}
                  numericCols={numericCols}
                />
              )}
            </div>
          )}

          {/* Compare / Scatter Tab */}
          {activeTab === 'compare' && (
            <div className="df-stats-panel">
              <ScatterPlotPanel
                rows={rows}
                columns={columns}
                numericCols={numericCols}
                stats={stats}
                scatterX={scatterX}
                scatterY={scatterY}
                scatterColor={scatterColor}
                setScatterX={setScatterX}
                setScatterY={setScatterY}
                setScatterColor={setScatterColor}
              />
            </div>
          )}

          {/* SmartPrep Advisor Tab */}
          {activeTab === 'smartprep' && (
            <div className="df-stats-panel">
              <SmartPrepPanel variableName={variableName} columns={columns} />
            </div>
          )}

          {/* Algorithm Matchmaker Tab */}
          {activeTab === 'algorithms' && (
            <div className="df-stats-panel">
              <AlgorithmMatchPanel variableName={variableName} columns={columns} />
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}

/* ===== Summary Deck (Bento Grid) ===== */
function SummaryDeck({ totalRows, columns, stats, profile }) {
  const nullCount = columns.reduce((sum, c) => sum + (stats[c]?.null_count || 0), 0);
  const numericCount = columns.filter(c => stats[c]?.type === 'numeric').length;
  
  return (
    <div className="df-summary-deck">
      <div className="summary-card">
        <div className="summary-card-icon"><Database size={16} /></div>
        <div className="summary-card-value">{totalRows.toLocaleString()}</div>
        <div className="summary-card-label">Total Rows</div>
        <div className="summary-card-trend" style={{ color: 'var(--success)' }}>
          <Activity size={10} /> Live Dataset
        </div>
      </div>
      
      <div className="summary-card">
        <div className="summary-card-icon"><Columns size={16} /></div>
        <div className="summary-card-value">{columns.length}</div>
        <div className="summary-card-label">Columns</div>
        <div className="summary-card-trend">
          {numericCount} numeric • {columns.length - numericCount} cat
        </div>
      </div>

      <div className="summary-card">
        <div className="summary-card-icon" style={{ background: nullCount > 0 ? 'var(--error-glow)' : undefined, color: nullCount > 0 ? 'var(--error)' : undefined }}>
          <Shield size={16} />
        </div>
        <div className="summary-card-value">{nullCount.toLocaleString()}</div>
        <div className="summary-card-label">Missing Values</div>
        <div className="summary-card-trend" style={{ color: nullCount > 0 ? 'var(--error)' : 'var(--success)' }}>
          {nullCount > 0 ? 'Attention required' : 'Clean dataset'}
        </div>
      </div>

      {profile?.memory_bytes && (
        <div className="summary-card">
          <div className="summary-card-icon"><HardDrive size={16} /></div>
          <div className="summary-card-value">{formatBytes(profile.memory_bytes)}</div>
          <div className="summary-card-label">Memory Impact</div>
          <div className="summary-card-trend">RAM usage</div>
        </div>
      )}
    </div>
  );
}


/* ===== Correlation Heatmap ===== */
function CorrelationHeatmap({ correlations }) {
  const { columns, matrix } = correlations;
  const n = columns.length;

  const getColor = (val) => {
    const abs = Math.abs(val);
    if (val > 0) return `rgba(99, 102, 241, ${abs * 0.8})`;   // indigo for positive
    return `rgba(244, 63, 94, ${abs * 0.8})`;                  // rose for negative
  };

  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--fg-muted)', marginBottom: 8, display: 'flex', gap: 12, alignItems: 'center' }}>
        <span>Pearson Correlation Matrix</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(244, 63, 94, 0.6)' }} />
          <span style={{ fontSize: '0.6rem' }}>Negative</span>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(200,200,200,0.1)' }} />
          <span style={{ fontSize: '0.6rem' }}>Zero</span>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(99, 102, 241, 0.6)' }} />
          <span style={{ fontSize: '0.6rem' }}>Positive</span>
        </div>
      </div>
      <div className="corr-grid" style={{ display: 'grid', gridTemplateColumns: `80px repeat(${n}, 1fr)`, gap: 1 }}>
        {/* Header row */}
        <div />
        {columns.map(col => (
          <div key={col} className="corr-header" title={col}>
            {col.length > 8 ? col.slice(0, 7) + '…' : col}
          </div>
        ))}
        {/* Data rows */}
        {matrix.map((row, i) => (
          <React.Fragment key={i}>
            <div className="corr-label" title={columns[i]}>
              {columns[i].length > 10 ? columns[i].slice(0, 9) + '…' : columns[i]}
            </div>
            {row.map((val, j) => (
              <div key={j} className="corr-cell" style={{ background: getColor(val) }}
                title={`${columns[i]} × ${columns[j]}: ${val}`}>
                {Math.abs(val) > 0.01 ? val.toFixed(2) : ''}
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>

      {/* Strong correlations summary */}
      <StrongCorrelations columns={columns} matrix={matrix} />
    </div>
  );
}

function StrongCorrelations({ columns, matrix }) {
  const pairs = [];
  for (let i = 0; i < matrix.length; i++) {
    for (let j = i + 1; j < matrix[i].length; j++) {
      const val = matrix[i][j];
      if (Math.abs(val) >= 0.5) {
        pairs.push({ a: columns[i], b: columns[j], val });
      }
    }
  }

  if (pairs.length === 0) return null;

  pairs.sort((a, b) => Math.abs(b.val) - Math.abs(a.val));

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: '0.7rem', color: 'var(--fg-muted)', marginBottom: 6, fontWeight: 600 }}>
        Notable Correlations (|r| ≥ 0.5)
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {pairs.slice(0, 8).map(({ a, b, val }, i) => (
          <div key={i} className="corr-pair-badge" style={{
            borderColor: val > 0 ? 'rgba(99,102,241,0.3)' : 'rgba(244,63,94,0.3)',
            color: val > 0 ? 'var(--accent-light)' : '#f43f5e',
          }}>
            {a} ↔ {b}: <strong>{val.toFixed(2)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== Data Quality Panel ===== */
function DataQualityPanel({ quality, stats, columns, totalRows }) {
  const completeness = quality.completeness || 100;
  const completeColor = completeness >= 95 ? 'var(--green)' : completeness >= 80 ? '#f59e0b' : '#ef4444';

  return (
    <div>
      {/* Quality Score */}
      <div className="df-quality-score">
        <div className="quality-ring" style={{ '--pct': `${completeness}%`, '--color': completeColor }}>
          <span className="quality-value">{completeness}%</span>
          <span className="quality-label">Complete</span>
        </div>
        <div className="quality-metrics">
          <QualityMetric icon={CheckCircle} label="Total Rows" value={totalRows.toLocaleString()} color="var(--green)" />
          <QualityMetric icon={XCircle} label="Null Values" value={quality.total_nulls} color={quality.total_nulls > 0 ? '#f59e0b' : 'var(--green)'} />
          <QualityMetric icon={Copy} label="Duplicate Rows" value={`${quality.duplicate_rows} (${quality.duplicate_pct}%)`} color={quality.duplicate_rows > 0 ? '#f59e0b' : 'var(--green)'} />
          <QualityMetric icon={Columns} label="Cols with Nulls" value={quality.columns_with_nulls} color={quality.columns_with_nulls > 0 ? '#f59e0b' : 'var(--green)'} />
        </div>
      </div>

      {/* Issues */}
      {(quality.constant_columns?.length > 0 || quality.high_cardinality?.length > 0) && (
        <div className="df-quality-issues">
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 6 }}>
            <AlertTriangle size={11} style={{ display: 'inline', verticalAlign: -1, marginRight: 4 }} />
            Issues Detected
          </div>
          {quality.constant_columns?.length > 0 && (
            <div className="quality-issue warn">
              <span>Constant columns (no variance):</span>
              <code>{quality.constant_columns.join(', ')}</code>
            </div>
          )}
          {quality.high_cardinality?.length > 0 && (
            <div className="quality-issue info">
              <span>High cardinality (50+ unique):</span>
              <code>{quality.high_cardinality.join(', ')}</code>
            </div>
          )}
        </div>
      )}

      {/* Per-column null breakdown */}
      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 6 }}>
          Column Completeness
        </div>
        {columns.map(col => {
          const nulls = stats[col]?.null_count || 0;
          const pct = totalRows > 0 ? ((totalRows - nulls) / totalRows * 100) : 100;
          return (
            <div key={col} className="quality-bar-row">
              <span className="quality-bar-label" title={col}>
                {col.length > 16 ? col.slice(0, 14) + '…' : col}
              </span>
              <div className="quality-bar-track">
                <div className="quality-bar-fill" style={{
                  width: `${pct}%`,
                  background: pct >= 95 ? 'var(--green)' : pct >= 80 ? '#f59e0b' : '#ef4444',
                }} />
              </div>
              <span className="quality-bar-pct">{pct.toFixed(0)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function QualityMetric({ icon: Icon, label, value, color }) {
  return (
    <div className="quality-metric">
      <Icon size={14} style={{ color }} />
      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--fg-primary)' }}>{value}</div>
        <div style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>{label}</div>
      </div>
    </div>
  );
}

/* ===== Sub-components ===== */

function StatItem({ label, value, warn }) {
  return (
    <div className="df-stat-item">
      <span className="df-stat-label">{label}</span>
      <span className={`df-stat-value ${warn ? 'warn' : ''}`}>
        {typeof value === 'number' ? (Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4)) : value}
        {warn && <AlertTriangle size={9} style={{ marginLeft: 3 }} />}
      </span>
    </div>
  );
}

function MiniHistogram({ data }) {
  const { counts, bin_edges } = data;
  const max = Math.max(...counts);
  return (
    <div className="mini-histogram">
      {counts.map((c, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${Math.max(2, (c / max) * 32)}px` }}
          className="mini-hist-bar"
          title={`${bin_edges[i].toFixed(2)} – ${bin_edges[i + 1].toFixed(2)}: ${c}`}
        />
      ))}
    </div>
  );
}

function MiniBarChart({ data }) {
  const entries = Object.entries(data);
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="mini-bar-chart">
      {entries.slice(0, 5).map(([label, val]) => (
        <div key={label} className="mini-bar-row">
          <span className="mini-bar-label" title={label}>
            {label.length > 12 ? label.slice(0, 10) + '…' : label}
          </span>
          <div className="mini-bar-track">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(val / max) * 100}%` }}
              className="mini-bar-fill"
            />
          </div>
          <span className="mini-bar-count">{val}</span>
        </div>
      ))}
    </div>
  );
}


function LargeHistogram({ data, label }) {
  const { counts, bin_edges } = data;
  const max = Math.max(...counts);
  return (
    <div className="large-histogram">
      <div className="hist-bars">
        {counts.map((c, i) => (
          <div key={i} className="hist-bar-col">
            <div
              className="hist-bar"
              style={{ height: `${Math.max(2, (c / max) * 100)}%` }}
            />
            {i % Math.max(1, Math.floor(counts.length / 5)) === 0 && (
              <span className="hist-label">{bin_edges[i].toFixed(1)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function LargeBarChart({ data }) {
  const entries = Object.entries(data);
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="large-bar-chart">
      {entries.map(([label, val]) => (
        <div key={label} className="large-bar-row">
          <span className="large-bar-label" title={label}>
            {label.length > 16 ? label.slice(0, 14) + '…' : label}
          </span>
          <div className="large-bar-track">
            <div className="large-bar-fill" style={{ width: `${(val / max) * 100}%` }}>
              <span className="large-bar-value">{val}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ===== Resizable Chart Wrapper ===== */
function ResizableChart({ title, children, defaultHeight = 200 }) {
  const [height, setHeight] = useState(defaultHeight);
  const [expanded, setExpanded] = useState(false);
  const [dragging, setDragging] = useState(false);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    const startY = e.clientY;
    const startH = height;
    const onMove = (ev) => { setHeight(Math.max(100, startH + ev.clientY - startY)); };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); setDragging(false); };
    setDragging(true);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [height]);

  return (
    <div className={`resizable-chart ${expanded ? 'expanded' : ''}`}
      style={{ height: expanded ? '80vh' : height, position: expanded ? 'fixed' : 'relative',
        top: expanded ? '10vh' : undefined, left: expanded ? '10vw' : undefined,
        width: expanded ? '80vw' : '100%', zIndex: expanded ? 1000 : undefined,
        background: 'var(--bg-primary)', borderRadius: 8, border: '1px solid var(--border-subtle)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
      {expanded && <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: -1 }} onClick={() => setExpanded(false)} />}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-secondary)' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--fg-muted)' }}>{title}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn-icon" onClick={() => setExpanded(!expanded)} title={expanded ? 'Collapse' : 'Expand'} style={{ width: 20, height: 20 }}>
            {expanded ? <XCircle size={10} /> : <Box size={10} />}
          </button>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
        {children}
      </div>
      {!expanded && (
        <div onMouseDown={handleMouseDown} style={{ height: 6, cursor: 'ns-resize', background: dragging ? 'var(--accent-bg)' : 'transparent', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ width: 30, height: 2, borderRadius: 1, background: 'var(--fg-dim)' }} />
        </div>
      )}
    </div>
  );
}

/* ===== ML Insights Panel ===== */
function MLInsightsPanel({ mlInsights, stats, columns, rows, numericCols }) {
  const ml = mlInsights || {};
  const featureTypes = ml.feature_types || {};
  const scaling = ml.scaling || {};
  const suggestions = ml.suggestions || [];
  const potentialTargets = ml.potential_targets || [];
  const featureVariance = ml.feature_variance || {};
  const summary = ml.summary || {};

  const typeColors = {
    continuous: '#6366f1', binary: '#10b981', ordinal: '#f59e0b',
    nominal: '#8b5cf6', temporal: '#06b6d4', high_cardinality: '#ef4444',
  };
  const iconMap = { recommended: '✅', alternative: '🔄', caution: '⚠️', warning: '🚨', preprocessing: '🔧' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Dataset Summary */}
      {summary.n_samples && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
          {[
            { label: 'Samples', value: summary.n_samples?.toLocaleString(), icon: '📊' },
            { label: 'Features', value: summary.n_features, icon: '🔢' },
            { label: 'Numeric', value: summary.n_numeric, icon: '#️⃣' },
            { label: 'Categorical', value: summary.n_categorical, icon: '🏷️' },
            { label: 'Samples/Feature', value: summary.samples_per_feature, icon: '📐' },
            { label: 'Memory', value: `${summary.memory_mb} MB`, icon: '💾' },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{ padding: '8px 12px', borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '1rem' }}>{icon}</span>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--fg-primary)' }}>{value}</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Feature Types */}
      {Object.keys(featureTypes).length > 0 && (
        <ResizableChart title="Feature Type Classification" defaultHeight={120}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {Object.entries(featureTypes).map(([col, type]) => (
              <span key={col} style={{ padding: '3px 8px', borderRadius: 12, fontSize: '0.65rem', fontWeight: 500, background: `${typeColors[type] || '#666'}18`, color: typeColors[type] || '#666', border: `1px solid ${typeColors[type] || '#666'}30` }}>
                {col} <span style={{ opacity: 0.7 }}>• {type}</span>
              </span>
            ))}
          </div>
        </ResizableChart>
      )}

      {/* Outlier Summary */}
      {(() => {
        const outlierCols = Object.entries(stats).filter(([, s]) => s.outliers > 0);
        if (outlierCols.length === 0) return null;
        return (
          <ResizableChart title="⚡ Outlier Detection (IQR Method)" defaultHeight={160}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {outlierCols.map(([col, s]) => (
                <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', borderRadius: 6, background: s.outlier_pct > 5 ? 'rgba(239,68,68,0.08)' : 'var(--bg-secondary)' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--fg-primary)', minWidth: 100 }}>{col}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--border-subtle)', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', height: '100%', width: `${Math.min(100, s.outlier_pct * 5)}%`, background: s.outlier_pct > 10 ? '#ef4444' : s.outlier_pct > 5 ? '#f59e0b' : '#6366f1', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: '0.65rem', fontWeight: 600, color: s.outlier_pct > 5 ? '#ef4444' : 'var(--fg-muted)', minWidth: 60 }}>
                    {s.outliers} ({s.outlier_pct}%)
                  </span>
                  <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>
                    [{s.lower_fence?.toFixed(1)}, {s.upper_fence?.toFixed(1)}]
                  </span>
                </div>
              ))}
            </div>
          </ResizableChart>
        );
      })()}

      {/* Scaling Recommendations */}
      {Object.keys(scaling).length > 0 && (
        <ResizableChart title="⚖️ Scaling Recommendations" defaultHeight={160}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {Object.entries(scaling).map(([col, rec]) => {
              const methodColors = { log_transform: '#f59e0b', robust_scaler: '#8b5cf6', standard_scaler: '#6366f1', none: '#10b981' };
              return (
                <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', borderRadius: 6, background: 'var(--bg-secondary)' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--fg-primary)', minWidth: 100 }}>{col}</span>
                  <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: '0.6rem', fontWeight: 600, background: `${methodColors[rec.method] || '#666'}18`, color: methodColors[rec.method] || '#666' }}>
                    {rec.method === 'none' ? '✓ No scaling needed' : rec.method.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)', flex: 1 }}>{rec.reason}</span>
                </div>
              );
            })}
          </div>
        </ResizableChart>
      )}

      {/* Target Variable Detection */}
      {potentialTargets.length > 0 && (
        <ResizableChart title="🎯 Potential Target Variables" defaultHeight={120}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {potentialTargets.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 8, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)' }}>
                <Target size={14} style={{ color: '#6366f1' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--fg-primary)' }}>{t.column}</span>
                <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: '0.6rem', fontWeight: 600, background: t.type === 'classification' ? 'rgba(16,185,129,0.15)' : 'rgba(99,102,241,0.15)', color: t.type === 'classification' ? '#10b981' : '#6366f1' }}>
                  {t.type} ({t.n_classes} classes)
                </span>
                <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>{t.reason}</span>
              </div>
            ))}
          </div>
        </ResizableChart>
      )}

      {/* Algorithm Suggestions */}
      {suggestions.length > 0 && (
        <ResizableChart title="🤖 Algorithm Suggestions" defaultHeight={180}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {suggestions.map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 10px', borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '1rem', lineHeight: 1 }}>{iconMap[s.icon] || '💡'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--fg-primary)' }}>{s.algo}</div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--fg-muted)', marginTop: 2 }}>{s.reason}</div>
                  {s.pairs && (
                    <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {s.pairs.map((p, j) => (
                        <span key={j} style={{ fontSize: '0.55rem', padding: '1px 6px', borderRadius: 6, background: 'rgba(244,63,94,0.1)', color: '#f43f5e' }}>
                          {p.a} ↔ {p.b}: r={p.corr.toFixed(2)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ResizableChart>
      )}

      {/* Feature Variance Ranking */}
      {Object.keys(featureVariance).length > 0 && (
        <ResizableChart title="📊 Feature Variance Ranking" defaultHeight={160}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {Object.entries(featureVariance).map(([col, info]) => (
              <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 8px' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 500, color: 'var(--fg-primary)', minWidth: 100 }}>{col}</span>
                <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--border-subtle)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${info.normalized * 100}%`, background: `linear-gradient(90deg, #6366f1, #8b5cf6)`, borderRadius: 4, transition: 'width 0.3s ease' }} />
                </div>
                <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)', minWidth: 70, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace" }}>
                  {info.variance.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </ResizableChart>
      )}
    </div>
  );
}

/* ===== Scatter Plot / Column Comparison ===== */
function ScatterPlotPanel({ rows, columns, numericCols, stats, scatterX, scatterY, scatterColor, setScatterX, setScatterY, setScatterColor }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [chartHeight, setChartHeight] = useState(350);

  // Default to first two numeric columns
  const xCol = scatterX || numericCols[0];
  const yCol = scatterY || numericCols[1] || numericCols[0];

  const categoricalCols = useMemo(() => columns.filter(c => stats[c]?.type !== 'numeric'), [columns, stats]);

  // Generate color palette
  const PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#84cc16'];
  const colorMap = useMemo(() => {
    if (!scatterColor) return null;
    const unique = [...new Set(rows.map(r => String(r[scatterColor])))];
    const map = {};
    unique.forEach((v, i) => { map[v] = PALETTE[i % PALETTE.length]; });
    return map;
  }, [rows, scatterColor]);

  // Compute plot bounds
  const points = useMemo(() => {
    if (!xCol || !yCol) return [];
    return rows.filter(r => typeof r[xCol] === 'number' && typeof r[yCol] === 'number')
      .map((r, i) => ({ x: r[xCol], y: r[yCol], color: scatterColor ? (colorMap?.[String(r[scatterColor])] || '#6366f1') : '#6366f1', label: scatterColor ? String(r[scatterColor]) : '', idx: i, row: r }));
  }, [rows, xCol, yCol, scatterColor, colorMap]);

  const bounds = useMemo(() => {
    if (points.length === 0) return { xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
    const xs = points.map(p => p.x);
    const ys = points.map(p => p.y);
    const pad = 0.05;
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const xPad = (xMax - xMin) * pad || 1;
    const yPad = (yMax - yMin) * pad || 1;
    return { xMin: xMin - xPad, xMax: xMax + xPad, yMin: yMin - yPad, yMax: yMax + yPad };
  }, [points]);

  const W = 600, H = chartHeight;
  const margin = { top: 20, right: 20, bottom: 35, left: 55 };
  const plotW = W - margin.left - margin.right;
  const plotH = H - margin.top - margin.bottom;

  const toSvgX = (v) => margin.left + (v - bounds.xMin) / (bounds.xMax - bounds.xMin) * plotW;
  const toSvgY = (v) => margin.top + plotH - (v - bounds.yMin) / (bounds.yMax - bounds.yMin) * plotH;

  // Grid lines
  const xTicks = useMemo(() => {
    const range = bounds.xMax - bounds.xMin;
    const step = Math.pow(10, Math.floor(Math.log10(range))) || 1;
    const ticks = [];
    for (let v = Math.ceil(bounds.xMin / step) * step; v <= bounds.xMax; v += step) ticks.push(v);
    return ticks.slice(0, 8);
  }, [bounds]);

  const yTicks = useMemo(() => {
    const range = bounds.yMax - bounds.yMin;
    const step = Math.pow(10, Math.floor(Math.log10(range))) || 1;
    const ticks = [];
    for (let v = Math.ceil(bounds.yMin / step) * step; v <= bounds.yMax; v += step) ticks.push(v);
    return ticks.slice(0, 8);
  }, [bounds]);

  if (numericCols.length < 2) {
    return (
      <div className="df-empty-state">
        <ScatterChart size={24} />
        <span>Need at least 2 numeric columns for comparison plots</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.7rem', color: 'var(--fg-muted)' }}>
          X Axis:
          <select value={xCol || ''} onChange={e => setScatterX(e.target.value)} style={{ fontSize: '0.7rem', padding: '3px 6px', borderRadius: 6, background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border-subtle)' }}>
            {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.7rem', color: 'var(--fg-muted)' }}>
          Y Axis:
          <select value={yCol || ''} onChange={e => setScatterY(e.target.value)} style={{ fontSize: '0.7rem', padding: '3px 6px', borderRadius: 6, background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border-subtle)' }}>
            {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.7rem', color: 'var(--fg-muted)' }}>
          Color by:
          <select value={scatterColor || ''} onChange={e => setScatterColor(e.target.value || null)} style={{ fontSize: '0.7rem', padding: '3px 6px', borderRadius: 6, background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border-subtle)' }}>
            <option value="">None</option>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <span style={{ fontSize: '0.6rem', color: 'var(--fg-dim)' }}>{points.length} points</span>
      </div>

      {/* Scatter Plot SVG */}
      <ResizableChart title={`${xCol} vs ${yCol}${scatterColor ? ` (colored by ${scatterColor})` : ''}`} defaultHeight={380}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%' }}>
          {/* Grid */}
          {xTicks.map(v => (
            <g key={`x${v}`}>
              <line x1={toSvgX(v)} x2={toSvgX(v)} y1={margin.top} y2={margin.top + plotH} stroke="var(--border-subtle)" strokeWidth={0.5} />
              <text x={toSvgX(v)} y={H - 5} textAnchor="middle" fontSize={9} fill="var(--fg-dim)">{v > 1000 ? `${(v/1000).toFixed(0)}k` : v.toFixed(1)}</text>
            </g>
          ))}
          {yTicks.map(v => (
            <g key={`y${v}`}>
              <line x1={margin.left} x2={margin.left + plotW} y1={toSvgY(v)} y2={toSvgY(v)} stroke="var(--border-subtle)" strokeWidth={0.5} />
              <text x={margin.left - 5} y={toSvgY(v) + 3} textAnchor="end" fontSize={9} fill="var(--fg-dim)">{v > 1000 ? `${(v/1000).toFixed(0)}k` : v.toFixed(1)}</text>
            </g>
          ))}
          {/* Axes */}
          <line x1={margin.left} x2={margin.left + plotW} y1={margin.top + plotH} y2={margin.top + plotH} stroke="var(--fg-dim)" strokeWidth={1} />
          <line x1={margin.left} x2={margin.left} y1={margin.top} y2={margin.top + plotH} stroke="var(--fg-dim)" strokeWidth={1} />
          {/* Axis labels */}
          <text x={margin.left + plotW / 2} y={H - 0} textAnchor="middle" fontSize={10} fontWeight={600} fill="var(--fg-muted)">{xCol}</text>
          <text x={12} y={margin.top + plotH / 2} textAnchor="middle" fontSize={10} fontWeight={600} fill="var(--fg-muted)" transform={`rotate(-90, 12, ${margin.top + plotH / 2})`}>{yCol}</text>
          {/* Points */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={toSvgX(p.x)}
              cy={toSvgY(p.y)}
              r={hoveredPoint === i ? 5 : 3}
              fill={p.color}
              opacity={hoveredPoint === i ? 1 : 0.6}
              stroke={hoveredPoint === i ? '#fff' : 'none'}
              strokeWidth={1.5}
              style={{ cursor: 'pointer', transition: 'r 0.15s, opacity 0.15s' }}
              onMouseEnter={() => setHoveredPoint(i)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
          {/* Tooltip */}
          {hoveredPoint !== null && points[hoveredPoint] && (() => {
            const p = points[hoveredPoint];
            const tx = toSvgX(p.x), ty = toSvgY(p.y);
            const tooltipText = `${xCol}: ${p.x.toFixed(3)}, ${yCol}: ${p.y.toFixed(3)}${p.label ? `, ${scatterColor}: ${p.label}` : ''}`;
            return (
              <g>
                <rect x={tx + 8} y={ty - 18} width={tooltipText.length * 5.5 + 12} height={20} rx={4} fill="var(--bg-elevated)" stroke="var(--border-subtle)" />
                <text x={tx + 14} y={ty - 4} fontSize={9} fill="var(--fg-primary)" fontFamily="'JetBrains Mono', monospace">{tooltipText}</text>
              </g>
            );
          })()}
        </svg>
      </ResizableChart>

      {/* Color Legend */}
      {colorMap && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '4px 0' }}>
          {Object.entries(colorMap).map(([label, color]) => (
            <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.6rem', color: 'var(--fg-muted)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Quick Correlation Info */}
      {xCol && yCol && xCol !== yCol && (() => {
        const xVals = rows.filter(r => typeof r[xCol] === 'number' && typeof r[yCol] === 'number');
        if (xVals.length < 3) return null;
        const mx = xVals.reduce((a, r) => a + r[xCol], 0) / xVals.length;
        const my = xVals.reduce((a, r) => a + r[yCol], 0) / xVals.length;
        const sx = Math.sqrt(xVals.reduce((a, r) => a + (r[xCol] - mx) ** 2, 0) / xVals.length) || 1;
        const sy = Math.sqrt(xVals.reduce((a, r) => a + (r[yCol] - my) ** 2, 0) / xVals.length) || 1;
        const r = xVals.reduce((a, row) => a + ((row[xCol] - mx) / sx) * ((row[yCol] - my) / sy), 0) / xVals.length;
        const strength = Math.abs(r) > 0.7 ? 'Strong' : Math.abs(r) > 0.4 ? 'Moderate' : 'Weak';
        const dir = r > 0 ? 'positive' : 'negative';
        return (
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '6px 10px', borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
            <TrendingUp size={14} style={{ color: '#6366f1' }} />
            <span style={{ fontSize: '0.7rem', color: 'var(--fg-muted)' }}>
              Pearson r = <strong style={{ color: r > 0 ? '#6366f1' : '#f43f5e' }}>{r.toFixed(3)}</strong>
              {' '}— {strength} {dir} correlation
            </span>
          </div>
        );
      })()}
    </div>
  );
}

/* ===== SmartPrep Advisor Panel ===== */
function SmartPrepPanel({ variableName, columns }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [target, setTarget] = useState('');
  const [appliedSet, setAppliedSet] = useState(new Set());

  const fetchSuggestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/smartprep/${variableName}${target ? `?target=${target}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [variableName, target]);

  useEffect(() => { fetchSuggestions(); }, [fetchSuggestions]);

  const handleApplyCode = useCallback((code, index) => {
    // Dispatch event to insert code cell
    window.dispatchEvent(new CustomEvent('flowyml:insert-cell', {
      detail: { code, below: true },
    }));
    setAppliedSet(prev => new Set([...prev, index]));
  }, []);

  const severityColors = {
    high: { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)', text: '#ef4444', icon: '🔴' },
    medium: { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', text: '#f59e0b', icon: '🟡' },
    low: { bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.2)', text: '#6366f1', icon: '🔵' },
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, gap: 8 }}>
        <Loader2 size={16} className="animate-spin" style={{ color: '#6366f1' }} />
        <span style={{ fontSize: '0.75rem', color: 'var(--fg-muted)' }}>Analyzing data quality...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#ef4444', fontSize: '0.75rem' }}>
        <AlertCircle size={16} style={{ marginBottom: 4 }} />
        <div>{error}</div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Wrench size={16} style={{ color: '#6366f1' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--fg-primary)' }}>
            SmartPrep Advisor
          </span>
          <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: '0.65rem', fontWeight: 600,
            background: data.total_issues > 5 ? 'rgba(239,68,68,0.15)' : data.total_issues > 0 ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
            color: data.total_issues > 5 ? '#ef4444' : data.total_issues > 0 ? '#f59e0b' : '#10b981',
          }}>
            {data.total_issues} {data.total_issues === 1 ? 'issue' : 'issues'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select value={target} onChange={e => setTarget(e.target.value)}
            style={{ fontSize: '0.65rem', padding: '3px 6px', borderRadius: 6, background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border-subtle)' }}>
            <option value="">No target column</option>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={fetchSuggestions} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
            <Loader2 size={12} style={{ color: 'var(--fg-dim)' }} />
          </button>
        </div>
      </div>

      {/* Suggestions */}
      {data.suggestions.length === 0 ? (
        <div style={{ padding: 30, textAlign: 'center' }}>
          <CheckCircle size={24} style={{ color: '#10b981', margin: '0 auto 8px' }} />
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#10b981' }}>Data looks clean!</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--fg-dim)', marginTop: 4 }}>
            No major preprocessing issues detected.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.suggestions.map((s, i) => {
            const sev = severityColors[s.severity] || severityColors.low;
            const applied = appliedSet.has(i);
            return (
              <motion.div key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: applied ? 0.5 : 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                style={{
                  padding: '10px 12px', borderRadius: 10,
                  background: sev.bg, border: `1px solid ${sev.border}`,
                  opacity: applied ? 0.5 : 1,
                }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ fontSize: '0.8rem', lineHeight: 1, flexShrink: 0 }}>{sev.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--fg-primary)', marginBottom: 2 }}>
                      {s.title}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--fg-muted)', lineHeight: 1.4 }}>
                      {s.reason}
                    </div>
                    {/* Code Preview */}
                    <pre style={{
                      marginTop: 8, padding: '6px 10px', borderRadius: 6,
                      background: 'rgba(0,0,0,0.3)', fontSize: '0.6rem',
                      color: '#a5b4fc', fontFamily: "'JetBrains Mono', monospace",
                      overflowX: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.5,
                    }}>
                      {s.code}
                    </pre>
                    {/* Action */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
                      <button
                        onClick={() => handleApplyCode(s.code, i)}
                        disabled={applied}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 4,
                          padding: '4px 10px', borderRadius: 6, fontSize: '0.65rem', fontWeight: 600,
                          background: applied ? 'rgba(16,185,129,0.15)' : 'rgba(99,102,241,0.15)',
                          color: applied ? '#10b981' : '#6366f1',
                          border: `1px solid ${applied ? 'rgba(16,185,129,0.3)' : 'rgba(99,102,241,0.3)'}`,
                          cursor: applied ? 'default' : 'pointer',
                        }}>
                        {applied ? <><CheckCircle size={11} /> Applied</> : <><Play size={11} /> Generate Cell</>}
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Apply All Button */}
      {data.suggestions.length > 1 && appliedSet.size < data.suggestions.length && (
        <button
          onClick={() => {
            data.suggestions.forEach((s, i) => {
              if (!appliedSet.has(i)) handleApplyCode(s.code, i);
            });
          }}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            padding: '8px 16px', borderRadius: 8, fontSize: '0.75rem', fontWeight: 600,
            background: 'rgba(99,102,241,0.12)', color: '#6366f1',
            border: '1px solid rgba(99,102,241,0.25)', cursor: 'pointer',
          }}>
          <Zap size={13} /> Apply All Fixes ({data.suggestions.length - appliedSet.size} remaining)
        </button>
      )}
    </div>
  );
}

/* ===== Algorithm Matchmaker Panel ===== */
function AlgorithmMatchPanel({ variableName, columns }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [target, setTarget] = useState('');
  const [expandedAlgo, setExpandedAlgo] = useState(null);

  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/algorithm-match/${variableName}${target ? `?target=${target}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [variableName, target]);

  useEffect(() => { fetchRecommendations(); }, [fetchRecommendations]);

  const handleGeneratePipeline = useCallback((code) => {
    window.dispatchEvent(new CustomEvent('flowyml:insert-cell', {
      detail: { code, below: true },
    }));
  }, []);

  const taskTypeConfig = {
    classification: { color: '#10b981', icon: '🎯', label: 'Classification' },
    regression: { color: '#6366f1', icon: '📈', label: 'Regression' },
    clustering: { color: '#f59e0b', icon: '🔮', label: 'Clustering' },
  };

  const speedColors = { fast: '#10b981', medium: '#f59e0b', slow: '#ef4444' };
  const interpretColors = { high: '#10b981', medium: '#f59e0b', low: '#ef4444' };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, gap: 8 }}>
        <Loader2 size={16} className="animate-spin" style={{ color: '#6366f1' }} />
        <span style={{ fontSize: '0.75rem', color: 'var(--fg-muted)' }}>Analyzing data characteristics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#ef4444', fontSize: '0.75rem' }}>
        <AlertCircle size={16} style={{ marginBottom: 4 }} />
        <div>{error}</div>
      </div>
    );
  }

  if (!data) return null;

  const tc = taskTypeConfig[data.task_type] || taskTypeConfig.clustering;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Cpu size={16} style={{ color: '#6366f1' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--fg-primary)' }}>
            Algorithm Matchmaker
          </span>
        </div>
        <select value={target} onChange={e => setTarget(e.target.value)}
          style={{ fontSize: '0.65rem', padding: '3px 6px', borderRadius: 6, background: 'var(--bg-secondary)', color: 'var(--fg-primary)', border: '1px solid var(--border-subtle)' }}>
          <option value="">Select target column</option>
          {columns.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Task Type Detection */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10,
        background: `${tc.color}10`, border: `1px solid ${tc.color}25`,
      }}>
        <span style={{ fontSize: '1.2rem' }}>{tc.icon}</span>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: tc.color }}>{tc.label} Task Detected</div>
          <div style={{ fontSize: '0.6rem', color: 'var(--fg-dim)', marginTop: 2 }}>
            {data.data_characteristics.n_samples.toLocaleString()} samples × {data.data_characteristics.n_features} features
            {data.target_info?.classes && ` · ${data.target_info.classes} classes`}
            {data.target_info?.balanced !== undefined && (
              <span style={{ color: data.target_info.balanced ? '#10b981' : '#f59e0b' }}>
                {' '}· {data.target_info.balanced ? 'Balanced' : 'Imbalanced'}
              </span>
            )}
          </div>
        </div>
      </div>

      {!target && (
        <div style={{
          padding: '8px 12px', borderRadius: 8, fontSize: '0.65rem',
          background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
          color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <Info size={12} /> Select a target column above for supervised learning recommendations
        </div>
      )}

      {/* Algorithm Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.recommendations.map((algo, i) => {
          const isExpanded = expandedAlgo === i;
          return (
            <motion.div key={algo.name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                borderRadius: 10, overflow: 'hidden',
                background: i === 0 ? 'rgba(99,102,241,0.06)' : 'var(--bg-secondary)',
                border: `1px solid ${i === 0 ? 'rgba(99,102,241,0.2)' : 'var(--border-subtle)'}`,
              }}>
              {/* Card Header */}
              <div
                onClick={() => setExpandedAlgo(isExpanded ? null : i)}
                style={{
                  padding: '10px 12px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                {/* Rank badge */}
                <div style={{
                  width: 24, height: 24, borderRadius: '50%', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', fontWeight: 800,
                  background: i === 0 ? '#6366f1' : i === 1 ? '#8b5cf6' : 'var(--bg-primary)',
                  color: i < 2 ? '#fff' : 'var(--fg-muted)',
                  border: i >= 2 ? '1px solid var(--border-subtle)' : 'none',
                  flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--fg-primary)' }}>{algo.name}</span>
                    {i === 0 && (
                      <span style={{ padding: '1px 6px', borderRadius: 8, fontSize: '0.55rem', fontWeight: 700,
                        background: 'rgba(99,102,241,0.2)', color: '#6366f1' }}>
                        Best Match
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 3 }}>
                    <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 6,
                      background: `${speedColors[algo.speed]}15`, color: speedColors[algo.speed] }}>
                      ⚡ {algo.speed}
                    </span>
                    <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 6,
                      background: `${interpretColors[algo.interpretability]}15`, color: interpretColors[algo.interpretability] }}>
                      👁 {algo.interpretability}
                    </span>
                    <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 6,
                      background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>
                      {algo.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
                {/* Score bar */}
                <div style={{ width: 60, textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: algo.score >= 90 ? '#10b981' : algo.score >= 80 ? '#6366f1' : '#f59e0b' }}>
                    {algo.score}%
                  </div>
                  <div style={{ height: 4, borderRadius: 2, background: 'var(--border-subtle)', marginTop: 3 }}>
                    <div style={{
                      height: '100%', borderRadius: 2, width: `${algo.score}%`,
                      background: algo.score >= 90 ? '#10b981' : algo.score >= 80 ? '#6366f1' : '#f59e0b',
                    }} />
                  </div>
                </div>
                <ChevronDown size={14} style={{
                  color: 'var(--fg-dim)', transform: isExpanded ? 'rotate(180deg)' : 'none',
                  transition: 'transform 0.2s',
                }} />
              </div>

              {/* Expanded Details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    style={{ overflow: 'hidden' }}>
                    <div style={{ padding: '0 12px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {/* Why this algorithm */}
                      <div>
                        <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 4 }}>
                          Why this algorithm?
                        </div>
                        {algo.reasons.map((r, j) => (
                          <div key={j} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.65rem', color: 'var(--fg-primary)', padding: '2px 0' }}>
                            <CheckCircle size={10} style={{ color: '#10b981', flexShrink: 0, marginTop: 2 }} />
                            <span>{r}</span>
                          </div>
                        ))}
                      </div>
                      {/* Caveats */}
                      {algo.caveats && algo.caveats.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 4 }}>
                            Watch out for
                          </div>
                          {algo.caveats.map((c, j) => (
                            <div key={j} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.65rem', color: '#f59e0b', padding: '2px 0' }}>
                              <AlertTriangle size={10} style={{ flexShrink: 0, marginTop: 2 }} />
                              <span>{c}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Code Preview */}
                      {algo.code && (
                        <>
                          <pre style={{
                            padding: '8px 10px', borderRadius: 6,
                            background: 'rgba(0,0,0,0.3)', fontSize: '0.6rem',
                            color: '#a5b4fc', fontFamily: "'JetBrains Mono', monospace",
                            overflowX: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.5,
                          }}>
                            {algo.code}
                          </pre>
                          <button
                            onClick={() => handleGeneratePipeline(algo.code)}
                            style={{
                              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                              padding: '6px 12px', borderRadius: 6, fontSize: '0.7rem', fontWeight: 600,
                              background: 'rgba(99,102,241,0.15)', color: '#6366f1',
                              border: '1px solid rgba(99,102,241,0.3)', cursor: 'pointer',
                            }}>
                            <Play size={12} /> Generate Pipeline Cell
                          </button>
                        </>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/* ===== Utilities ===== */

function isNumericType(dtype) {
  if (!dtype) return false;
  return dtype.includes('int') || dtype.includes('float') || dtype.includes('num');
}

function getCellClass(val) {
  if (val === null || val === undefined) return 'null';
  if (typeof val === 'number') return 'number';
  if (typeof val === 'boolean') return val ? 'bool-true' : 'bool-false';
  return '';
}

function formatCell(val) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val.toLocaleString();
    return val.toFixed(4);
  }
  if (typeof val === 'boolean') return val ? '✓' : '✗';
  const s = String(val);
  return s.length > 50 ? s.slice(0, 47) + '...' : s;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
