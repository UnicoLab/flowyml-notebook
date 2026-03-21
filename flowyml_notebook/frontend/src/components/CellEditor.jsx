import React, { useCallback, useRef, useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import CellOutput from './CellOutput';
import MarkdownRenderer from './MarkdownRenderer';
import {
  Play, Trash2, Copy, ChevronDown, ChevronRight,
  Code, Type, Database, GripVertical, Eye, EyeOff,
  MoreHorizontal, Clock, ArrowUpDown, Check,
  Cpu, HardDrive, Activity, Gauge, Zap
} from 'lucide-react';

const CELL_TYPE_CONFIG = {
  code: { icon: Code, label: 'Python', language: 'python', badge: 'code' },
  markdown: { icon: Type, label: 'Markdown', language: 'markdown', badge: 'markdown' },
  sql: { icon: Database, label: 'SQL', language: 'sql', badge: 'sql' },
};

export default function CellEditor({
  cell, state, focused, executing, theme,
  upstream, downstream,
  onFocus, onUpdate, onExecute, onDelete,
}) {
  const editorRef = useRef(null);
  const [collapsed, setCollapsed] = useState(false);
  const [outputVisible, setOutputVisible] = useState(true);
  const [copied, setCopied] = useState(false);
  const config = CELL_TYPE_CONFIG[cell.cell_type] || CELL_TYPE_CONFIG.code;

  const stateClass = state === 'idle' ? '' :
    state === 'success' ? 'state-success' :
    state === 'error' ? 'state-error' :
    state === 'stale' ? 'state-stale' :
    state === 'running' ? 'state-running' : '';

  const lineCount = useMemo(() => (cell.source?.split('\n').length || 1), [cell.source]);
  const editorHeight = Math.max(56, Math.min(400, lineCount * 19 + 16));

  const handleEditorMount = useCallback((editor) => {
    editorRef.current = editor;
    editor.addCommand(2048 | 3, () => onExecute());
    editor.addCommand(2048 | 2048 | 3, () => onExecute());
  }, [onExecute]);

  const handleChange = useCallback((value) => {
    onUpdate(value || '');
  }, [onUpdate]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(cell.source || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [cell.source]);

  // Format duration nicely
  const fmtDuration = (s) => {
    if (!s || s === 0) return null;
    if (s < 0.001) return '<1ms';
    if (s < 0.01) return `${(s * 1000).toFixed(1)}ms`;
    if (s < 1) return `${(s * 1000).toFixed(0)}ms`;
    if (s < 60) return `${s.toFixed(2)}s`;
    return `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
  };

  const fmtMemory = (mb) => {
    if (!mb || mb === 0) return null;
    if (Math.abs(mb) < 1) return `${(mb * 1024).toFixed(0)} KB`;
    return `${mb.toFixed(1)} MB`;
  };

  const speedClass = (s) => {
    if (!s) return '';
    if (s < 1) return 'fast';
    if (s < 5) return 'medium';
    return 'slow';
  };

  const hasExecData = cell.execution_count > 0 && cell.duration_seconds !== undefined;

  // Markdown rendered view (when not focused)
  if (cell.cell_type === 'markdown' && !focused) {
    return (
      <div className={`cell ${stateClass}`} onClick={onFocus}>
        <MarkdownRenderer source={cell.source || '*Click to edit...*'} />
      </div>
    );
  }

  return (
    <div className={`cell ${stateClass} ${focused ? 'focused' : ''}`} onClick={onFocus}>
      {/* Cell Toolbar */}
      <div className="cell-toolbar">
        <div className="cell-toolbar-left">
          <div className="text-gray-700 cursor-grab active:cursor-grabbing hover:text-gray-500 transition-colors">
            <GripVertical size={12} />
          </div>

          <button className="btn-icon" style={{ width: 20, height: 20 }}
            onClick={(e) => { e.stopPropagation(); setCollapsed(!collapsed); }}>
            {collapsed ? <ChevronRight size={11} /> : <ChevronDown size={11} />}
          </button>

          <span className={`cell-badge ${config.badge}`}>
            <config.icon size={10} />
            {config.label}
          </span>

          {cell.label && (
            <span className="text-[10px] font-mono text-gray-500 ml-1.5">
              {cell.label}
            </span>
          )}

          {cell.execution_count > 0 && (
            <span className="text-[9px] text-gray-600 font-mono ml-1">[{cell.execution_count}]</span>
          )}

          {upstream?.length > 0 && (
            <span className="dep-badge" title={`Depends on: ${upstream.join(', ')}`}>
              <ArrowUpDown size={9} /> {upstream.length}
            </span>
          )}
        </div>

        <div className="cell-toolbar-right">
          {hasExecData && (
            <span className={`cell-metric-badge ${speedClass(cell.duration_seconds)}`}
              title={`Wall: ${fmtDuration(cell.duration_seconds)}`}>
              <Zap size={9} />
              {fmtDuration(cell.duration_seconds)}
            </span>
          )}

          {cell.outputs?.length > 0 && (
            <button className="btn-icon" style={{ width: 24, height: 24 }}
              onClick={(e) => { e.stopPropagation(); setOutputVisible(!outputVisible); }}
              title={outputVisible ? 'Hide output' : 'Show output'}>
              {outputVisible ? <Eye size={11} /> : <EyeOff size={11} />}
            </button>
          )}

          <button
            className="btn-icon"
            style={{ width: 26, height: 26 }}
            onClick={(e) => { e.stopPropagation(); onExecute(); }}
            title="Run cell (Shift+Enter)"
            disabled={executing}
          >
            <Play size={13} className={executing ? 'animate-pulse text-purple-400' : 'text-gray-500 hover:text-indigo-400'} />
          </button>

          <button className="btn-icon" style={{ width: 24, height: 24 }}
            onClick={(e) => { e.stopPropagation(); handleCopy(); }}
            title="Copy code">
            {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
          </button>

          <button className="btn-icon" style={{ width: 24, height: 24 }}
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            title="Delete cell">
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Editor (collapsible) */}
      {!collapsed && (
        <div className="cell-editor">
          <Editor
            height={editorHeight}
            language={config.language}
            value={cell.source || ''}
            theme={theme === 'light' ? 'vs' : 'vs-dark'}
            onChange={handleChange}
            onMount={handleEditorMount}
            options={{
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              lineNumbersMinChars: 3,
              glyphMargin: false,
              folding: true,
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Menlo', monospace",
              fontLigatures: true,
              renderWhitespace: 'none',
              tabSize: 4,
              insertSpaces: true,
              wordWrap: 'on',
              automaticLayout: true,
              padding: { top: 8, bottom: 8 },
              overviewRulerLanes: 0,
              hideCursorInOverviewRuler: true,
              overviewRulerBorder: false,
              scrollbar: {
                vertical: 'hidden',
                horizontal: 'auto',
                verticalScrollbarSize: 0,
              },
              contextmenu: true,
              suggest: { showWords: true },
              quickSuggestions: true,
              bracketPairColorization: { enabled: true },
              guides: { bracketPairs: true, indentation: true },
              renderLineHighlight: 'line',
              renderLineHighlightOnlyWhenFocus: true,
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              smoothScrolling: true,
            }}
          />
        </div>
      )}

      {/* Collapsed preview */}
      {collapsed && (
        <div className="px-3 py-2 text-xs text-gray-500 font-mono truncate cursor-pointer"
          onClick={() => setCollapsed(false)}>
          {cell.source?.split('\n')[0] || '(empty)'}
          {lineCount > 1 && <span className="text-gray-700 ml-2">+{lineCount - 1} lines</span>}
        </div>
      )}

      {/* Output */}
      {outputVisible && cell.outputs && cell.outputs.length > 0 && (
        <CellOutput outputs={cell.outputs} />
      )}

      {/* Execution Stats Footer */}
      {hasExecData && (
        <div className="cell-exec-footer">
          <div className="exec-stat" title={`Wall time: ${fmtDuration(cell.duration_seconds)}`}>
            <Clock size={10} />
            <span className="exec-stat-label">Wall</span>
            <span className={`exec-stat-value ${speedClass(cell.duration_seconds)}`}>
              {fmtDuration(cell.duration_seconds)}
            </span>
          </div>

          {cell.cpu_time_s > 0 && (
            <div className="exec-stat" title={`CPU time: ${fmtDuration(cell.cpu_time_s)}`}>
              <Cpu size={10} />
              <span className="exec-stat-label">CPU</span>
              <span className="exec-stat-value">{fmtDuration(cell.cpu_time_s)}</span>
            </div>
          )}

          {cell.memory_delta_mb !== 0 && (
            <div className="exec-stat" title={`Memory delta: ${cell.memory_delta_mb > 0 ? '+' : ''}${fmtMemory(cell.memory_delta_mb)}`}>
              <Activity size={10} />
              <span className="exec-stat-label">Δ Mem</span>
              <span className={`exec-stat-value ${cell.memory_delta_mb > 50 ? 'warn' : ''}`}>
                {cell.memory_delta_mb > 0 ? '+' : ''}{fmtMemory(cell.memory_delta_mb)}
              </span>
            </div>
          )}

          {cell.peak_memory_mb > 0 && (
            <div className="exec-stat" title={`Peak process memory: ${fmtMemory(cell.peak_memory_mb)}`}>
              <Gauge size={10} />
              <span className="exec-stat-label">Peak</span>
              <span className="exec-stat-value">{fmtMemory(cell.peak_memory_mb)}</span>
            </div>
          )}

          <div className="exec-stat" title={`Run count: ${cell.execution_count}`}>
            <HardDrive size={10} />
            <span className="exec-stat-label">Run</span>
            <span className="exec-stat-value">#{cell.execution_count}</span>
          </div>
        </div>
      )}
    </div>
  );
}
