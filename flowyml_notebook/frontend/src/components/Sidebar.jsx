import React, { useState, useMemo, useEffect, useCallback } from 'react';
import {
  Variable, GitBranch, FileCode, List, Search, Package,
  Server, Cpu, Database, ChevronDown, ChevronRight,
  Circle, ArrowRight, Zap, Terminal, Globe, FileText,
  FolderOpen, History, Github, Layers, RefreshCw,
  Box, FlaskConical, Activity, GitCommit
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
  { id: 'flowyml', label: 'FlowyML', shortLabel: 'FML', icon: Layers, group: 'analysis' },
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
            {activeTab === 'flowyml' && (
              <FlowyMLPanel />
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

/* ── GitHub Panel (Enhanced) ──────────────────────────────────────── */

function GitHubPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [showInit, setShowInit] = useState(false);
  const [mergeStatus, setMergeStatus] = useState(null);
  const [commitMsg, setCommitMsg] = useState('');
  const [activeTab, setActiveTab] = useState('sync'); // sync | activity | branches | stash
  const [activity, setActivity] = useState([]);
  const [editors, setEditors] = useState([]);
  const [branches, setBranches] = useState({ branches: [], current: '' });
  const [newBranch, setNewBranch] = useState('');
  const [showNewBranch, setShowNewBranch] = useState(false);
  const [stashes, setStashes] = useState([]);
  const [stashMsg, setStashMsg] = useState('');

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/github/status');
      const data = await res.json();
      setStatus(data);
    } catch { setStatus({ connected: false, error: 'Failed to connect' }); }
    setLoading(false);
  };

  const loadMergeStatus = async () => {
    try {
      const res = await fetch('/api/github/merge-status');
      setMergeStatus(await res.json());
    } catch {}
  };

  const loadActivity = async () => {
    try {
      const res = await fetch('/api/github/activity?limit=20');
      const data = await res.json();
      setActivity(data.feed || []);
    } catch {}
  };

  const loadEditors = async () => {
    try {
      const res = await fetch('/api/github/presence');
      const data = await res.json();
      setEditors(data.editors || []);
    } catch {}
  };

  const loadBranches = async () => {
    try {
      const res = await fetch('/api/github/branches');
      setBranches(await res.json());
    } catch {}
  };

  const loadStashes = async () => {
    try {
      const res = await fetch('/api/github/stash/list');
      const data = await res.json();
      setStashes(data.stashes || []);
    } catch {}
  };

  React.useEffect(() => {
    loadStatus();
    const interval = setInterval(loadEditors, 30000); // Poll presence every 30s
    return () => clearInterval(interval);
  }, []);

  React.useEffect(() => {
    if (status?.connected) {
      loadMergeStatus();
      loadEditors();
    }
  }, [status?.connected]);

  const handleInit = async () => {
    if (!repoUrl) return;
    setLoading(true);
    try {
      await fetch(`/api/github/init?repo_url=${encodeURIComponent(repoUrl)}`, { method: 'POST' });
      setShowInit(false);
      loadStatus();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handlePush = async () => {
    setLoading(true);
    try {
      const url = commitMsg
        ? `/api/github/push?message=${encodeURIComponent(commitMsg)}`
        : '/api/github/push';
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      if (data.pushed) { loadStatus(); loadMergeStatus(); setCommitMsg(''); }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handlePull = async () => {
    setLoading(true);
    try {
      await fetch('/api/github/pull-rebase', { method: 'POST' });
      loadStatus();
      loadMergeStatus();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleCreateBranch = async () => {
    if (!newBranch.trim()) return;
    await fetch(`/api/github/branch?name=${encodeURIComponent(newBranch.trim())}`, { method: 'POST' });
    setNewBranch('');
    setShowNewBranch(false);
    loadBranches();
    loadStatus();
  };

  const handleSwitchBranch = async (name) => {
    await fetch(`/api/github/branch?name=${encodeURIComponent(name)}`, { method: 'PUT' });
    loadStatus();
    loadMergeStatus();
  };

  const handleDeleteBranch = async (name) => {
    if (!confirm(`Delete branch "${name}"?`)) return;
    await fetch(`/api/github/branch?name=${encodeURIComponent(name)}`, { method: 'DELETE' });
    loadBranches();
  };

  const handleStash = async () => {
    await fetch(`/api/github/stash${stashMsg ? `?message=${encodeURIComponent(stashMsg)}` : ''}`, { method: 'POST' });
    setStashMsg('');
    loadStatus();
    loadStashes();
  };

  const handlePopStash = async () => {
    await fetch('/api/github/stash/pop', { method: 'POST' });
    loadStatus();
    loadStashes();
  };

  const formatTimeAgo = (ts) => {
    if (!ts) return '';
    const now = Date.now();
    const date = new Date(ts);
    const diff = now - date.getTime();
    if (diff < 60000) return 'now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return date.toLocaleDateString();
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

  const tabItems = [
    { id: 'sync', label: 'Sync' },
    { id: 'activity', label: 'Activity', onClick: loadActivity },
    { id: 'branches', label: 'Branches', onClick: loadBranches },
    { id: 'stash', label: 'Stash', onClick: loadStashes },
  ];

  return (
    <div>
      {/* Active editors */}
      {editors.length > 0 && (
        <div className="github-presence-bar">
          <span style={{ fontSize: 9, color: 'var(--fg-tertiary)', marginRight: 4 }}>Active:</span>
          {editors.map((e, i) => (
            <div
              key={i}
              title={`${e.name} — editing ${e.notebook}`}
              style={{
                width: 20, height: 20, borderRadius: '50%',
                background: `hsl(${e.avatar_hue || 200}, 60%, 45%)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 8, fontWeight: 700, color: '#fff',
                marginLeft: i > 0 ? -4 : 0, border: '2px solid var(--bg-secondary)',
              }}
            >
              {e.initials || '?'}
            </div>
          ))}
        </div>
      )}

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
          {/* Merge status badges */}
          {mergeStatus && mergeStatus.status !== 'up-to-date' && (
            <span style={{
              fontSize: 9, padding: '1px 6px', borderRadius: 8,
              background: mergeStatus.status === 'diverged' ? 'rgba(239,68,68,0.15)' :
                          mergeStatus.status === 'behind' ? 'rgba(251,191,36,0.15)' :
                          'rgba(34,197,94,0.15)',
              color: mergeStatus.status === 'diverged' ? '#ef4444' :
                     mergeStatus.status === 'behind' ? '#fbbf24' : '#22c55e',
              fontWeight: 600,
            }}>
              {mergeStatus.ahead > 0 && `↑${mergeStatus.ahead}`}
              {mergeStatus.ahead > 0 && mergeStatus.behind > 0 && ' '}
              {mergeStatus.behind > 0 && `↓${mergeStatus.behind}`}
            </span>
          )}
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

      {/* Commit message input */}
      <div style={{ padding: '0 8px 6px' }}>
        <input
          style={{
            width: '100%', padding: '5px 8px', borderRadius: 6, fontSize: 10,
            border: '1px solid var(--border)', background: 'var(--bg-primary)',
            color: 'var(--fg-primary)', outline: 'none', boxSizing: 'border-box',
          }}
          placeholder="Commit message (optional)"
          value={commitMsg}
          onChange={e => setCommitMsg(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handlePush(); }}
        />
      </div>

      {/* Actions */}
      <div className="github-actions">
        <button
          className="github-action-btn push"
          onClick={handlePush}
          disabled={loading || (mergeStatus?.needs_pull)}
          title={mergeStatus?.needs_pull ? 'Pull first — behind remote' : 'Push to remote'}
        >
          Push {mergeStatus?.ahead > 0 && `(${mergeStatus.ahead})`}
        </button>
        <button className="github-action-btn pull" onClick={handlePull} disabled={loading}>
          Pull {mergeStatus?.behind > 0 && `(${mergeStatus.behind})`}
        </button>
        <button className="github-action-btn refresh" onClick={() => { loadStatus(); loadMergeStatus(); }} disabled={loading}>
          ↻
        </button>
      </div>

      {/* Sub-tabs */}
      <div style={{
        display: 'flex', gap: 2, padding: '4px 8px', borderBottom: '1px solid var(--border)',
        borderTop: '1px solid var(--border)',
      }}>
        {tabItems.map(t => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); t.onClick?.(); }}
            style={{
              flex: 1, padding: '4px 0', borderRadius: 6, fontSize: 9, fontWeight: 500,
              background: activeTab === t.id ? 'var(--accent-muted)' : 'transparent',
              color: activeTab === t.id ? 'var(--accent)' : 'var(--fg-secondary)',
              border: 'none', cursor: 'pointer',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ maxHeight: 300, overflowY: 'auto' }}>
        {/* Sync tab — changes list */}
        {activeTab === 'sync' && status.changes?.length > 0 && (
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

        {/* Activity feed */}
        {activeTab === 'activity' && (
          <div style={{ padding: '6px 8px' }}>
            {activity.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 16, color: 'var(--fg-tertiary)', fontSize: 10 }}>
                No recent activity
              </div>
            ) : (
              activity.map((event, i) => {
                const iconMap = { commit: '📦', comment: '💬', review: '📋' };
                const user = event.user || {};
                return (
                  <div key={i} style={{
                    display: 'flex', gap: 6, padding: '5px 0',
                    borderBottom: '1px solid var(--border)', alignItems: 'flex-start',
                  }}>
                    <div style={{
                      width: 18, height: 18, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                      background: `hsl(${user.avatar_hue || (user.name?.charCodeAt(0) * 37 % 360 || 200)}, 60%, 45%)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 8, fontWeight: 700, color: '#fff',
                    }}>
                      {user.initials || (user.name || '?')[0]?.toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 10, color: 'var(--fg-primary)' }}>
                        <span style={{ fontWeight: 600 }}>{user.name || 'Unknown'}</span>
                        {' '}{event.message?.slice(0, 60)}
                      </div>
                      <div style={{ fontSize: 9, color: 'var(--fg-tertiary)', display: 'flex', gap: 6, marginTop: 1 }}>
                        <span>{iconMap[event.type] || '📌'} {event.type}</span>
                        <span>{formatTimeAgo(event.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Branches tab */}
        {activeTab === 'branches' && (
          <div style={{ padding: '6px 8px' }}>
            {showNewBranch ? (
              <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
                <input
                  style={{
                    flex: 1, padding: '4px 8px', borderRadius: 6, fontSize: 10,
                    border: '1px solid var(--border)', background: 'var(--bg-primary)',
                    color: 'var(--fg-primary)', outline: 'none',
                  }}
                  placeholder="Branch name"
                  value={newBranch}
                  onChange={e => setNewBranch(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleCreateBranch(); }}
                />
                <button className="btn-primary-sm" onClick={handleCreateBranch} style={{ fontSize: 9 }}>
                  Create
                </button>
                <button className="btn-ghost-sm" onClick={() => setShowNewBranch(false)} style={{ fontSize: 9 }}>
                  ✕
                </button>
              </div>
            ) : (
              <button className="btn-ghost-sm" onClick={() => setShowNewBranch(true)} style={{ fontSize: 9, marginBottom: 6 }}>
                + New Branch
              </button>
            )}
            {branches.branches?.filter(b => !b.startsWith('origin/')).map(branch => (
              <div key={branch} style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0',
                borderBottom: '1px solid var(--border)',
              }}>
                <GitBranch size={10} style={{ color: branch === branches.current ? 'var(--accent)' : 'var(--fg-dim)' }} />
                <span style={{
                  flex: 1, fontSize: 10, fontWeight: branch === branches.current ? 600 : 400,
                  color: branch === branches.current ? 'var(--accent)' : 'var(--fg-primary)',
                }}>
                  {branch}
                  {branch === branches.current && ' ✓'}
                </span>
                {branch !== branches.current && (
                  <>
                    <button className="btn-icon" style={{ width: 18, height: 18, fontSize: 8 }}
                      onClick={() => handleSwitchBranch(branch)} title="Switch">↪</button>
                    <button className="btn-icon" style={{ width: 18, height: 18, fontSize: 8, color: '#ef4444' }}
                      onClick={() => handleDeleteBranch(branch)} title="Delete">✕</button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Stash tab */}
        {activeTab === 'stash' && (
          <div style={{ padding: '6px 8px' }}>
            <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
              <input
                style={{
                  flex: 1, padding: '4px 8px', borderRadius: 6, fontSize: 10,
                  border: '1px solid var(--border)', background: 'var(--bg-primary)',
                  color: 'var(--fg-primary)', outline: 'none',
                }}
                placeholder="Stash message (optional)"
                value={stashMsg}
                onChange={e => setStashMsg(e.target.value)}
              />
              <button className="btn-primary-sm" onClick={handleStash} style={{ fontSize: 9 }}>
                Stash
              </button>
            </div>
            {stashes.length > 0 && (
              <>
                <button className="btn-ghost-sm" onClick={handlePopStash} style={{ fontSize: 9, marginBottom: 4 }}>
                  ↩ Pop Latest Stash
                </button>
                {stashes.map((s, i) => (
                  <div key={i} style={{
                    padding: '4px 0', fontSize: 10, borderBottom: '1px solid var(--border)',
                    color: 'var(--fg-secondary)',
                  }}>
                    <span style={{ fontWeight: 500 }}>{s.ref}</span>
                    {' '}{s.message}
                    <div style={{ fontSize: 9, color: 'var(--fg-tertiary)' }}>{s.date}</div>
                  </div>
                ))}
              </>
            )}
            {stashes.length === 0 && (
              <div style={{ textAlign: 'center', padding: 12, color: 'var(--fg-tertiary)', fontSize: 10 }}>
                No stashes
              </div>
            )}
          </div>
        )}
      </div>
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

/* ── FlowyML Session Inspector ─────────────────────────────────────── */

function FlowyMLPanel() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pipelineGraph, setPipelineGraph] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/flowyml/session-info');
      const data = await res.json();
      setInfo(data);
    } catch (e) {
      setError('Could not load session info');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const loadPipelineGraph = async (variable) => {
    try {
      const res = await fetch(`/api/flowyml/pipeline-graph?variable=${variable}`);
      const data = await res.json();
      if (!data.error) setPipelineGraph(data);
    } catch (e) { /* ignore */ }
  };

  const typeColors = {
    Step: '#3b82f6', Pipeline: '#8b5cf6', Dataset: '#10b981',
    Model: '#f59e0b', Metrics: '#ef4444', Experiment: '#06b6d4',
    Run: '#14b8a6', Prompt: '#ec4899', Checkpoint: '#f97316',
    Artifact: '#64748b', FeatureSet: '#84cc16', Report: '#6366f1',
    ModelRegistry: '#a855f7',
  };

  if (loading && !info) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#64748b', fontSize: '0.75rem' }}>
        <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
        <div>Scanning session...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#ef4444', fontSize: '0.75rem' }}>
        {error}
        <button onClick={refresh} style={{ display: 'block', margin: '8px auto', padding: '4px 12px',
          background: 'rgba(59,130,246,0.15)', color: '#3b82f6', border: 'none', borderRadius: 6,
          cursor: 'pointer', fontSize: '0.7rem' }}>Retry</button>
      </div>
    );
  }

  const total = info?.total || 0;

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Header */}
      <div style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Layers size={14} style={{ color: '#8b5cf6' }} />
          <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#e2e8f0' }}>Session Inspector</span>
          <span style={{ fontSize: '0.6rem', color: '#64748b', background: 'rgba(99,102,241,0.1)',
            padding: '1px 6px', borderRadius: 8 }}>{total} objects</span>
        </div>
        <button onClick={refresh} title="Refresh" style={{ background: 'none', border: 'none',
          cursor: 'pointer', color: '#64748b', padding: 2, display: 'flex' }}>
          <RefreshCw size={12} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
        </button>
      </div>

      {total === 0 && (
        <div style={{ padding: '20px 12px', textAlign: 'center', color: '#475569', fontSize: '0.7rem' }}>
          <Box size={24} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
          <div style={{ fontWeight: 500, marginBottom: 4, color: '#64748b' }}>No FlowyML objects yet</div>
          <div>Define <code style={{ color: '#8b5cf6' }}>@step</code>, create a <code style={{ color: '#8b5cf6' }}>Pipeline</code>,
            or load a <code style={{ color: '#8b5cf6' }}>Dataset</code> to see them here.</div>
        </div>
      )}

      {/* Steps */}
      {info?.steps?.length > 0 && (
        <CollapsibleSection title={`Steps (${info.steps.length})`} defaultOpen={true}>
          <div style={{ padding: '2px 12px' }}>
            {info.steps.map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0',
                borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <Zap size={10} style={{ color: typeColors.Step, flexShrink: 0 }} />
                <span style={{ fontSize: '0.7rem', color: '#e2e8f0', fontFamily: 'monospace', fontWeight: 500 }}>{s.name}</span>
                {s.outputs?.length > 0 && (
                  <span style={{ fontSize: '0.55rem', color: '#64748b', marginLeft: 'auto' }}>
                    → {s.outputs.join(', ')}
                  </span>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Pipelines */}
      {info?.pipelines?.length > 0 && (
        <CollapsibleSection title={`Pipelines (${info.pipelines.length})`} defaultOpen={true}>
          <div style={{ padding: '2px 12px' }}>
            {info.pipelines.map((p, i) => (
              <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <GitCommit size={10} style={{ color: typeColors.Pipeline, flexShrink: 0 }} />
                  <span style={{ fontSize: '0.7rem', color: '#e2e8f0', fontWeight: 600, fontFamily: 'monospace' }}>{p.name}</span>
                  <button onClick={() => loadPipelineGraph(p.variable)} style={{ marginLeft: 'auto',
                    background: 'rgba(139,92,246,0.1)', border: 'none', borderRadius: 4, padding: '1px 6px',
                    color: '#8b5cf6', fontSize: '0.55rem', cursor: 'pointer' }}>DAG</button>
                </div>
                {p.steps?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginTop: 4, paddingLeft: 16 }}>
                    {p.steps.map((s, j) => (
                      <React.Fragment key={j}>
                        <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 4,
                          background: 'rgba(59,130,246,0.1)', color: '#93c5fd', fontFamily: 'monospace' }}>{s}</span>
                        {j < p.steps.length - 1 && <ArrowRight size={8} style={{ color: '#475569', alignSelf: 'center' }} />}
                      </React.Fragment>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Pipeline DAG Preview */}
      {pipelineGraph && (
        <CollapsibleSection title={`DAG: ${pipelineGraph.name}`} defaultOpen={true}>
          <div style={{ padding: '8px 12px' }}>
            <svg viewBox="0 0 300 60" style={{ width: '100%', height: 50, overflow: 'visible' }}>
              {pipelineGraph.nodes.map((node, i) => {
                const x = 20 + i * (260 / Math.max(1, pipelineGraph.nodes.length - 1));
                return (
                  <g key={node.id}>
                    <rect x={x - 15} y={15} width={30} height={30} rx={6}
                      fill="rgba(139,92,246,0.15)" stroke="#8b5cf6" strokeWidth={1} />
                    <text x={x} y={52} textAnchor="middle" fill="#94a3b8" fontSize={5}
                      fontFamily="monospace">{node.id.slice(0, 10)}</text>
                    <text x={x} y={34} textAnchor="middle" fill="#e2e8f0" fontSize={7}
                      fontWeight="600">{i + 1}</text>
                  </g>
                );
              })}
              {pipelineGraph.edges.map((edge, i) => {
                const fromIdx = pipelineGraph.nodes.findIndex(n => n.id === edge.from);
                const toIdx = pipelineGraph.nodes.findIndex(n => n.id === edge.to);
                if (fromIdx < 0 || toIdx < 0) return null;
                const x1 = 20 + fromIdx * (260 / Math.max(1, pipelineGraph.nodes.length - 1)) + 15;
                const x2 = 20 + toIdx * (260 / Math.max(1, pipelineGraph.nodes.length - 1)) - 15;
                return <line key={i} x1={x1} y1={30} x2={x2} y2={30} stroke="#6366f1" strokeWidth={1} markerEnd="url(#arrowhead)" />;
              })}
              <defs><marker id="arrowhead" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
                <polygon points="0 0, 6 2, 0 4" fill="#6366f1" /></marker></defs>
            </svg>
          </div>
        </CollapsibleSection>
      )}

      {/* Assets */}
      {info?.assets?.length > 0 && (
        <CollapsibleSection title={`Assets (${info.assets.length})`} defaultOpen={true}>
          <div style={{ padding: '2px 12px' }}>
            {info.assets.map((a, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0',
                borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <Database size={10} style={{ color: typeColors[a.type] || '#64748b', flexShrink: 0 }} />
                <span style={{ fontSize: '0.7rem', color: '#e2e8f0', fontFamily: 'monospace' }}>{a.name}</span>
                <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 4,
                  background: `${typeColors[a.type] || '#64748b'}18`, color: typeColors[a.type] || '#94a3b8'
                }}>{a.type}</span>
                {a.shape && (
                  <span style={{ fontSize: '0.55rem', color: '#64748b', marginLeft: 'auto', fontFamily: 'monospace' }}>{a.shape}</span>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Experiments */}
      {info?.experiments?.length > 0 && (
        <CollapsibleSection title={`Tracking (${info.experiments.length})`} defaultOpen={true}>
          <div style={{ padding: '2px 12px' }}>
            {info.experiments.map((e, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0',
                borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <FlaskConical size={10} style={{ color: typeColors[e.type] || '#06b6d4', flexShrink: 0 }} />
                <span style={{ fontSize: '0.7rem', color: '#e2e8f0', fontFamily: 'monospace' }}>{e.name}</span>
                <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: 4,
                  background: 'rgba(6,182,212,0.1)', color: '#06b6d4' }}>{e.type}</span>
                {e.status && (
                  <span style={{ fontSize: '0.55rem', color: '#64748b', marginLeft: 'auto' }}>{e.status}</span>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Tracking indicator */}
      {info?.has_tracking && (
        <div style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 6,
          background: 'rgba(16,185,129,0.05)', margin: '4px 0', borderRadius: 6 }}>
          <Activity size={10} style={{ color: '#10b981' }} />
          <span style={{ fontSize: '0.6rem', color: '#10b981' }}>Experiment tracking active</span>
        </div>
      )}
    </div>
  );
}
