import React, { useState, useCallback, useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useNotebook } from './hooks/useNotebook';
import NotebookHeader from './components/NotebookHeader';
import CellList from './components/CellList';
import Sidebar from './components/Sidebar';
import StatusBar from './components/StatusBar';
import AIPanel from './components/AIPanel';
import FlowyMLPanel from './components/FlowyMLPanel';
import CommandPalette from './components/CommandPalette';
import PipelineDAG from './components/PipelineDAG';
import CommentsPanel from './components/CommentsPanel';
import ReportGenerator from './components/ReportGenerator';
import AppPublisher from './components/AppPublisher';
import AnalysisPatternsPanel from './components/AnalysisPatternsPanel';
import PipelineWizard from './components/PipelineWizard';
import { FLOWYML_SNIPPETS } from './data/flowymlSnippets';
import { wrapInStep } from './data/flowymlSnippets';

export default function App() {
  const notebook = useNotebook();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightPanel, setRightPanel] = useState(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [focusedCellId, setFocusedCellId] = useState(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('fml-theme') || 'dark');

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('fml-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(t => t === 'dark' ? 'light' : 'dark');
  }, []);

  const handleCommand = useCallback((cmd) => {
    switch (cmd) {
      case '__open_palette': setPaletteOpen(true); return;
      case 'run-all': notebook.executeAll(); break;
      case 'run-cell': if (focusedCellId) notebook.executeCell(focusedCellId); break;
      case 'reset-kernel': notebook.resetKernel(); break;
      case 'add-code': notebook.addCell('code'); break;
      case 'add-markdown': notebook.addCell('markdown'); break;
      case 'add-sql': notebook.addCell('sql'); break;
      case 'delete-cell': if (focusedCellId) notebook.deleteCell(focusedCellId); break;
      case 'save': notebook.saveNotebook(); break;
      case 'export-pipeline': handleAction('export', { format: 'pipeline' }); break;
      case 'export-html': handleAction('export', { format: 'html' }); break;
      case 'promote': handleAction('promote'); break;
      case 'deploy-model': handleAction('deploy-model'); break;
      case 'schedule': setRightPanel('flowyml'); break;
      case 'show-dag': setRightPanel(p => p === 'dag' ? null : 'dag'); break;
      case 'connect': break;
      case 'ai-assist': setRightPanel(p => p === 'ai' ? null : 'ai'); break;
      case 'comments': setRightPanel(p => p === 'comments' ? null : 'comments'); break;
      case 'report': setRightPanel(p => p === 'report' ? null : 'report'); break;
      case 'publish-app': setRightPanel(p => p === 'app' ? null : 'app'); break;
      case 'patterns': setRightPanel(p => p === 'patterns' ? null : 'patterns'); break;
      case 'find': break;
    }

    // FlowyML snippet insertion commands from CommandPalette
    const snippetMap = {
      'insert-step': 'fml-step',
      'insert-pipeline': 'fml-pipeline',
      'insert-branch': 'fml-branch',
      'insert-context': 'fml-context',
      'insert-dataset': 'fml-dataset',
      'insert-model': 'fml-model',
      'insert-metrics': 'fml-metrics',
      'insert-parallel': 'fml-parallel',
      'insert-experiment': 'fml-experiment',
      'insert-registry': 'fml-registry',
    };
    if (snippetMap[cmd]) {
      const snippet = FLOWYML_SNIPPETS.find(s => s.id === snippetMap[cmd]);
      if (snippet) notebook.insertCellWithSource(snippet.source, snippet.name);
      return;
    }
    if (cmd === 'pipeline-wizard') {
      setWizardOpen(true);
      return;
    }
    if (cmd === 'wrap-in-step') {
      if (focusedCellId) {
        const cell = notebook.cells.find(c => c.id === focusedCellId);
        if (cell && cell.source) {
          const wrapped = wrapInStep(cell.source, cell.name);
          notebook.updateCell(focusedCellId, wrapped);
        }
      }
      return;
    }
  }, [notebook, focusedCellId]);

  const handleAction = useCallback(async (action, payload) => {
    switch (action) {
      case 'execute-all': notebook.executeAll(); break;
      case 'export':
        try {
          const res = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json();
          console.log('Export:', data);
        } catch (e) { console.error(e); }
        break;
      case 'promote':
        try {
          await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format: 'pipeline' }),
          });
        } catch (e) { console.error(e); }
        break;
      case 'deploy':
      case 'deploy-model':
        console.log('Deploy:', payload);
        break;
      case 'schedule':
        try {
          await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
        } catch (e) { console.error(e); }
        break;
    }
  }, [notebook]);

  // Global keyboard shortcuts
  React.useEffect(() => {
    const handler = (e) => {
      // Cmd+S → Save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        notebook.saveNotebook();
      }
      // Cmd+Shift+Enter → Run all
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'Enter') {
        e.preventDefault();
        notebook.executeAll();
      }
      // Cmd+Shift+D → Toggle DAG
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'd') {
        e.preventDefault();
        setRightPanel(p => p === 'dag' ? null : 'dag');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [notebook]);

  const scrollToCell = useCallback((cellId) => {
    setFocusedCellId(cellId);
    const el = document.getElementById(`cell-${cellId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, []);

  // Pending reviews count for badge
  const pendingReviews = notebook.reviews.filter(r => r.status === 'pending').length;
  const openComments = notebook.comments.filter(c => !c.resolved).length;

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--bg-primary)', color: 'var(--fg-primary)' }}>
      {/* Review Banner */}
      {pendingReviews > 0 && (
        <div style={{
          padding: '6px 16px', display: 'flex', alignItems: 'center', gap: 8,
          background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(139,92,246,0.12))',
          borderBottom: '1px solid rgba(59,130,246,0.2)',
          fontSize: 12,
        }}>
          <span style={{ fontWeight: 600, color: '#93c5fd' }}>📋 {pendingReviews} pending review{pendingReviews > 1 ? 's' : ''}</span>
          <span style={{ flex: 1 }} />
          {notebook.reviews.filter(r => r.status === 'pending').map(r => (
            <div key={r.id} style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => notebook.updateReview(r.id, { status: 'approved' })}
                style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                  background: 'rgba(34,197,94,0.15)', color: '#4ade80', border: 'none', cursor: 'pointer',
                }}
              >
                ✓ Approve
              </button>
              <button
                onClick={() => notebook.updateReview(r.id, { status: 'rejected' })}
                style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                  background: 'rgba(239,68,68,0.15)', color: '#f87171', border: 'none', cursor: 'pointer',
                }}
              >
                ✗ Request Changes
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Header */}
      <NotebookHeader
        metadata={notebook.metadata}
        executing={notebook.executing}
        staleCellCount={notebook.staleCellIds?.length || 0}
        onRunAll={notebook.executeAll}
        onRunStale={notebook.runStaleCells}
        onSave={() => notebook.saveNotebook()}
        onResetKernel={notebook.resetKernel}
        onLoadDemo={notebook.loadDemo}
        onRenameNotebook={notebook.renameNotebook}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onToggleAI={() => setRightPanel(p => p === 'ai' ? null : 'ai')}
        onToggleFlowyML={() => setRightPanel(p => p === 'flowyml' ? null : 'flowyml')}
        onToggleDAG={() => setRightPanel(p => p === 'dag' ? null : 'dag')}
        onToggleComments={() => setRightPanel(p => p === 'comments' ? null : 'comments')}
        onToggleReport={() => setRightPanel(p => p === 'report' ? null : 'report')}
        onToggleApp={() => setRightPanel(p => p === 'app' ? null : 'app')}
        onTogglePatterns={() => setRightPanel(p => p === 'patterns' ? null : 'patterns')}
        onOpenPalette={() => setPaletteOpen(true)}
        onRequestReview={notebook.requestReview}
        sidebarOpen={sidebarOpen}
        rightPanel={rightPanel}
        theme={theme}
        onToggleTheme={toggleTheme}
        userProfile={notebook.userProfile}
        commentCount={openComments}
      />

      {/* Main Content — Resizable Panels */}
      <PanelGroup direction="horizontal" autoSaveId="fml-layout" className="flex-1 overflow-hidden">
        {/* Left Sidebar */}
        {sidebarOpen && (
          <>
            <Panel
              id="sidebar"
              order={1}
              defaultSize={18}
              minSize={12}
              maxSize={35}
              collapsible
            >
              <Sidebar
                variables={notebook.variables}
                graph={notebook.graph}
                cells={notebook.cells}
                metadata={notebook.metadata}
                connected={notebook.connected}
                onInsertRecipe={notebook.insertRecipe}
                onOpenNotebook={notebook.loadNotebookState}
                onScrollToCell={scrollToCell}
                saveStatus={notebook.saveStatus}
              />
            </Panel>
            <PanelResizeHandle className="resize-handle-h" />
          </>
        )}

        {/* Cell Editor Area */}
        <Panel id="editor" order={2} minSize={30}>
          <CellList
            cells={notebook.cells}
            graph={notebook.graph}
            executing={notebook.executing}
            focusedCellId={focusedCellId}
            onFocusCell={setFocusedCellId}
            onUpdateCell={notebook.updateCell}
            onExecuteCell={notebook.executeCell}
            onDeleteCell={notebook.deleteCell}
            onAddCell={notebook.addCell}
            onInsertSnippet={(source, name, index) => notebook.insertCellWithSource(source, name, 'code', index ?? null)}
            theme={theme}
          />
        </Panel>

        {/* Right Panel */}
        {rightPanel && (
          <>
            <PanelResizeHandle className="resize-handle-h" />
            <Panel
              id="right-panel"
              order={3}
              defaultSize={rightPanel === 'dag' ? 35 : 28}
              minSize={20}
              maxSize={55}
              collapsible
            >
              {rightPanel === 'ai' && (
                <AIPanel onClose={() => setRightPanel(null)} />
              )}
              {rightPanel === 'flowyml' && (
                <FlowyMLPanel
                  onClose={() => setRightPanel(null)}
                  connected={notebook.connected}
                  onAction={handleAction}
                />
              )}
              {rightPanel === 'dag' && (
                <PipelineDAG
                  cells={notebook.cells}
                  graph={notebook.graph}
                  executing={notebook.executing}
                  onClose={() => setRightPanel(null)}
                  onCellClick={scrollToCell}
                />
              )}
              {rightPanel === 'comments' && (
                <CommentsPanel
                  comments={notebook.comments}
                  cells={notebook.cells}
                  onAddComment={notebook.addComment}
                  onResolveComment={notebook.resolveComment}
                  onDeleteComment={notebook.deleteComment}
                  onReplyComment={notebook.replyToComment}
                  onClose={() => setRightPanel(null)}
                />
              )}
              {rightPanel === 'report' && (
                <ReportGenerator
                  onClose={() => setRightPanel(null)}
                  metadata={notebook.metadata}
                />
              )}
              {rightPanel === 'app' && (
                <AppPublisher
                  onClose={() => setRightPanel(null)}
                  cells={notebook.cells}
                  metadata={notebook.metadata}
                />
              )}
              {rightPanel === 'patterns' && (
                <AnalysisPatternsPanel
                  cells={notebook.cells}
                  onInsertCells={async (patternCells) => {
                    for (const cell of patternCells) {
                      await notebook.insertCellWithSource(cell.source, cell.name);
                    }
                  }}
                />
              )}
            </Panel>
          </>
        )}
      </PanelGroup>

      {/* Status Bar */}
      <StatusBar
        sessionId={notebook.sessionId}
        connected={notebook.connected}
        cellCount={notebook.cells.length}
        executing={notebook.executing}
        variables={notebook.variables}
        saveStatus={notebook.saveStatus}
        lastSaved={notebook.lastSaved}
        dirty={notebook.dirty}
      />

      {/* Command Palette */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onCommand={handleCommand}
      />

      {/* Pipeline Builder Wizard */}
      {wizardOpen && (
        <PipelineWizard
          onClose={() => setWizardOpen(false)}
          onGenerateCells={async (cells) => {
            for (const cell of cells) {
              await notebook.insertCellWithSource(cell.source, cell.name);
            }
          }}
        />
      )}
    </div>
  );
}
