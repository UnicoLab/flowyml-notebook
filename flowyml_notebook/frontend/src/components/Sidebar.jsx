import React, { useState, useMemo } from 'react';
import {
  Variable, GitBranch, FileCode, List, Search, Package,
  Server, Cpu, Database, ChevronDown, ChevronRight,
  Circle, ArrowRight, Zap, Terminal, Globe, FileText,
  FolderOpen, History, Github
} from 'lucide-react';
import NotebookManager from './NotebookManager';
import FilesExplorer from './FilesExplorer';
import VersionHistory from './VersionHistory';
import ConnectionConfig from './ConnectionConfig';
import CellRecipes from './CellRecipes';

const TABS = [
  { id: 'notebooks', label: 'Notebooks', shortLabel: 'Notes', icon: FileText, group: 'core' },
  { id: 'files', label: 'Files', shortLabel: 'Files', icon: FolderOpen, group: 'core' },
  { id: 'recipes', label: 'Recipes', shortLabel: 'Snips', icon: Package, group: 'core' },
  { id: 'variables', label: 'Variables', shortLabel: 'Vars', icon: Variable, group: 'analysis' },
  { id: 'graph', label: 'Graph', shortLabel: 'Graph', icon: GitBranch, group: 'analysis' },
  { id: 'outline', label: 'Outline', shortLabel: 'Cells', icon: List, group: 'analysis' },
  { id: 'history', label: 'History', shortLabel: 'Hist', icon: History, group: 'system' },
  { id: 'github', label: 'GitHub', shortLabel: 'Git', icon: Github, group: 'system' },
  { id: 'env', label: 'Environment', shortLabel: 'Env', icon: Terminal, group: 'system' },
];

