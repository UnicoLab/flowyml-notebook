import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play, Save, RotateCcw, Download, Upload, Search, FileCode,
  BarChart3, Rocket, Clock, Zap, Sparkles, GitBranch,
  Plus, Code, Type, Database, Trash2, Settings, Moon, Sun, Layout,
  Command, FileText, Globe, Workflow, Box, Activity, Cpu, ToggleLeft,
  FlaskConical, Package, Eraser
} from 'lucide-react';

const ALL_COMMANDS = [
  { id: 'run-all', label: 'Run All Cells', shortcut: ['⌘', '⇧', 'Enter'], icon: Play, group: 'Execution' },
  { id: 'run-cell', label: 'Run Current Cell', shortcut: ['⇧', 'Enter'], icon: Play, group: 'Execution' },
  { id: 'reset-kernel', label: 'Reset Kernel', shortcut: ['⌘', '⇧', 'R'], icon: RotateCcw, group: 'Execution' },
  { id: 'add-code', label: 'Add Code Cell', shortcut: ['⌘', 'B'], icon: Code, group: 'Cells' },
  { id: 'add-markdown', label: 'Add Markdown Cell', shortcut: ['⌘', 'M'], icon: Type, group: 'Cells' },
  { id: 'add-sql', label: 'Add SQL Cell', icon: Database, group: 'Cells' },
  { id: 'delete-cell', label: 'Delete Cell', shortcut: ['⌘', '⌫'], icon: Trash2, group: 'Cells' },
  { id: 'clear-cell-output', label: 'Clear Cell Output', icon: Eraser, group: 'Cells' },
  { id: 'clear-all-outputs', label: 'Clear All Outputs', shortcut: ['⌘', '⇧', '⌫'], icon: Eraser, group: 'Cells' },
  { id: 'save', label: 'Save Notebook', shortcut: ['⌘', 'S'], icon: Save, group: 'File' },
  { id: 'export-pipeline', label: 'Export as Pipeline', icon: FileCode, group: 'File' },
  { id: 'export-html', label: 'Export HTML Report', icon: BarChart3, group: 'File' },
  { id: 'export-docker', label: 'Generate Dockerfile', icon: Layout, group: 'File' },
  { id: 'promote', label: 'Promote to Production Pipeline', icon: Rocket, group: 'FlowyML' },
  { id: 'deploy-model', label: 'Deploy Model', icon: Upload, group: 'FlowyML' },
  { id: 'schedule', label: 'Schedule Pipeline', icon: Clock, group: 'FlowyML' },
  { id: 'show-dag', label: 'View Dependency Graph', icon: GitBranch, group: 'FlowyML' },
  { id: 'connect', label: 'Connect to FlowyML Server', icon: Zap, group: 'FlowyML' },
  { id: 'insert-step', label: 'Insert @step', icon: Workflow, group: 'FlowyML Insert' },
  { id: 'insert-pipeline', label: 'Insert Pipeline', icon: GitBranch, group: 'FlowyML Insert' },
  { id: 'insert-branch', label: 'Insert Branch (If/Switch)', icon: Activity, group: 'FlowyML Insert' },
  { id: 'insert-context', label: 'Insert Context Config', icon: ToggleLeft, group: 'FlowyML Insert' },
  { id: 'insert-dataset', label: 'Insert Dataset Asset', icon: Database, group: 'FlowyML Insert' },
  { id: 'insert-model', label: 'Insert Model Asset', icon: Cpu, group: 'FlowyML Insert' },
  { id: 'insert-metrics', label: 'Insert Metrics Asset', icon: BarChart3, group: 'FlowyML Insert' },
  { id: 'insert-parallel', label: 'Insert Parallel Execution', icon: Box, group: 'FlowyML Insert' },
  { id: 'insert-experiment', label: 'Insert Experiment Tracking', icon: FlaskConical, group: 'FlowyML Insert' },
  { id: 'insert-registry', label: 'Insert Model Registry', icon: Package, group: 'FlowyML Insert' },
  { id: 'pipeline-wizard', label: 'Open Pipeline Builder Wizard', icon: Workflow, group: 'FlowyML Insert' },
  { id: 'wrap-in-step', label: 'Wrap Current Cell in @step', icon: Zap, group: 'FlowyML Insert' },
  { id: 'report', label: 'Generate Report', icon: FileText, group: 'Publish' },
  { id: 'publish-app', label: 'Publish as App', icon: Globe, group: 'Publish' },
  { id: 'ai-assist', label: 'Open AI Assistant', shortcut: ['⌘', 'J'], icon: Sparkles, group: 'Tools' },
  { id: 'find', label: 'Find in Notebook', shortcut: ['⌘', 'F'], icon: Search, group: 'Tools' },
];

export default function CommandPalette({ open, onClose, onCommand }) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Global shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (open) onClose(); else onCommand('__open_palette');
      }
      if (e.key === 'Escape' && open) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose, onCommand]);

  const filtered = useMemo(() => {
    if (!query) return ALL_COMMANDS;
    const q = query.toLowerCase();
    return ALL_COMMANDS.filter(c =>
      c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q)
    );
  }, [query]);

  // Group results
  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach(cmd => {
      if (!groups[cmd.group]) groups[cmd.group] = [];
      groups[cmd.group].push(cmd);
    });
    return groups;
  }, [filtered]);

  const flatList = filtered;

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, flatList.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (flatList[selected]) {
        onCommand(flatList[selected].id);
        onClose();
      }
    }
  };

  if (!open) return null;

  let itemIdx = -1;

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div className="command-palette" onClick={e => e.stopPropagation()}>
        <div className="flex items-center px-4 gap-2 border-b border-white/5">
          <Command size={14} className="text-gray-500" />
          <input
            ref={inputRef}
            className="command-palette-input"
            placeholder="Type a command..."
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={handleKeyDown}
            style={{ border: 'none', borderBottom: 'none', padding: '0.875rem 0' }}
          />
          <kbd className="text-[10px] text-gray-600 bg-white/[0.03] px-1.5 py-0.5 rounded border border-white/5">ESC</kbd>
        </div>
        <div className="command-list">
          {Object.entries(grouped).map(([group, commands]) => (
            <div key={group}>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">{group}</div>
              {commands.map(cmd => {
                itemIdx++;
                const idx = itemIdx;
                return (
                  <div key={cmd.id}
                    className={`command-item ${selected === idx ? 'selected' : ''}`}
                    onClick={() => { onCommand(cmd.id); onClose(); }}
                    onMouseEnter={() => setSelected(idx)}>
                    <div className="flex items-center gap-2.5">
                      <cmd.icon size={14} className="text-gray-500" />
                      <span className="label">{cmd.label}</span>
                    </div>
                    {cmd.shortcut && (
                      <div className="shortcut">
                        {cmd.shortcut.map((k, ki) => <kbd key={ki}>{k}</kbd>)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
          {flatList.length === 0 && (
            <div className="text-center text-gray-600 text-sm py-6">No commands found</div>
          )}
        </div>
      </div>
    </div>
  );
}
