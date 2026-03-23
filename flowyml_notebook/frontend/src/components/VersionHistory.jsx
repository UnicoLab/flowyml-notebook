import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock, GitCommit, ArrowLeft, ChevronDown, ChevronRight,
  User, FileCode, Plus, Minus, Edit3, RotateCcw
} from 'lucide-react';

/**
 * VersionHistory — Enhanced commit timeline with contributor avatars,
 * file stats (insertions/deletions), merge indicators, compare-to-current,
 * and cell-level change summaries.
 */
export default function VersionHistory({ onClose }) {
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [diffSummary, setDiffSummary] = useState(null);

  useEffect(() => {
    loadCommits();
  }, []);

  const loadCommits = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/github/log?limit=30');
      const data = await res.json();
      setCommits(data.commits || []);
    } catch { setCommits([]); }
    setLoading(false);
  };

  const loadDiff = async (sha) => {
    try {
      const res = await fetch(`/api/github/diff-summary/${sha}`);
      setDiffSummary(await res.json());
    } catch { setDiffSummary(null); }
  };

  const selectCommit = (commit) => {
    if (selectedCommit?.sha === commit.sha) {
      setSelectedCommit(null);
      setDiffSummary(null);
    } else {
      setSelectedCommit(commit);
      loadDiff(commit.sha);
    }
  };

  const handleRestore = async (sha) => {
    if (!confirm('Restore this version? Current changes will be overwritten.')) return;
    try {
      await fetch(`/api/github/restore?sha=${sha}`, { method: 'POST' });
    } catch (e) {
      console.error('Restore failed', e);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    if (diff < 172800000) return 'Yesterday';
    return d.toLocaleDateString('en', { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
  };

  if (loading) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: 'var(--fg-tertiary)' }}>
        <Clock size={20} className="animate-spin" style={{ margin: '0 auto 12px' }} />
        <div style={{ fontSize: 11 }}>Loading history...</div>
      </div>
    );
  }

  return (
    <div className="version-history" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Clock size={14} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>Version History</span>
        <span style={{ fontSize: 10, color: 'var(--fg-secondary)' }}>{commits.length} commits</span>
        {onClose && (
          <button className="btn-icon" onClick={onClose} style={{ width: 20, height: 20 }}>
            <ArrowLeft size={12} />
          </button>
        )}
      </div>

      {/* Timeline */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
        {commits.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--fg-tertiary)', fontSize: 11 }}>
            <GitCommit size={24} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
            <div>No commit history</div>
            <div style={{ fontSize: 10, marginTop: 4 }}>Push to GitHub to start tracking versions</div>
          </div>
        ) : (
          commits.map((commit, i) => {
            const isSelected = selectedCommit?.sha === commit.sha;
            const author = commit.author || {};
            return (
              <div key={commit.sha}>
                <div
                  onClick={() => selectCommit(commit)}
                  style={{
                    display: 'flex', gap: 8, padding: '8px 6px',
                    borderRadius: 8, cursor: 'pointer', alignItems: 'flex-start',
                    background: isSelected ? 'var(--accent-muted)' : 'transparent',
                    borderLeft: `3px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                    marginBottom: 2, transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                >
                  {/* Timeline dot + connector */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 24, flexShrink: 0 }}>
                    {/* Avatar */}
                    <div style={{
                      width: 22, height: 22, borderRadius: '50%',
                      background: `hsl(${author.avatar_hue || 200}, 60%, 45%)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 9, fontWeight: 700, color: '#fff',
                      border: commit.is_merge ? '2px solid var(--warning, #fbbf24)' : '2px solid var(--bg-secondary)',
                    }}>
                      {author.initials || '?'}
                    </div>
                    {i < commits.length - 1 && (
                      <div style={{ width: 1, flex: 1, background: 'var(--border)', marginTop: 2 }} />
                    )}
                  </div>

                  {/* Commit info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {commit.message}
                      </span>
                      {commit.is_merge && (
                        <span style={{
                          fontSize: 8, padding: '1px 5px', borderRadius: 6,
                          background: 'rgba(251,191,36,0.15)', color: '#fbbf24',
                          fontWeight: 600,
                        }}>
                          merge
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 9, color: 'var(--fg-tertiary)' }}>
                      <span style={{ fontWeight: 500 }}>{author.name}</span>
                      <span>{formatDate(commit.date)}</span>
                      <code style={{
                        fontSize: 9, padding: '0 4px', borderRadius: 3,
                        background: 'var(--bg-primary)', fontFamily: 'var(--font-mono)',
                      }}>
                        {commit.sha_short}
                      </code>
                    </div>

                    {/* Stats badges */}
                    {(commit.files_changed > 0 || commit.insertions > 0 || commit.deletions > 0) && (
                      <div style={{ display: 'flex', gap: 6, marginTop: 3, fontSize: 9 }}>
                        {commit.files_changed > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 2, color: 'var(--fg-secondary)' }}>
                            <FileCode size={9} /> {commit.files_changed}
                          </span>
                        )}
                        {commit.insertions > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 2, color: '#22c55e' }}>
                            <Plus size={9} /> {commit.insertions}
                          </span>
                        )}
                        {commit.deletions > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 2, color: '#ef4444' }}>
                            <Minus size={9} /> {commit.deletions}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Expanded diff summary */}
                {isSelected && diffSummary && (
                  <div style={{
                    marginLeft: 32, padding: '6px 8px', marginBottom: 4,
                    background: 'var(--bg-tertiary)', borderRadius: 6,
                    border: '1px solid var(--border)',
                  }}>
                    <div style={{ fontSize: 10, fontWeight: 600, marginBottom: 4, color: 'var(--fg-primary)' }}>
                      Changed Files
                    </div>
                    {diffSummary.files?.map((f, j) => (
                      <div key={j} style={{
                        display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0',
                        fontSize: 10, color: 'var(--fg-secondary)',
                      }}>
                        <span style={{
                          width: 14, height: 14, borderRadius: 3, display: 'flex',
                          alignItems: 'center', justifyContent: 'center', fontSize: 8,
                          background: f.status === 'A' ? 'rgba(34,197,94,0.15)' :
                                     f.status === 'D' ? 'rgba(239,68,68,0.15)' :
                                     'rgba(96,165,250,0.15)',
                          color: f.status === 'A' ? '#22c55e' :
                                 f.status === 'D' ? '#ef4444' : '#60a5fa',
                          fontWeight: 700,
                        }}>
                          {f.status}
                        </span>
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {f.file.split('/').pop()}
                        </span>
                      </div>
                    ))}

                    {/* Cell-level changes */}
                    {diffSummary.cell_changes?.length > 0 && (
                      <div style={{ marginTop: 6 }}>
                        <div style={{ fontSize: 9, fontWeight: 600, color: 'var(--accent)', marginBottom: 2 }}>
                          📓 Notebook Changes
                        </div>
                        {diffSummary.cell_changes.map((f, j) => (
                          <div key={j} style={{ fontSize: 9, color: 'var(--fg-tertiary)', padding: '1px 0' }}>
                            {f.status === 'A' ? '➕' : f.status === 'D' ? '➖' : '✏️'}{' '}
                            {f.file.split('/').pop()}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Restore button */}
                    <button
                      className="btn-ghost-sm"
                      onClick={() => handleRestore(commit.sha)}
                      style={{ marginTop: 6, fontSize: 9, display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <RotateCcw size={10} /> Restore this version
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