export default function Sidebar({ variables, graph, cells, metadata, connected, onInsertRecipe, onOpenNotebook, onScrollToCell, saveStatus }) {
  const [activeTab, setActiveTab] = useState('variables');
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsed, setCollapsed] = useState(false);

  const groups = useMemo(() => {
    const g = {};
    TABS.forEach(tab => {
      if (!g[tab.group]) g[tab.group] = [];
      g[tab.group].push(tab);
    });
    return g;
  }, []);

  return (
    <div className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Icon Rail — with micro-labels */}
      <div className="sidebar-icon-rail">
        {Object.entries(groups).map(([groupName, tabs], gi) => (
          <React.Fragment key={groupName}>
            {gi > 0 && <div className="sidebar-rail-divider" />}
            <div className="sidebar-rail-group-label">{groupName}</div>
            {tabs.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id && !collapsed;
              return (
                <button
                  key={tab.id}
                  className={`sidebar-rail-btn ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    if (activeTab === tab.id && !collapsed) {
                      setCollapsed(true);
                    } else {
                      setActiveTab(tab.id);
                      setCollapsed(false);
                    }
                  }}
                  title={tab.label}
                >
                  <Icon size={16} />
                  <span className="sidebar-rail-label">{tab.shortLabel || tab.label.slice(0, 5)}</span>
                  {isActive && <div className="sidebar-rail-indicator" />}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {/* Panel Content — shown when not collapsed */}
      {!collapsed && (
        <div className="sidebar-panel">
          {/* Panel Header */}
          <div className="sidebar-panel-header">
            <span className="sidebar-panel-title">
              {TABS.find(t => t.id === activeTab)?.label}
            </span>
          </div>

          {/* Search (for variables and outline) */}
          {(activeTab === 'variables' || activeTab === 'outline') && (
            <div className="sidebar-panel-search">
              <Search size={13} className="sidebar-search-icon" />
              <input
                className="sidebar-search-input"
                placeholder={activeTab === 'variables' ? 'Filter variables...' : 'Search cells...'}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
          )}

          {/* Tab content */}
          <div className="sidebar-panel-content">
            {activeTab === 'notebooks' && (
              <NotebookManager currentNotebookName={metadata?.name} onOpenNotebook={onOpenNotebook} saveStatus={saveStatus} />
            )}
            {activeTab === 'files' && (
              <FilesExplorer />
            )}
            {activeTab === 'recipes' && (
              <CellRecipes onInsertRecipe={onInsertRecipe} />
            )}
            {activeTab === 'variables' && (
              <VariablesPanel variables={variables} search={searchQuery} />
            )}
            {activeTab === 'graph' && (
              <GraphPanel graph={graph} cells={cells} />
            )}
            {activeTab === 'history' && (
              <VersionHistory />
            )}
            {activeTab === 'outline' && (
              <OutlinePanel cells={cells} search={searchQuery} onScrollToCell={onScrollToCell} />
            )}
            {activeTab === 'github' && (
              <GitHubPanel />
            )}
            {activeTab === 'env' && (
              <div style={{ overflow: 'auto', height: '100%' }}>
                <ConnectionConfig />
                <EnvironmentPanel metadata={metadata} connected={connected} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── GitHub Panel ────────────────────────────────────────────────── */

function GitHubPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [showInit, setShowInit] = useState(false);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/github/status');
      const data = await res.json();
      setStatus(data);
    } catch { setStatus({ connected: false, error: 'Failed to connect' }); }
    setLoading(false);
  };

  React.useEffect(() => { loadStatus(); }, []);

  const handleInit = async () => {
    if (!repoUrl) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/github/init?repo_url=${encodeURIComponent(repoUrl)}`, { method: 'POST' });
      await res.json();
      setShowInit(false);
      loadStatus();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handlePush = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/github/push', { method: 'POST' });
      const data = await res.json();
      if (data.pushed) loadStatus();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handlePull = async () => {
    setLoading(true);
    try {
      await fetch('/api/github/pull', { method: 'POST' });
      loadStatus();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (!status || !status.connected) {
    return (
      <div className="sidebar-empty-state">
        <Github size={28} className="sidebar-empty-icon" />
        <span className="sidebar-empty-title">Connect GitHub</span>
        <p className="sidebar-empty-desc">
          Link a GitHub repository to enable team collaboration, versioning, and shared recipes.
        </p>

        {showInit ? (
          <div className="github-init-form">
            <input
              className="github-init-input"
              placeholder="https://github.com/team/notebooks"
              value={repoUrl}
              onChange={e => setRepoUrl(e.target.value)}
            />
            <div className="github-init-actions">
              <button className="btn-primary-sm" onClick={handleInit} disabled={loading || !repoUrl}>
                {loading ? 'Connecting...' : 'Connect'}
              </button>
              <button className="btn-ghost-sm" onClick={() => setShowInit(false)}>Cancel</button>
            </div>
          </div>
        ) : (
          <button className="btn-primary-sm" onClick={() => setShowInit(true)}>
            <Github size={12} /> Connect Repository
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      {/* Status card */}
      <div className="github-status-card">
        <div className="github-status-header">
          <div className="github-status-dot connected" />
          <span className="github-status-label">Connected</span>
          <span className="github-status-repo">{status.repo}</span>
        </div>

        <div className="github-status-row">
          <GitBranch size={12} />
          <span className="github-branch-name">{status.branch || 'main'}</span>
          {status.has_changes && (
            <span className="github-changes-badge">{status.changes?.length} changes</span>
          )}
        </div>

        {status.last_commit && (
          <div className="github-commit-info">
            <span className="github-commit-sha">{status.last_commit.sha}</span>
            <span className="github-commit-msg">{status.last_commit.message}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="github-actions">
        <button className="github-action-btn push" onClick={handlePush} disabled={loading}>
          Push
        </button>
        <button className="github-action-btn pull" onClick={handlePull} disabled={loading}>
          Pull
        </button>
        <button className="github-action-btn refresh" onClick={loadStatus} disabled={loading}>
          ↻
        </button>
      </div>

      {/* Changes list */}
      {status.changes?.length > 0 && (
        <CollapsibleSection title={`Changes (${status.changes.length})`} defaultOpen>
          {status.changes.map((change, i) => (
            <div key={i} className="github-change-item">
              <span className={`github-change-status ${change.status === 'M' ? 'modified' : change.status === 'A' ? 'added' : 'deleted'}`}>
                {change.status}
              </span>
              <span className="github-change-file">{change.file}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}
    </div>
  );
}

/* ── Variables Panel ─────────────────────────────────────────────── */

function VariablesPanel({ variables, search }) {
  const entries = useMemo(() => {
    const all = Object.entries(variables || {});
    if (!search) return all;
    const q = search.toLowerCase();
    return all.filter(([name]) => name.toLowerCase().includes(q));
  }, [variables, search]);

  if (entries.length === 0) {
    return (
      <div className="sidebar-empty-state">
        <Variable size={24} className="sidebar-empty-icon" />
        <span className="sidebar-empty-title">
          {search ? 'No matches' : 'No variables yet'}
        </span>
        {!search && <p className="sidebar-empty-desc">Run a cell to see variables here</p>}
      </div>
    );
  }

  // Group by type
  const grouped = {};
  entries.forEach(([name, info]) => {
    const type = info.type || 'other';
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push({ name, ...info });
  });

  // Sort: DataFrames first, then models, then rest
  const typeOrder = ['DataFrame', 'Series', 'ndarray', 'Pipeline', 'Model', 'dict', 'list', 'int', 'float', 'str'];
  const sortedGroups = Object.entries(grouped).sort(([a], [b]) => {
    const ai = typeOrder.indexOf(a), bi = typeOrder.indexOf(b);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  const typeIcons = {
    DataFrame: { icon: Database, color: 'var(--cyan-400, #22d3ee)' },
    Series: { icon: Database, color: 'var(--cyan-400, #22d3ee)' },
    ndarray: { icon: Cpu, color: 'var(--purple-400, #c084fc)' },
    Pipeline: { icon: Zap, color: 'var(--indigo-400, #818cf8)' },
    list: { icon: List, color: 'var(--amber-400, #fbbf24)' },
    dict: { icon: Package, color: 'var(--emerald-400, #34d399)' },
  };

  return (
    <div>
      {sortedGroups.map(([type, vars]) => (
        <CollapsibleSection key={type} title={`${type} (${vars.length})`} defaultOpen>
          {vars.map(v => {
            const tc = typeIcons[type];
            return (
              <div key={v.name} className="variable-item group">
                <div className="variable-item-left">
                  {tc && <tc.icon size={11} style={{ color: tc.color }} />}
                  <span className="variable-name">{v.name}</span>
                </div>
                <div className="variable-item-right">
                  {v.shape && (
                    <span className="variable-meta">[{v.shape.join('×')}]</span>
                  )}
                  {v.length !== undefined && !v.shape && (
                    <span className="variable-meta">len={v.length}</span>
                  )}
                </div>
              </div>
            );
          })}
        </CollapsibleSection>
      ))}
    </div>
  );
}

/* ── Graph Panel ─────────────────────────────────────────────────── */

function GraphPanel({ graph, cells }) {
  const cellEntries = Object.entries(graph?.cells || {});
  const varProducers = graph?.var_producers || {};

  if (cellEntries.length === 0) {
    return (
      <div className="sidebar-empty-state">
        <GitBranch size={24} className="sidebar-empty-icon" />
        <span className="sidebar-empty-title">No dependencies yet</span>
        <p className="sidebar-empty-desc">Run cells to build the reactive DAG</p>
      </div>
    );
  }

  return (
    <div>
      <CollapsibleSection title={`Cells (${cellEntries.length})`} defaultOpen>
        {cellEntries.map(([cellId, info]) => {
          const cell = cells?.find(c => c.id === cellId);
          const stateColor = {
            success: 'var(--green)', error: 'var(--error)',
            stale: 'var(--warning)', running: 'var(--accent)',
            idle: 'var(--fg-dim)',
          }[info.state] || 'var(--fg-dim)';

          return (
            <div key={cellId} className="variable-item group">
              <div className="variable-item-left">
                <div className="graph-state-dot" style={{ background: stateColor }} />
                <span className="variable-name">
                  {cell?.name || cellId.slice(0, 6)}
                </span>
              </div>
              <div className="variable-item-right">
                {info.writes?.length > 0 && (
                  <span className="graph-writes">→ {info.writes.slice(0, 3).join(', ')}</span>
                )}
                {(info.upstream?.length > 0 || info.downstream?.length > 0) && (
                  <span className="graph-arrows">
                    {info.upstream?.length > 0 && `↑${info.upstream.length}`}
                    {' '}
                    {info.downstream?.length > 0 && `↓${info.downstream.length}`}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </CollapsibleSection>

      <CollapsibleSection title={`Variables (${Object.keys(varProducers).length})`} defaultOpen={false}>
        {Object.entries(varProducers).map(([varName, cellId]) => {
          const cell = cells?.find(c => c.id === cellId);
          return (
            <div key={varName} className="variable-item">
              <span className="variable-name">{varName}</span>
              <span className="variable-meta" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <ArrowRight size={10} />
                {cell?.name || cellId.slice(0, 6)}
              </span>
            </div>
          );
        })}
      </CollapsibleSection>
    </div>
  );
}

/* ── Outline Panel ───────────────────────────────────────────────── */

function OutlinePanel({ cells, search, onScrollToCell }) {
  const items = useMemo(() => {
    const result = [];
    (cells || []).forEach((cell, index) => {
      if (cell.cell_type === 'markdown' && cell.source) {
        cell.source.split('\n').forEach(line => {
          const match = line.match(/^(#{1,3})\s+(.+)/);
          if (match) {
            result.push({
              level: match[1].length, text: match[2],
              cellIndex: index, cellId: cell.id, type: 'heading',
            });
          }
        });
      }
      if (cell.cell_type === 'code' && cell.name) {
        result.push({
          level: 2, text: cell.name,
          cellIndex: index, cellId: cell.id, type: 'code',
        });
      }
      if (cell.cell_type === 'sql') {
        const preview = cell.source?.split('\n')[0]?.slice(0, 40) || 'SQL Query';
        result.push({
          level: 3, text: preview,
          cellIndex: index, cellId: cell.id, type: 'sql',
        });
      }
    });

    if (search) {
      const q = search.toLowerCase();
      return result.filter(item => item.text.toLowerCase().includes(q));
    }
    return result;
  }, [cells, search]);

  if (items.length === 0) {
    return (
      <div className="sidebar-empty-state">
        <List size={24} className="sidebar-empty-icon" />
        <span className="sidebar-empty-title">
          {search ? 'No matches' : 'No outline available'}
        </span>
        {!search && <p className="sidebar-empty-desc">Add markdown headers to build an outline</p>}
      </div>
    );
  }

  const typeIcon = { heading: '📝', code: '⚡', sql: '🗃️' };

  return (
    <div>
      {items.map((item, i) => (
        <div key={i}
          className="outline-item"
          style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
          onClick={() => onScrollToCell?.(item.cellId)}
        >
          <span className="outline-item-text">
            <span className="outline-item-icon">{typeIcon[item.type]}</span>
            {item.text}
          </span>
          <span className="outline-item-index">{item.cellIndex + 1}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Environment Panel ───────────────────────────────────────────── */

function EnvironmentPanel({ metadata, connected }) {
  return (
    <div>
      <CollapsibleSection title="Connection" defaultOpen>
        <div className="env-card">
          <div className="env-card-row">
            <div className={`env-status-dot ${connected ? 'connected' : 'local'}`} />
            <span className="env-card-label">
              {connected ? 'Connected to Server' : 'Local Mode'}
            </span>
          </div>
          {metadata?.server ? (
            <div className="env-card-detail">
              <Globe size={11} /> {metadata.server}
            </div>
          ) : (
            <div className="env-card-detail">
              Running on local kernel. Connect to a FlowyML server for scheduling, deployment, and collaboration.
            </div>
          )}
          {!connected && (
            <button className="btn-ghost-sm w-full" style={{ marginTop: '8px' }}>
              <Server size={12} /> Connect to Server
            </button>
          )}
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Notebook" defaultOpen>
        <div className="env-info-list">
          <InfoRow label="Name" value={metadata?.name || 'untitled'} />
          <InfoRow label="Version" value={`v${metadata?.version || 1}`} />
          {metadata?.author && <InfoRow label="Author" value={metadata.author} />}
          {metadata?.description && <InfoRow label="Desc" value={metadata.description} />}
          {metadata?.tags?.length > 0 && (
            <div className="env-tags-row">
              <span className="env-info-label">Tags</span>
              <div className="env-tags">
                {metadata.tags.map(t => <span key={t} className="env-tag">{t}</span>)}
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Runtime" defaultOpen>
        <div className="env-info-list">
          <InfoRow label="Python" value="3.12" />
          <InfoRow label="Kernel" value="IPython" />
          <InfoRow label="Engine" value="Reactive DAG" />
          <InfoRow label="Format" value="# %% Percent" />
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Dependencies" defaultOpen={false}>
        <div className="env-deps-list">
          {['flowyml ≥1.8', 'pandas', 'numpy', 'scikit-learn', 'duckdb'].map(dep => (
            <div key={dep} className="env-dep-item">
              <Package size={10} />
              <span>{dep}</span>
            </div>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
}

/* ── Reusable Components ─────────────────────────────────────────── */

function CollapsibleSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title" onClick={() => setOpen(!open)}>
        <span className="sidebar-section-title-inner">
          {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          {title}
        </span>
      </div>
      {open && children}
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="env-info-row">
      <span className="env-info-label">{label}</span>
      <span className="env-info-value">{value}</span>
    </div>
  );
}
