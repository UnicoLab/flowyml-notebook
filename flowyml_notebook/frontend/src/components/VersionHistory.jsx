import React, { useState, useEffect, useCallback } from 'react';
import {
  GitBranch, GitCommit, GitMerge, Clock, User,
  ChevronDown, ChevronRight, FileText, Plus, Minus,
  RefreshCw, Save, Eye, RotateCcw
} from 'lucide-react';

export default function VersionHistory({ notebookId }) {
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedCommit, setExpandedCommit] = useState(null);
  const [diffData, setDiffData] = useState(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/version/history');
      if (res.ok) {
        const data = await res.json();
        setCommits(data.commits || []);
      }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const createSnapshot = async () => {
    try {
      const res = await fetch('/api/version/snapshot', { method: 'POST' });
      if (res.ok) fetchHistory();
    } catch {}
  };

  const viewDiff = async (commitId) => {
    if (expandedCommit === commitId) {
      setExpandedCommit(null);
      setDiffData(null);
      return;
    }
    setExpandedCommit(commitId);
    try {
      const res = await fetch(`/api/version/diff/${commitId}`);
      if (res.ok) setDiffData(await res.json());
    } catch {}
  };

  const restoreVersion = async (commitId) => {
    if (!confirm('Restore this version? Current changes will be saved as a new snapshot.')) return;
    try {
      await fetch(`/api/version/restore/${commitId}`, { method: 'POST' });
      window.location.reload();
    } catch {}
  };

  if (loading) {
    return (
      <div className="version-loading">
        <RefreshCw size={14} className="animate-spin" />
        <span>Loading history...</span>
      </div>
    );
  }

  return (
    <div className="version-history">
      <div className="version-toolbar">
        <button className="version-snapshot-btn" onClick={createSnapshot}>
          <Save size={12} />
          <span>Save Snapshot</span>
        </button>
        <button className="btn-icon" onClick={fetchHistory} title="Refresh" style={{ width: 24, height: 24 }}>
          <RefreshCw size={11} />
        </button>
      </div>

      {commits.length === 0 ? (
        <div className="version-empty">
          <GitBranch size={20} />
          <span>No snapshots yet</span>
          <p>Save a snapshot to start tracking changes</p>
        </div>
      ) : (
        <div className="version-timeline">
          {commits.map((commit, i) => (
            <div key={commit.id} className="version-commit">
              {/* Timeline line */}
              <div className="version-line">
                <div className={`version-dot ${i === 0 ? 'latest' : ''}`}>
                  <GitCommit size={10} />
                </div>
                {i < commits.length - 1 && <div className="version-connector" />}
              </div>

              {/* Commit info */}
              <div className="version-info">
                <div className="version-header" onClick={() => viewDiff(commit.id)}>
                  <span className="version-chevron">
                    {expandedCommit === commit.id ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                  </span>
                  <span className="version-message">{commit.message || `Snapshot ${i + 1}`}</span>
                  {i === 0 && <span className="version-badge latest">Latest</span>}
                </div>

                <div className="version-meta">
                  <span className="version-time">
                    <Clock size={9} />
                    {formatTimeAgo(commit.timestamp)}
                  </span>
                  {commit.cell_count !== undefined && (
                    <span className="version-cells">
                      <FileText size={9} />
                      {commit.cell_count} cells
                    </span>
                  )}
                  {commit.additions !== undefined && (
                    <span className="version-additions">+{commit.additions}</span>
                  )}
                  {commit.deletions !== undefined && (
                    <span className="version-deletions">−{commit.deletions}</span>
                  )}
                </div>

                {/* Actions */}
                <div className="version-actions">
                  <button className="version-action-btn" onClick={() => viewDiff(commit.id)} title="View changes">
                    <Eye size={10} /> Diff
                  </button>
                  {i > 0 && (
                    <button className="version-action-btn restore" onClick={() => restoreVersion(commit.id)} title="Restore">
                      <RotateCcw size={10} /> Restore
                    </button>
                  )}
                </div>

                {/* Diff view */}
                {expandedCommit === commit.id && diffData && (
                  <div className="version-diff">
                    {diffData.changes?.map((change, j) => (
                      <div key={j} className="version-diff-block">
                        <div className="diff-cell-header">
                          <FileText size={10} />
                          <span>Cell: {change.cell_name || change.cell_id?.slice(0, 8)}</span>
                          <span className={`diff-type ${change.type}`}>{change.type}</span>
                        </div>
                        {change.lines?.map((line, k) => (
                          <div key={k} className={`diff-line ${line.type}`}>
                            <span className="diff-marker">{line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}</span>
                            <span className="diff-content">{line.content}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                    {(!diffData.changes || diffData.changes.length === 0) && (
                      <div className="version-no-diff">No changes in this snapshot</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimeAgo(ts) {
  if (!ts) return '';
  const now = Date.now();
  const date = new Date(ts);
  const diff = now - date.getTime();
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}
