import React, { useCallback, useRef, useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import CellOutput from './CellOutput';
import MarkdownRenderer from './MarkdownRenderer';
import {
  Play, Trash2, Copy, ChevronDown, ChevronRight,
  Code, Type, Database, GripVertical, Eye, EyeOff,
  MoreHorizontal, Clock, ArrowUpDown, Check,
  Cpu, HardDrive, Activity, Gauge, Zap, Workflow,
  Plus, ToggleLeft, Tag, FileCode
} from 'lucide-react';
import { detectFlowyML, wrapInStep, DETECTION_BADGES, extractAllArtifacts, getArtifactType } from '../data/flowymlSnippets';

const CELL_TYPE_CONFIG = {
  code: { icon: Code, label: 'Python', language: 'python', badge: 'code' },
  markdown: { icon: Type, label: 'Markdown', language: 'markdown', badge: 'markdown' },
  sql: { icon: Database, label: 'SQL', language: 'sql', badge: 'sql' },
};

// Use shared DETECTION_BADGES from flowymlSnippets.js

export default function CellEditor({
  cell, state, focused, executing, theme,
  upstream, downstream,
  onFocus, onUpdate, onExecute, onDelete, onWrapInStep,
}) {
  const editorRef = useRef(null);
  const [collapsed, setCollapsed] = useState(false);
  const [outputVisible, setOutputVisible] = useState(true);
  const [copied, setCopied] = useState(false);
  const config = CELL_TYPE_CONFIG[cell.cell_type] || CELL_TYPE_CONFIG.code;

  // Detect FlowyML constructs in this cell
  const flowymlDetections = useMemo(() => {
    if (cell.cell_type !== 'code') return null;
    return detectFlowyML(cell.source);
  }, [cell.source, cell.cell_type]);

  // Extract artifact I/O for pill badges
  const cellArtifacts = useMemo(() => {
    if (cell.cell_type !== 'code') return null;
    const arts = extractAllArtifacts(cell.source);
    if (arts.inputs.length === 0 && arts.outputs.length === 0 && arts.assets.length === 0) return null;
    return arts;
  }, [cell.source, cell.cell_type]);

  const canWrapInStep = useMemo(() => {
    return cell.cell_type === 'code'
      && cell.source?.trim()
      && !flowymlDetections?.includes('step')
      && onWrapInStep;
  }, [cell.cell_type, cell.source, flowymlDetections, onWrapInStep]);

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

  const handleWrapInStep = useCallback(() => {
    if (!onWrapInStep) return;
    const wrapped = wrapInStep(cell.source, cell.name);
    onWrapInStep(wrapped);
  }, [cell.source, cell.name, onWrapInStep]);

  // --- Step-specific quick actions ---
  const handleAddStepInput = useCallback(() => {
    const src = cell.source || '';
    const updated = src.replace(
      /@step\(([^)]*)\)/,
      (match, args) => {
        if (args.includes('inputs=')) return match;
        const newArg = args ? `, inputs=["data/input"]` : `inputs=["data/input"]`;
        return `@step(${args}${newArg})`;
      }
    );
    onUpdate(updated);
  }, [cell.source, onUpdate]);

  const handleAddStepOutput = useCallback(() => {
    const src = cell.source || '';
    const updated = src.replace(
      /@step\(([^)]*)\)/,
      (match, args) => {
        if (args.includes('outputs=')) return match;
        const newArg = args ? `, outputs=["data/output"]` : `outputs=["data/output"]`;
        return `@step(${args}${newArg})`;
      }
    );
    onUpdate(updated);
  }, [cell.source, onUpdate]);

  const handleToggleCache = useCallback(() => {
    const src = cell.source || '';
    const hasCache = /cache\s*=\s*True/.test(src);
    let updated;
    if (hasCache) {
      updated = src.replace(/,?\s*cache\s*=\s*True/, '');
    } else {
      updated = src.replace(
        /@step\(([^)]*)\)/,
        (match, args) => `@step(${args}${args ? ', ' : ''}cache=True)`
      );
    }
    onUpdate(updated);
  }, [cell.source, onUpdate]);

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

          {/* FlowyML detection badges */}
          {flowymlDetections && flowymlDetections.map(detection => {
            const badge = DETECTION_BADGES[detection];
            if (!badge) return null;
            return (
              <span
                key={detection}
                className="flowyml-cell-badge"
                style={{ '--badge-color': badge.color }}
              >
                <Zap size={8} />
                {badge.label}
              </span>
            );
          })}
        </div>

        <div className="cell-toolbar-right">
          {hasExecData && (
            <span className={`cell-metric-badge ${speedClass(cell.duration_seconds)}`}
              title={`Wall: ${fmtDuration(cell.duration_seconds)}`}>
              <Zap size={9} />
              {fmtDuration(cell.duration_seconds)}
            </span>
          )}

          {/* Wrap in Step button */}
          {canWrapInStep && (
            <button
              className="flowyml-wrap-btn"
              onClick={(e) => { e.stopPropagation(); handleWrapInStep(); }}
              title="Wrap in FlowyML @step"
            >
              <Workflow size={11} />
              <span>Wrap in Step</span>
            </button>
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

      {/* FlowyML Contextual Actions Bar (for detected constructs) */}
      {!collapsed && flowymlDetections && flowymlDetections.length > 0 && focused && (
        <div className="flowyml-actions-bar">
          {flowymlDetections.includes('step') && (
            <>
              <button className="flowyml-action-btn" onClick={handleAddStepInput} title="Add input declaration">
                <Plus size={10} /> Input
              </button>
              <button className="flowyml-action-btn" onClick={handleAddStepOutput} title="Add output declaration">
                <Plus size={10} /> Output
              </button>
              <button className="flowyml-action-btn" onClick={handleToggleCache} title="Toggle @step cache">
                <ToggleLeft size={10} /> Cache
              </button>
            </>
          )}
          {flowymlDetections.includes('pipeline') && (
            <>
              <button className="flowyml-action-btn" onClick={() => {
                const src = cell.source || '';
                onUpdate(src + '\n# pipeline.add_step(my_step)  # TODO: add your step');
              }}>
                <Plus size={10} /> Add Step
              </button>
            </>
          )}
          {flowymlDetections.includes('context') && (
            <button className="flowyml-action-btn" onClick={() => {
              const src = cell.source || '';
              // Insert a new param line before the closing paren
              const updated = src.replace(
                /(\n\s*\))/,
                '\n    new_param="value",  # TODO: update$1'
              );
              onUpdate(updated);
            }}>
              <Plus size={10} /> Add Param
            </button>
          )}
          <span className="flowyml-actions-label">
            <Zap size={9} /> FlowyML
          </span>
        </div>
      )}

      {/* ── Premium Artifact I/O Panel ── */}
      {!collapsed && cellArtifacts && (
        <div className="cell-artifact-panel">
          {cellArtifacts.inputs.length > 0 && (
            <div className="artifact-io-group inputs">
              <span className="io-group-label">
                <span className="io-arrow">↓</span> INPUTS
              </span>
              <div className="io-group-items">
                {cellArtifacts.inputs.map(art => {
                  const t = getArtifactType(art);
                  return (
                    <span key={`in-${art}`} className="artifact-chip" style={{ '--chip-color': t.color }}>
                      <span className="chip-icon">{t.icon}</span>
                      <span className="chip-name">{art}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
          {cellArtifacts.inputs.length > 0 && cellArtifacts.outputs.length > 0 && (
            <div className="io-flow-arrow">
              <svg width="20" height="14" viewBox="0 0 20 14"><path d="M0 7h14m0 0l-4-4m4 4l-4 4" stroke="var(--fg-dim)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
          )}
          {cellArtifacts.outputs.length > 0 && (
            <div className="artifact-io-group outputs">
              <span className="io-group-label">
                <span className="io-arrow">↑</span> OUTPUTS
              </span>
              <div className="io-group-items">
                {cellArtifacts.outputs.map(art => {
                  const t = getArtifactType(art);
                  return (
                    <span key={`out-${art}`} className="artifact-chip" style={{ '--chip-color': t.color }}>
                      <span className="chip-icon">{t.icon}</span>
                      <span className="chip-name">{art}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
          {cellArtifacts.assets.length > 0 && (
            <div className="artifact-io-group assets">
              <span className="io-group-label">
                <span className="io-arrow">◆</span> ASSETS
              </span>
              <div className="io-group-items">
                {cellArtifacts.assets.map((asset, i) => (
                  <span key={`asset-${i}`} className="artifact-chip asset-chip" style={{ '--chip-color': asset.color }}>
                    <span className="chip-icon">{asset.icon}</span>
                    <span className="chip-name">{asset.name}</span>
                    <span className="chip-badge">{asset.type}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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
