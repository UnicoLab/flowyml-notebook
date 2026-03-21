import React, { useState, useEffect, useCallback } from 'react';
import {
  Folder, FolderOpen, FileText, FileCode, File, Image,
  ChevronDown, ChevronRight, RefreshCw, Home,
  FileSpreadsheet, Database, Settings, Package,
  Upload, Search
} from 'lucide-react';

const FILE_ICONS = {
  py: { icon: FileCode, color: '#3b82f6' },
  js: { icon: FileCode, color: '#f59e0b' },
  jsx: { icon: FileCode, color: '#06b6d4' },
  ts: { icon: FileCode, color: '#3b82f6' },
  tsx: { icon: FileCode, color: '#06b6d4' },
  css: { icon: FileCode, color: '#a855f7' },
  html: { icon: FileCode, color: '#ef4444' },
  json: { icon: Settings, color: '#f59e0b' },
  yaml: { icon: Settings, color: '#ef4444' },
  yml: { icon: Settings, color: '#ef4444' },
  toml: { icon: Settings, color: '#6b7280' },
  csv: { icon: FileSpreadsheet, color: '#22c55e' },
  tsv: { icon: FileSpreadsheet, color: '#22c55e' },
  md: { icon: FileText, color: '#6b7280' },
  txt: { icon: FileText, color: '#6b7280' },
  png: { icon: Image, color: '#ec4899' },
  jpg: { icon: Image, color: '#ec4899' },
  jpeg: { icon: Image, color: '#ec4899' },
  svg: { icon: Image, color: '#ec4899' },
  sql: { icon: Database, color: '#f59e0b' },
  pkl: { icon: Package, color: '#8b5cf6' },
  h5: { icon: Package, color: '#8b5cf6' },
  model: { icon: Package, color: '#8b5cf6' },
};

function getFileIcon(name, isDir) {
  if (isDir) return { icon: Folder, color: 'var(--accent-light)' };
  const ext = name.split('.').pop()?.toLowerCase();
  return FILE_ICONS[ext] || { icon: File, color: 'var(--fg-dim)' };
}

export default function FilesExplorer({ onFileOpen }) {
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(new Set(['']));
  const [search, setSearch] = useState('');

  const fetchTree = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/files');
      if (res.ok) setTree(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchTree(); }, [fetchTree]);

  const toggleDir = (path) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleUploadCSV = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv,.tsv,.txt';
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      await fetch('/api/upload-csv', { method: 'POST', body: formData });
      fetchTree();
    };
    input.click();
  };

  if (loading) {
    return (
      <div className="files-loading">
        <RefreshCw size={14} className="animate-spin" />
        <span>Loading files...</span>
      </div>
    );
  }

  const renderNode = (node, depth = 0) => {
    if (!node) return null;
    const { icon: Icon, color } = getFileIcon(node.name, node.is_dir);
    const isOpen = expanded.has(node.path);

    // Filter by search
    if (search && !node.name.toLowerCase().includes(search.toLowerCase())) {
      if (!node.is_dir) return null;
      // Check if any children match
      const childMatches = node.children?.some(c => 
        c.name.toLowerCase().includes(search.toLowerCase()) || c.is_dir
      );
      if (!childMatches) return null;
    }

    return (
      <div key={node.path}>
        <div
          className={`files-item ${node.is_dir ? 'dir' : 'file'}`}
          style={{ paddingLeft: depth * 16 + 8 }}
          onClick={() => {
            if (node.is_dir) toggleDir(node.path);
            else if (onFileOpen) onFileOpen(node);
          }}
        >
          {node.is_dir && (
            <span className="files-chevron">
              {isOpen ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            </span>
          )}
          {!node.is_dir && <span className="files-chevron" />}
          <Icon size={13} style={{ color, flexShrink: 0 }} />
          <span className="files-name">{node.name}</span>
          {!node.is_dir && node.size && (
            <span className="files-size">{formatSize(node.size)}</span>
          )}
        </div>
        {node.is_dir && isOpen && node.children?.map(child => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="files-explorer">
      <div className="files-toolbar">
        <div className="files-search-box">
          <Search size={11} />
          <input
            placeholder="Filter files..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button className="btn-icon" onClick={fetchTree} title="Refresh" style={{ width: 24, height: 24 }}>
          <RefreshCw size={11} />
        </button>
        <button className="btn-icon" onClick={handleUploadCSV} title="Upload CSV" style={{ width: 24, height: 24 }}>
          <Upload size={11} />
        </button>
      </div>

      <div className="files-tree">
        {tree ? renderNode(tree) : (
          <div className="files-empty">No files in workspace</div>
        )}
      </div>
    </div>
  );
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
