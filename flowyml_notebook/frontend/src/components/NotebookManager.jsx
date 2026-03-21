import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileText, Plus, Edit3, Trash2, Copy, MoreHorizontal,
  Check, X, ChevronRight, Clock, Loader2, FolderOpen, AlertTriangle
} from 'lucide-react';

export default function NotebookManager({ onOpenNotebook, currentNotebookName, saveStatus }) {
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const renameRef = useRef(null);

  const fetchNotebooks = useCallback(async () => {
    try {
      const res = await fetch('/api/notebooks');
      if (res.ok) setNotebooks(await res.json());
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchNotebooks(); }, [fetchNotebooks]);

  // Re-fetch notebook list when save completes to update cell counts
  useEffect(() => {
    if (saveStatus === 'saved') fetchNotebooks();
  }, [saveStatus, fetchNotebooks]);

  useEffect(() => {
    if (renamingId && renameRef.current) {
      renameRef.current.focus();
      renameRef.current.select();
    }
  }, [renamingId]);

  // Auto-dismiss delete confirmation after 5s
  useEffect(() => {
    if (!deletingId) return;
    const timer = setTimeout(() => setDeletingId(null), 5000);
    return () => clearTimeout(timer);
  }, [deletingId]);

  const handleCreate = async () => {
    const name = newName.trim() || 'Untitled';
    try {
      const res = await fetch('/api/notebooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        setNewName('');
        setCreating(false);
        fetchNotebooks();
      }
    } catch (e) { /* ignore */ }
  };

  const handleRename = async (nbId) => {
    const name = renameValue.trim();
    if (!name) return;
    try {
      await fetch(`/api/notebooks/${nbId}/rename?name=${encodeURIComponent(name)}`, { method: 'PUT' });
      setRenamingId(null);
      fetchNotebooks();
    } catch (e) { /* ignore */ }
  };

  const handleDelete = async (nbId) => {
    try {
      await fetch(`/api/notebooks/${nbId}`, { method: 'DELETE' });
      setDeletingId(null);
      fetchNotebooks();
    } catch (e) { /* ignore */ }
  };

  const handleDuplicate = async (nbId) => {
    try {
      await fetch(`/api/notebooks/${nbId}/duplicate`, { method: 'POST' });
      fetchNotebooks();
    } catch (e) { /* ignore */ }
  };

  const handleOpen = async (nbId) => {
    try {
      const res = await fetch(`/api/notebooks/${nbId}/open`, { method: 'PUT' });
      if (res.ok && onOpenNotebook) {
        onOpenNotebook(await res.json());
      }
    } catch (e) { /* ignore */ }
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="notebook-manager">
      {/* Header with create button */}
      <div className="flex items-center justify-between mb-2">
        <span className="sidebar-section-title" style={{ marginBottom: 0 }}>Notebooks</span>
        <button className="btn-icon" onClick={() => setCreating(!creating)}
          style={{ width: 22, height: 22 }} title="New notebook">
          <Plus size={13} />
        </button>
      </div>

      {/* Inline create form */}
      {creating && (
        <div className="flex items-center gap-1.5 mb-2">
          <input
            className="sidebar-search flex-1"
            style={{ marginBottom: 0, fontSize: '11px', padding: '4px 8px' }}
            placeholder="Notebook name..."
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false); }}
            autoFocus
          />
          <button className="btn-icon" onClick={handleCreate} style={{ width: 22, height: 22, color: 'var(--accent)' }}>
            <Check size={12} />
          </button>
          <button className="btn-icon" onClick={() => setCreating(false)} style={{ width: 22, height: 22 }}>
            <X size={12} />
          </button>
        </div>
      )}

      {/* Notebook list */}
      {loading ? (
        <div className="flex items-center justify-center p-4 text-gray-500 text-xs">
          <Loader2 size={14} className="animate-spin mr-2" /> Loading...
        </div>
      ) : notebooks.length > 0 ? (
        <div className="space-y-0.5">
          {notebooks.map(nb => (
            <div key={nb.id}>
              {/* Delete confirmation banner */}
              {deletingId === nb.id && (
                <div
                  className="flex items-center gap-2 p-2 mb-0.5 rounded-md text-xs"
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                  }}
                  onClick={e => e.stopPropagation()}
                >
                  <AlertTriangle size={12} style={{ color: '#ef4444', flexShrink: 0 }} />
                  <span style={{ color: '#fca5a5', flex: 1 }}>Delete "{nb.name}"?</span>
                  <button
                    className="btn-icon"
                    style={{ width: 20, height: 20, color: '#ef4444', background: 'rgba(239, 68, 68, 0.15)', borderRadius: 4 }}
                    onClick={e => { e.stopPropagation(); handleDelete(nb.id); }}
                    title="Confirm delete"
                  >
                    <Check size={11} />
                  </button>
                  <button
                    className="btn-icon"
                    style={{ width: 20, height: 20 }}
                    onClick={e => { e.stopPropagation(); setDeletingId(null); }}
                    title="Cancel"
                  >
                    <X size={11} />
                  </button>
                </div>
              )}
              <div
                className={`group flex items-center gap-2 p-1.5 rounded-md hover:bg-white/[0.03] cursor-pointer transition-all ${
                  nb.name === currentNotebookName ? 'bg-white/[0.06] ring-1 ring-white/[0.08]' : ''
                }`}
                onClick={() => handleOpen(nb.id)}
              >
                <FileText size={13} className="text-gray-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  {renamingId === nb.id ? (
                    <input
                      ref={renameRef}
                      className="sidebar-search w-full"
                      style={{ marginBottom: 0, fontSize: '11px', padding: '2px 6px' }}
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleRename(nb.id); if (e.key === 'Escape') setRenamingId(null); }}
                      onBlur={() => handleRename(nb.id)}
                      onClick={e => e.stopPropagation()}
                    />
                  ) : (
                    <>
                      <div className="text-xs font-medium text-gray-300 truncate">{nb.name}</div>
                      <div className="text-[10px] text-gray-600">
                        {nb.cell_count} cells · {formatDate(nb.modified_at)}
                      </div>
                    </>
                  )}
                </div>
                
                {/* Action buttons — visible on hover */}
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="btn-icon" style={{ width: 18, height: 18 }}
                    onClick={e => { e.stopPropagation(); setRenamingId(nb.id); setRenameValue(nb.name); }}
                    title="Rename">
                    <Edit3 size={10} />
                  </button>
                  <button className="btn-icon" style={{ width: 18, height: 18 }}
                    onClick={e => { e.stopPropagation(); handleDuplicate(nb.id); }}
                    title="Duplicate">
                    <Copy size={10} />
                  </button>
                  <button className="btn-icon" style={{ width: 18, height: 18, color: '#ef4444' }}
                    onClick={e => { e.stopPropagation(); setDeletingId(nb.id); }}
                    title="Delete">
                    <Trash2 size={10} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-3 text-center text-gray-600 text-xs">
          <FolderOpen size={16} className="mx-auto mb-1 text-gray-500" />
          No notebooks yet.<br />
          Click <Plus size={10} style={{ display: 'inline', verticalAlign: -1 }} /> to create one.
        </div>
      )}
    </div>
  );
}
