import React, { useState, useEffect, useCallback } from 'react';
import {
  Folder, FolderOpen, File, ChevronRight, ArrowUp, X, Save,
  Clock, FileText, HardDrive, Loader2
} from 'lucide-react';

export default function SaveAsDialog({ open, onClose, onSave, currentName }) {
  const [path, setPath] = useState('');
  const [entries, setEntries] = useState([]);
  const [parentPath, setParentPath] = useState(null);
  const [name, setName] = useState(currentName || 'untitled');
  const [format, setFormat] = useState('both');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const browse = useCallback(async (dir = '') => {
    setLoading(true);
    try {
      const res = await fetch(`/api/browse-dirs?path=${encodeURIComponent(dir)}`);
      const data = await res.json();
      setPath(data.current || '');
      setParentPath(data.parent || null);
      setEntries(data.entries || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (open) {
      setName(currentName || 'untitled');
      browse();
    }
  }, [open, currentName, browse]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({ path, name: name.trim(), format });
      onClose();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  if (!open) return null;

  const pathParts = path.split('/').filter(Boolean);

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-container save-as-dialog" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="dialog-header">
          <div className="dialog-title">
            <Save size={16} />
            <span>Save Notebook As</span>
          </div>
          <button className="btn-icon" onClick={onClose}><X size={16} /></button>
        </div>

        {/* Breadcrumb */}
        <div className="dialog-breadcrumb">
          <button className="breadcrumb-item" onClick={() => browse('/')}>
            <HardDrive size={12} />
          </button>
          {pathParts.map((part, i) => (
            <React.Fragment key={i}>
              <ChevronRight size={10} className="breadcrumb-sep" />
              <button
                className="breadcrumb-item"
                onClick={() => browse('/' + pathParts.slice(0, i + 1).join('/'))}
              >
                {part}
              </button>
            </React.Fragment>
          ))}
        </div>

        {/* Directory browser */}
        <div className="dialog-browser">
          {parentPath && (
            <div className="browser-item parent" onClick={() => browse(parentPath)}>
              <ArrowUp size={14} />
              <span>..</span>
            </div>
          )}
          {loading ? (
            <div className="browser-loading"><Loader2 size={16} className="spin" /> Loading...</div>
          ) : entries.length === 0 ? (
            <div className="browser-empty">Empty directory</div>
          ) : (
            entries.map((entry, i) => (
              <div
                key={i}
                className={`browser-item ${entry.is_dir ? 'dir' : 'file'}`}
                onClick={() => entry.is_dir && browse(entry.path)}
              >
                {entry.is_dir ? <Folder size={14} /> : <FileText size={14} />}
                <span className="browser-item-name">{entry.name}</span>
                {!entry.is_dir && entry.modified && (
                  <span className="browser-item-meta">
                    <Clock size={10} />
                    {new Date(entry.modified).toLocaleDateString()}
                  </span>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer: name + format + save */}
        <div className="dialog-footer">
          <div className="dialog-footer-row">
            <label className="dialog-label">Name</label>
            <input
              className="dialog-input"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              placeholder="Notebook name..."
              autoFocus
            />
          </div>
          <div className="dialog-footer-row">
            <label className="dialog-label">Format</label>
            <div className="dialog-format-group">
              {[
                { value: 'both', label: '.py + .json' },
                { value: 'py', label: '.py only' },
                { value: 'json', label: '.json only' },
              ].map(opt => (
                <button
                  key={opt.value}
                  className={`format-btn ${format === opt.value ? 'active' : ''}`}
                  onClick={() => setFormat(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="dialog-actions">
            <button className="dialog-btn secondary" onClick={onClose}>Cancel</button>
            <button className="dialog-btn primary" onClick={handleSave} disabled={saving || !name.trim()}>
              {saving ? <><Loader2 size={14} className="spin" /> Saving...</> : <><Save size={14} /> Save</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
