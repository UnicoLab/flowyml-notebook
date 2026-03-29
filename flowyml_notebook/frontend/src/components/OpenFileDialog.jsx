import React, { useState, useEffect, useCallback } from 'react';
import {
  Folder, ArrowUp, X, FolderOpen, ChevronRight,
  FileText, Clock, HardDrive, Loader2, File
} from 'lucide-react';

export default function OpenFileDialog({ open, onClose, onOpen, recentFiles = [] }) {
  const [path, setPath] = useState('');
  const [entries, setEntries] = useState([]);
  const [parentPath, setParentPath] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState(false);
  const [tab, setTab] = useState('browse'); // 'browse' | 'recent'

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
    if (open) browse();
  }, [open, browse]);

  const handleOpen = async (filePath) => {
    setOpening(true);
    try {
      await onOpen(filePath);
      onClose();
    } catch (e) { console.error(e); }
    setOpening(false);
  };

  if (!open) return null;

  const pathParts = path.split('/').filter(Boolean);
  const files = entries.filter(e => !e.is_dir);
  const dirs = entries.filter(e => e.is_dir);

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-container open-file-dialog" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="dialog-header">
          <div className="dialog-title">
            <FolderOpen size={16} />
            <span>Open Notebook</span>
          </div>
          <button className="btn-icon" onClick={onClose}><X size={16} /></button>
        </div>

        {/* Tabs */}
        <div className="dialog-tabs">
          <button
            className={`dialog-tab ${tab === 'browse' ? 'active' : ''}`}
            onClick={() => setTab('browse')}
          >
            <Folder size={12} /> Browse
          </button>
          <button
            className={`dialog-tab ${tab === 'recent' ? 'active' : ''}`}
            onClick={() => setTab('recent')}
          >
            <Clock size={12} /> Recent ({recentFiles.length})
          </button>
        </div>

        {tab === 'browse' ? (
          <>
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
              ) : (
                <>
                  {dirs.map((entry, i) => (
                    <div key={`d${i}`} className="browser-item dir" onClick={() => browse(entry.path)}>
                      <Folder size={14} />
                      <span className="browser-item-name">{entry.name}</span>
                    </div>
                  ))}
                  {files.map((entry, i) => (
                    <div
                      key={`f${i}`}
                      className="browser-item file openable"
                      onClick={() => handleOpen(entry.path)}
                    >
                      <FileText size={14} />
                      <span className="browser-item-name">{entry.name}</span>
                      <span className="browser-item-meta">
                        <Clock size={10} />
                        {entry.modified ? new Date(entry.modified).toLocaleDateString() : ''}
                      </span>
                    </div>
                  ))}
                  {dirs.length === 0 && files.length === 0 && (
                    <div className="browser-empty">No notebook files in this directory</div>
                  )}
                </>
              )}
            </div>
          </>
        ) : (
          /* Recent files tab */
          <div className="dialog-browser recent-files">
            {recentFiles.length === 0 ? (
              <div className="browser-empty">No recent files</div>
            ) : (
              recentFiles.map((file, i) => (
                <div
                  key={i}
                  className="browser-item file openable"
                  onClick={() => handleOpen(file.path)}
                >
                  <FileText size={14} />
                  <div className="recent-file-info">
                    <span className="browser-item-name">{file.name}</span>
                    <span className="recent-file-path">{file.path}</span>
                  </div>
                  <span className="browser-item-meta">
                    <Clock size={10} />
                    {file.opened_at ? new Date(file.opened_at).toLocaleDateString() : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {/* Footer */}
        {opening && (
          <div className="dialog-footer">
            <div className="dialog-actions">
              <Loader2 size={14} className="spin" /> Opening notebook...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
