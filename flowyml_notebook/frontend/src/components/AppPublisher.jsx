import React, { useState, useCallback } from 'react';
import {
  Globe, X, Layout, Grid3X3, ColumnsIcon, PanelTop,
  BarChart3, Eye, EyeOff, Code, Sun, Moon, Monitor,
  CheckCircle, Loader, ExternalLink, Settings,
  Columns2, Columns3, Columns4,
  SlidersHorizontal, RefreshCw, Share2, Copy, Link, Mail,
  Zap, Play, Clock
} from 'lucide-react';

const LAYOUTS = [
  { id: 'linear', label: 'Linear', icon: PanelTop, desc: 'Top-to-bottom flow' },
  { id: 'grid', label: 'Grid', icon: Grid3X3, desc: 'CSS grid layout' },
  { id: 'tabs', label: 'Tabs', icon: ColumnsIcon, desc: 'Tabbed sections' },
  { id: 'sidebar', label: 'Sidebar', icon: Layout, desc: 'Sidebar + main' },
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3, desc: 'KPIs + charts' },
];

const THEMES = [
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'auto', label: 'Auto', icon: Monitor },
];

export default function AppPublisher({ onClose, cells = [], metadata }) {
  const [title, setTitle] = useState(metadata?.name || 'My App');
  const [layout, setLayout] = useState('linear');
  const [theme, setTheme] = useState('dark');
  const [showCode, setShowCode] = useState(false);
  const [gridColumns, setGridColumns] = useState(2);
  const [cellVisibility, setCellVisibility] = useState(() => {
    const vis = {};
    cells.forEach(c => { vis[c.id] = true; });
    return vis;
  });
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(null);
  const [interactive, setInteractive] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState('off');
  const [shareCopied, setShareCopied] = useState(false);
  const [snapshotSending, setSnapshotSending] = useState(false);

  const toggleCell = (cellId) => {
    setCellVisibility(prev => ({ ...prev, [cellId]: !prev[cellId] }));
  };

  const handlePublish = useCallback(async () => {
    setPublishing(true);
    try {
      const res = await fetch('/api/app/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title, layout, theme, show_code: showCode,
          grid_columns: gridColumns, cell_visibility: cellVisibility,
          interactive, refresh_interval: refreshInterval !== 'off' ? parseInt(refreshInterval) : null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPublished(data);
      }
    } catch (e) {
      console.error('Publish failed:', e);
    }
    setPublishing(false);
  }, [title, layout, theme, showCode, gridColumns, cellVisibility]);

  const handlePreview = useCallback(() => {
    window.open('/api/app/preview', '_blank');
  }, []);

  const visibleCount = Object.values(cellVisibility).filter(Boolean).length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Globe size={16} style={{ color: '#8b5cf6' }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>Publish as App</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--fg-muted)', cursor: 'pointer' }}>
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {/* Title */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>App Title</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={inputStyle}
          />
        </div>

        {/* Layout Picker */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Layout</label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
            {LAYOUTS.map(l => (
              <button
                key={l.id}
                onClick={() => setLayout(l.id)}
                style={{
                  padding: '10px 6px', borderRadius: 8, fontSize: 10, fontWeight: 600,
                  background: layout === l.id ? 'rgba(139,92,246,0.15)' : 'var(--bg-primary)',
                  border: `1px solid ${layout === l.id ? '#8b5cf6' : 'var(--border)'}`,
                  color: layout === l.id ? '#c4b5fd' : 'var(--fg-muted)',
                  cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s',
                }}
              >
                <l.icon size={16} style={{ margin: '0 auto 4px', display: 'block' }} />
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Grid columns (only for grid/dashboard) */}
        {(layout === 'grid' || layout === 'dashboard') && (
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Grid Columns</label>
            <div style={{ display: 'flex', gap: 6 }}>
              {[2, 3, 4].map(n => (
                <button
                  key={n}
                  onClick={() => setGridColumns(n)}
                  style={{
                    flex: 1, padding: '8px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                    background: gridColumns === n ? 'rgba(139,92,246,0.15)' : 'var(--bg-primary)',
                    border: `1px solid ${gridColumns === n ? '#8b5cf6' : 'var(--border)'}`,
                    color: gridColumns === n ? '#c4b5fd' : 'var(--fg-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {n} cols
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Theme */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Theme</label>
          <div style={{ display: 'flex', gap: 6 }}>
            {THEMES.map(t => (
              <button
                key={t.id}
                onClick={() => setTheme(t.id)}
                style={{
                  flex: 1, padding: '8px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                  background: theme === t.id ? 'rgba(139,92,246,0.15)' : 'var(--bg-primary)',
                  border: `1px solid ${theme === t.id ? '#8b5cf6' : 'var(--border)'}`,
                  color: theme === t.id ? '#c4b5fd' : 'var(--fg-muted)',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                }}
              >
                <t.icon size={12} /> {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Show Code */}
        <div style={{ marginBottom: 16 }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
            padding: '10px 12px', borderRadius: 8,
            background: 'var(--bg-primary)', border: '1px solid var(--border)',
          }}>
            <input
              type="checkbox" checked={showCode}
              onChange={e => setShowCode(e.target.checked)}
              style={{ accentColor: '#8b5cf6' }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Show Source Code</div>
              <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>Display code alongside outputs in the app</div>
            </div>
          </label>
        </div>

        {/* Cell Visibility */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Cell Visibility ({visibleCount}/{cells.length})</label>
          <div style={{ maxHeight: 200, overflow: 'auto', borderRadius: 8, border: '1px solid var(--border)' }}>
            {cells.map((cell, i) => (
              <button
                key={cell.id}
                onClick={() => toggleCell(cell.id)}
                style={{
                  width: '100%', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 8,
                  background: 'none', border: 'none', borderBottom: '1px solid var(--border)',
                  color: cellVisibility[cell.id] ? 'var(--fg-primary)' : 'var(--fg-muted)',
                  cursor: 'pointer', fontSize: 12, textAlign: 'left',
                  opacity: cellVisibility[cell.id] ? 1 : 0.5,
                }}
              >
                {cellVisibility[cell.id] ? <Eye size={12} /> : <EyeOff size={12} />}
                <span style={{ fontWeight: 500 }}>
                  {cell.name || `Cell ${i + 1}`}
                </span>
                <span style={{
                  marginLeft: 'auto', padding: '1px 6px', borderRadius: 4, fontSize: 9,
                  background: 'rgba(255,255,255,0.05)', fontWeight: 600,
                }}>
                  {cell.cell_type}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Interactive Widgets Section */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>
            <SlidersHorizontal size={10} style={{ marginRight: 4, display: 'inline', verticalAlign: -1 }} />
            Interactive Dashboard
          </label>
          <div style={{
            padding: '10px 12px', borderRadius: 8,
            background: 'var(--bg-primary)', border: '1px solid var(--border)',
          }}>
            {/* Enable interactivity */}
            <label style={{
              display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', marginBottom: 10,
            }}>
              <input
                type="checkbox" checked={interactive}
                onChange={e => setInteractive(e.target.checked)}
                style={{ accentColor: '#8b5cf6' }}
              />
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-primary)' }}>
                  <Zap size={11} style={{ display: 'inline', verticalAlign: -1, marginRight: 4, color: '#f59e0b' }} />
                  Enable Interactive Widgets
                </div>
                <div style={{ fontSize: 10, color: 'var(--fg-dim)', marginTop: 2 }}>
                  Auto-detect DataFrames and add filters, sliders, and dropdowns for stakeholders
                </div>
              </div>
            </label>

            {interactive && (
              <>
                {/* Auto-refresh */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
                  borderTop: '1px solid var(--border)',
                }}>
                  <RefreshCw size={11} style={{ color: 'var(--fg-dim)' }} />
                  <span style={{ fontSize: 11, color: 'var(--fg-muted)', flex: 1 }}>Auto-refresh</span>
                  <select
                    value={refreshInterval}
                    onChange={e => setRefreshInterval(e.target.value)}
                    style={{
                      fontSize: 10, padding: '3px 6px', borderRadius: 6,
                      background: 'var(--bg-secondary)', color: 'var(--fg-primary)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <option value="off">Off</option>
                    <option value="30">30 seconds</option>
                    <option value="60">1 minute</option>
                    <option value="300">5 minutes</option>
                    <option value="900">15 minutes</option>
                  </select>
                </div>

                {/* Widget types */}
                <div style={{
                  padding: '8px 0', borderTop: '1px solid var(--border)',
                  display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4,
                }}>
                  {['Date Range', 'Category Dropdown', 'Numeric Slider', 'Text Search'].map(w => (
                    <span key={w} style={{
                      padding: '3px 8px', borderRadius: 10, fontSize: 9, fontWeight: 600,
                      background: 'rgba(139,92,246,0.1)', color: '#c4b5fd',
                      border: '1px solid rgba(139,92,246,0.2)',
                    }}>
                      {w}
                    </span>
                  ))}
                  <span style={{ fontSize: 9, color: 'var(--fg-dim)', alignSelf: 'center', marginLeft: 4 }}>
                    Auto-detected from data columns
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Sharing Section */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>
            <Share2 size={10} style={{ marginRight: 4, display: 'inline', verticalAlign: -1 }} />
            Sharing Options
          </label>
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <button
              onClick={() => {
                const url = `${window.location.origin}/api/app/preview?state=${btoa(JSON.stringify({ title, layout, theme }))}#shared`;
                navigator.clipboard.writeText(url);
                setShareCopied(true);
                setTimeout(() => setShareCopied(false), 2000);
              }}
              style={{
                padding: '8px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                background: 'var(--bg-primary)', border: '1px solid var(--border)',
                color: 'var(--fg-primary)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left',
              }}
            >
              {shareCopied ? <CheckCircle size={13} style={{ color: '#10b981' }} /> : <Link size={13} style={{ color: '#8b5cf6' }} />}
              <div style={{ flex: 1 }}>
                <div>{shareCopied ? 'Link Copied!' : 'Copy Shareable Link'}</div>
                <div style={{ fontSize: 9, color: 'var(--fg-dim)', marginTop: 1 }}>URL with embedded filter state</div>
              </div>
            </button>

            <button
              onClick={async () => {
                setSnapshotSending(true);
                try {
                  await fetch('/api/app/snapshot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, format: 'png' }),
                  });
                } catch (e) { /* ignore */ }
                setSnapshotSending(false);
              }}
              style={{
                padding: '8px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                background: 'var(--bg-primary)', border: '1px solid var(--border)',
                color: 'var(--fg-primary)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left',
              }}
            >
              <Mail size={13} style={{ color: '#f59e0b' }} />
              <div style={{ flex: 1 }}>
                <div>{snapshotSending ? 'Sending...' : 'Email Snapshot'}</div>
                <div style={{ fontSize: 9, color: 'var(--fg-dim)', marginTop: 1 }}>Render current state as PNG and send</div>
              </div>
            </button>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            onClick={handlePublish}
            disabled={publishing}
            style={{
              padding: '12px 16px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
              color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              opacity: publishing ? 0.7 : 1,
            }}
          >
            {publishing ? <Loader size={14} className="animate-spin" /> : <Globe size={14} />}
            {publishing ? 'Publishing...' : interactive ? 'Publish Interactive Dashboard' : 'Publish App'}
          </button>

          {published && (
            <button
              onClick={handlePreview}
              style={{
                padding: '10px 16px', borderRadius: 8,
                border: '1px solid rgba(139,92,246,0.3)',
                background: 'rgba(139,92,246,0.08)',
                color: '#c4b5fd', cursor: 'pointer', fontSize: 13, fontWeight: 500,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <ExternalLink size={14} /> Open App Preview
            </button>
          )}
        </div>

        {/* Published result */}
        {published && (
          <div style={{
            marginTop: 16, padding: 12, borderRadius: 8,
            background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <CheckCircle size={14} style={{ color: '#4ade80' }} />
              <span style={{ fontWeight: 600, fontSize: 12, color: '#4ade80' }}>
                {interactive ? 'Interactive Dashboard Published!' : 'App Published!'}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-muted)', wordBreak: 'break-all' }}>
              Saved: {published.path}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const labelStyle = {
  display: 'block', fontSize: 11, fontWeight: 600,
  color: 'var(--fg-muted)', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '0.05em',
};

const inputStyle = {
  width: '100%', padding: '8px 12px', borderRadius: 8,
  background: 'var(--bg-primary)', border: '1px solid var(--border)',
  color: 'var(--fg-primary)', fontSize: 13,
};
