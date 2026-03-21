import React, { useState, useRef, useEffect } from 'react';
import {
  Play, RotateCcw, Save, PanelLeftClose, PanelLeftOpen,
  Sparkles, Zap, Command, ChevronDown, Rocket, Sun, Moon,
  GitBranch, Server, Check, X, FlaskConical, MessageSquare,
  ClipboardCheck, User, FileText, Globe
} from 'lucide-react';

export default function NotebookHeader({
  metadata, executing, onRunAll, onSave, onResetKernel, onLoadDemo,
  onToggleSidebar, onToggleAI, onToggleFlowyML, onToggleDAG, onToggleComments,
  onToggleReport, onToggleApp,
  onOpenPalette, onRenameNotebook, onRequestReview,
  sidebarOpen, rightPanel, theme, onToggleTheme,
  userProfile, commentCount = 0,
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const startEditing = () => {
    setEditValue(metadata?.name || 'untitled');
    setEditing(true);
  };

  const commitRename = () => {
    const name = editValue.trim();
    if (name && name !== (metadata?.name || 'untitled')) {
      onRenameNotebook?.(name);
    }
    setEditing(false);
  };

  const cancelEditing = () => {
    setEditing(false);
  };

  return (
    <header className="notebook-header">
      {/* Left */}
      <div className="flex items-center gap-2">
        <button className="btn-icon" onClick={onToggleSidebar} title="Toggle sidebar (⌘ \\)">
          {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>

        <div className="logo">
          <Zap size={18} />
          <span>FlowyML</span>
        </div>

        <div className="header-divider" />

        {editing ? (
          <div className="header-name-edit">
            <input
              ref={inputRef}
              className="header-name-input"
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') commitRename();
                if (e.key === 'Escape') cancelEditing();
              }}
              onBlur={commitRename}
            />
          </div>
        ) : (
          <button
            className="header-notebook-name"
            onClick={startEditing}
            title="Click to rename notebook"
          >
            {metadata?.name || 'untitled'}
          </button>
        )}
      </div>

      {/* Center - Quick actions */}
      <div className="flex items-center gap-1">
        <button
          className="btn btn-primary"
          onClick={onRunAll}
          disabled={!!executing}
          title="Run All (⌘ ⇧ Enter)"
        >
          <Play size={13} />
          {executing ? 'Running...' : 'Run All'}
        </button>

        <button className="btn btn-ghost" onClick={onSave} title="Save (⌘ S)">
          <Save size={13} />
        </button>

        <button className="btn btn-ghost" onClick={onResetKernel} title="Reset Kernel">
          <RotateCcw size={13} />
        </button>

        <button className="btn btn-ghost" onClick={onLoadDemo} title="Load Demo Notebook">
          <FlaskConical size={13} />
          Demo
        </button>

        <div className="header-divider" />

        {/* Command palette trigger */}
        <button className="btn btn-ghost gap-3" onClick={onOpenPalette} title="Command Palette (⌘ K)"
          style={{ minWidth: 160, justifyContent: 'space-between', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 8 }}>
          <span className="flex items-center gap-1.5 text-gray-500">
            <Command size={12} />
            Commands...
          </span>
          <kbd className="text-[10px] text-gray-600 bg-white/[0.04] px-1.5 py-0.5 rounded">⌘K</kbd>
        </button>
      </div>

      {/* Right */}
      <div className="header-actions">
        <button
          className={`btn btn-ghost ${rightPanel === 'comments' ? 'text-amber-400 bg-amber-500/10' : ''}`}
          onClick={onToggleComments}
          title="Comments"
          style={{ position: 'relative' }}
        >
          <MessageSquare size={13} />
          Comments
          {commentCount > 0 && (
            <span style={{
              position: 'absolute', top: -2, right: -4,
              background: '#ef4444', color: '#fff', fontSize: 9, fontWeight: 700,
              borderRadius: '50%', width: 16, height: 16,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {commentCount}
            </span>
          )}
        </button>

        <button
          className="btn btn-ghost"
          onClick={() => onRequestReview?.()}
          title="Request Review"
        >
          <ClipboardCheck size={13} />
          Review
        </button>

        <button
          className={`btn btn-ghost ${rightPanel === 'report' ? 'text-blue-400 bg-blue-500/10' : ''}`}
          onClick={onToggleReport}
          title="Generate Report"
        >
          <FileText size={13} />
          Report
        </button>

        <button
          className={`btn btn-ghost ${rightPanel === 'app' ? 'text-pink-400 bg-pink-500/10' : ''}`}
          onClick={onToggleApp}
          title="Publish as App"
        >
          <Globe size={13} />
          Publish
        </button>

        <div className="header-divider" />

        <button
          className={`btn btn-ghost ${rightPanel === 'dag' ? 'text-cyan-400 bg-cyan-500/10' : ''}`}
          onClick={onToggleDAG}
          title="Pipeline DAG (⌘ ⇧ D)"
        >
          <GitBranch size={13} />
          DAG
        </button>

        <button
          className={`btn btn-ghost ${rightPanel === 'flowyml' ? 'text-indigo-400 bg-indigo-500/10' : ''}`}
          onClick={onToggleFlowyML}
          title="FlowyML Production"
        >
          <Rocket size={13} />
          Production
        </button>

        <button
          className={`btn btn-ghost ${rightPanel === 'ai' ? 'text-purple-400 bg-purple-500/10' : ''}`}
          onClick={onToggleAI}
          title="AI Assistant (⌘ J)"
        >
          <Sparkles size={13} />
          AI
        </button>

        <div className="header-divider" />

        <button
          className="theme-toggle"
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* User Avatar */}
        {userProfile && (
          <div
            title={`${userProfile.name} (${userProfile.email})`}
            style={{
              width: 26, height: 26, borderRadius: '50%',
              background: userProfile.avatar_color || 'var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700, color: '#fff', cursor: 'default',
              marginLeft: 4,
            }}
          >
            {userProfile.initials || 'U'}
          </div>
        )}
      </div>
    </header>
  );
}
