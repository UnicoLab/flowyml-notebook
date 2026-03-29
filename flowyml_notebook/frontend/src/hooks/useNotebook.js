/**
 * useNotebook hook — central state management for the notebook.
 * Manages cells, execution state, WebSocket kernel, reactive graph,
 * and auto-save functionality.
 */
import { useState, useCallback, useRef, useEffect, useMemo } from 'react';

const API = '/api';
const AUTO_SAVE_INTERVAL = 30000; // 30 seconds

export function useNotebook() {
  const [cells, setCells] = useState([]);
  const [graph, setGraph] = useState({ cells: {}, var_producers: {} });
  const [variables, setVariables] = useState({});
  const [metadata, setMetadata] = useState({ name: 'untitled', version: 1 });
  const [sessionId, setSessionId] = useState(null);
  const [connected, setConnected] = useState(false);
  const [executing, setExecuting] = useState(null); // cell_id being executed
  const [kernelStatus, setKernelStatus] = useState('idle'); // 'idle' | 'starting' | 'ready' | 'error'
  const [kernelInfo, setKernelInfo] = useState(null); // { kernel_name, available_kernels, ... }
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error'
  const [lastSaved, setLastSaved] = useState(null);
  const wsRef = useRef(null);
  const autoSaveTimerRef = useRef(null);
  const dirtyRef = useRef(false);

  // Load initial state
  useEffect(() => {
    fetch(`${API}/state`)
      .then(r => r.ok ? r.json() : null)
      .then(state => {
        if (state) {
          setCells(state.notebook?.cells || []);
          setGraph(state.graph || { cells: {}, var_producers: {} });
          setVariables(state.variables || {});
          setMetadata(state.notebook?.metadata || { name: 'untitled' });
          setSessionId(state.session_id);
          setConnected(state.connected);
        }
      })
      .catch(() => {});

    // Fetch kernel status
    fetch(`${API}/kernel/status`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          setKernelInfo(data);
          if (data.status === 'ready') setKernelStatus('ready');
        }
      })
      .catch(() => {});
  }, []);

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/kernel`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleKernelMessage(msg);
    };

    ws.onclose = () => {
      setTimeout(() => {
        // Reconnect logic would go here
      }, 3000);
    };

    return () => ws.close();
  }, []);

  // Auto-save timer
  useEffect(() => {
    autoSaveTimerRef.current = setInterval(() => {
      if (dirtyRef.current) {
        performAutoSave();
      }
    }, AUTO_SAVE_INTERVAL);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, []);

  // Keep dirtyRef in sync
  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);

  const markDirty = useCallback(() => {
    setDirty(true);
    setSaveStatus('idle');
  }, []);

  const performAutoSave = useCallback(async () => {
    setSaveStatus('saving');
    try {
      const res = await fetch(`${API}/auto-save`, { method: 'POST' });
      const data = await res.json();
      if (data.saved) {
        setDirty(false);
        setSaveStatus('saved');
        setLastSaved(new Date().toISOString());
        // Reset to idle after 3 seconds
        setTimeout(() => setSaveStatus(prev => prev === 'saved' ? 'idle' : prev), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch {
      setSaveStatus('error');
    }
  }, []);

  const handleKernelMessage = useCallback((msg) => {
    const { type, data } = msg;

    switch (type) {
      case 'cell_complete':
        setCells(prev => prev.map(c =>
          c.id === data.cell_id
            ? { ...c, outputs: data.outputs, execution_count: (c.execution_count || 0) + 1 }
            : c
        ));
        setExecuting(null);
        markDirty();
        break;

      case 'cell_state':
        setGraph(prev => ({
          ...prev,
          cells: {
            ...prev.cells,
            [data.cell_id]: {
              ...prev.cells?.[data.cell_id],
              state: data.state,
            },
          },
        }));
        break;

      case 'graph_update':
        setGraph(data);
        break;

      case 'variables_update':
        setVariables(data);
        break;

      case 'state_update':
        setCells(data.notebook?.cells || []);
        setGraph(data.graph || { cells: {}, var_producers: {} });
        setVariables(data.variables || {});
        break;
    }
  }, [markDirty]);

  // --- Actions ---

  const addCell = useCallback(async (cellType = 'code', index = null) => {
    const res = await fetch(`${API}/cells`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cell_type: cellType, source: '', index }),
    });
    const cell = await res.json();
    setCells(prev => {
      if (index !== null) {
        const next = [...prev];
        next.splice(index, 0, cell);
        return next;
      }
      return [...prev, cell];
    });
    markDirty();
    return cell;
  }, [markDirty]);

  const updateCell = useCallback(async (cellId, source) => {
    setCells(prev => prev.map(c => c.id === cellId ? { ...c, source } : c));
    markDirty();

    const res = await fetch(`${API}/cells/${cellId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    });
    const data = await res.json();
    if (data.graph) setGraph(data.graph);
  }, [markDirty]);

  const deleteCell = useCallback(async (cellId) => {
    setCells(prev => prev.filter(c => c.id !== cellId));
    markDirty();
    await fetch(`${API}/cells/${cellId}`, { method: 'DELETE' });
  }, [markDirty]);

  const executeCell = useCallback(async (cellId) => {
    setExecuting(cellId);
    // Track kernel startup for the very first execution
    if (kernelStatus === 'idle') {
      setKernelStatus('starting');
    }
    setGraph(prev => ({
      ...prev,
      cells: {
        ...prev.cells,
        [cellId]: { ...prev.cells?.[cellId], state: 'running' },
      },
    }));

    try {
      const res = await fetch(`${API}/cells/${cellId}/execute`, { method: 'POST' });

      // Kernel is now ready after first successful execution
      if (kernelStatus !== 'ready') {
        setKernelStatus('ready');
      }

      if (!res.ok) {
        const errorText = await res.text().catch(() => `HTTP ${res.status}`);
        setCells(prev => prev.map(c =>
          c.id === cellId
            ? { ...c, outputs: [{ output_type: 'error', data: `Execution failed: ${errorText}` }] }
            : c
        ));
        setGraph(prev => ({
          ...prev,
          cells: { ...prev.cells, [cellId]: { ...prev.cells?.[cellId], state: 'error' } },
        }));
        setExecuting(null);
        return;
      }

      const data = await res.json();

      if (data.results) {
        for (const result of data.results) {
          setCells(prev => prev.map(c =>
            c.id === result.cell_id
              ? {
                  ...c,
                  outputs: result.outputs || [],
                  execution_count: (c.execution_count || 0) + 1,
                  last_executed: new Date().toISOString(),
                  duration_seconds: result.duration_seconds || 0,
                  memory_delta_mb: result.memory_delta_mb || 0,
                  cpu_time_s: result.cpu_time_s || 0,
                  peak_memory_mb: result.peak_memory_mb || 0,
                }
              : c
          ));
          setGraph(prev => ({
            ...prev,
            cells: {
              ...prev.cells,
              [result.cell_id]: {
                ...prev.cells?.[result.cell_id],
                state: result.success ? 'success' : 'error',
              },
            },
          }));
        }
      }
      // Server graph is authoritative — it has correct states after reactive cascade
      if (data.graph) setGraph(data.graph);
      if (data.variables) setVariables(data.variables);
      markDirty();
    } catch (err) {
      console.error('Execute cell error:', err);
      if (kernelStatus === 'starting') setKernelStatus('error');
      setCells(prev => prev.map(c =>
        c.id === cellId
          ? { ...c, outputs: [{ output_type: 'error', data: `Network error: ${err.message}` }] }
          : c
      ));
      setGraph(prev => ({
        ...prev,
        cells: { ...prev.cells, [cellId]: { ...prev.cells?.[cellId], state: 'error' } },
      }));
    }
    setExecuting(null);
  }, [markDirty, kernelStatus]);

  const executeAll = useCallback(async () => {
    setExecuting('all');
    try {
      const res = await fetch(`${API}/execute-all`, { method: 'POST' });

      if (!res.ok) {
        console.error('Execute all failed:', res.status);
        setExecuting(null);
        return;
      }

      const data = await res.json();

      if (data.results) {
        for (const result of data.results) {
          setCells(prev => prev.map(c =>
            c.id === result.cell_id
              ? {
                  ...c,
                  outputs: result.outputs || [],
                  execution_count: (c.execution_count || 0) + 1,
                  last_executed: new Date().toISOString(),
                }
              : c
          ));
        }
      }
      if (data.graph) setGraph(data.graph);
      if (data.variables) setVariables(data.variables);
      markDirty();
    } catch (err) {
      console.error('Execute all error:', err);
    }
    setExecuting(null);
  }, [markDirty]);

  const resetKernel = useCallback(async () => {
    await fetch(`${API}/kernel/reset`, { method: 'POST' });
    setVariables({});
    setGraph({ cells: {}, var_producers: {} });
    setCells(prev => prev.map(c => ({ ...c, outputs: [], execution_count: 0 })));
    setKernelStatus('idle');
  }, []);

  // --- Clear outputs ---

  const clearCellOutput = useCallback(async (cellId) => {
    setCells(prev => prev.map(c =>
      c.id === cellId ? { ...c, outputs: [], execution_count: 0 } : c
    ));
    markDirty();
    try {
      await fetch(`${API}/cells/${cellId}/clear-output`, { method: 'POST' });
    } catch (e) { console.error('Clear output failed:', e); }
  }, [markDirty]);

  const clearAllOutputs = useCallback(async () => {
    setCells(prev => prev.map(c => ({ ...c, outputs: [], execution_count: 0 })));
    markDirty();
    try {
      await fetch(`${API}/clear-all-outputs`, { method: 'POST' });
    } catch (e) { console.error('Clear all outputs failed:', e); }
  }, [markDirty]);

  // --- Reactive: stale cell tracking ---
  const staleCellIds = useMemo(() => {
    if (!graph?.cells) return [];
    return Object.entries(graph.cells)
      .filter(([, info]) => info.state === 'stale')
      .map(([id]) => id);
  }, [graph]);

  const runStaleCells = useCallback(async () => {
    if (staleCellIds.length === 0) return;
    // Execute stale cells in sequence (each will cascade reactively)
    for (const cellId of staleCellIds) {
      // Re-check state since previous execution may have resolved staleness
      const currentState = graph?.cells?.[cellId]?.state;
      if (currentState !== 'stale') continue;
      await executeCell(cellId);
    }
  }, [staleCellIds, graph, executeCell]);

  const saveNotebook = useCallback(async (path) => {
    setSaveStatus('saving');
    try {
      const res = await fetch(`${API}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      const data = await res.json();
      setDirty(false);
      setSaveStatus('saved');
      setLastSaved(new Date().toISOString());
      setTimeout(() => setSaveStatus(prev => prev === 'saved' ? 'idle' : prev), 3000);
      return data;
    } catch {
      setSaveStatus('error');
    }
  }, []);

  const uploadCSV = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API}/upload-csv`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.error) {
        console.error('CSV upload error:', data.error);
        return data;
      }

      // Refresh state to pick up new cell
      const stateRes = await fetch(`${API}/state`);
      const state = await stateRes.json();
      if (state.cells) setCells(state.cells);
      if (state.graph) setGraph(state.graph);
      if (state.variables) setVariables(state.variables);
      markDirty();

      return data;
    } catch (err) {
      console.error('CSV upload error:', err);
      return { error: err.message };
    }
  }, [markDirty]);

  // Insert a recipe as a new cell
  const insertRecipe = useCallback(async (recipe) => {
    const res = await fetch(`${API}/cells`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cell_type: recipe.cell_type || 'code',
        source: recipe.source || '',
        name: recipe.name || '',
      }),
    });
    const cell = await res.json();
    setCells(prev => [...prev, cell]);
    markDirty();
    return cell;
  }, [markDirty]);

  // Insert a cell with pre-filled source code at a specific position
  const insertCellWithSource = useCallback(async (source, name = '', cellType = 'code', index = null) => {
    const res = await fetch(`${API}/cells`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cell_type: cellType, source, name, index }),
    });
    const cell = await res.json();
    setCells(prev => {
      if (index !== null) {
        const next = [...prev];
        next.splice(index, 0, cell);
        return next;
      }
      return [...prev, cell];
    });
    markDirty();
    return cell;
  }, [markDirty]);

  // Load a full notebook state (from open-notebook API response)
  const loadNotebookState = useCallback((state) => {
    if (!state) return;
    setCells(state.notebook?.cells || state.cells || []);
    setGraph(state.graph || { cells: {}, var_producers: {} });
    setVariables(state.variables || {});
    setMetadata(state.notebook?.metadata || state.metadata || { name: 'untitled' });
    if (state.session_id) setSessionId(state.session_id);
    if (state.connected !== undefined) setConnected(state.connected);
    setDirty(false);
    setSaveStatus('idle');
  }, []);

  // Rename current notebook
  const renameNotebook = useCallback(async (newName) => {
    if (!newName?.trim()) return;
    try {
      const res = await fetch(`${API}/metadata?name=${encodeURIComponent(newName.trim())}`, {
        method: 'PUT',
      });
      if (res.ok) {
        const data = await res.json();
        setMetadata(prev => ({ ...prev, name: data.name || newName.trim() }));
        markDirty();
      }
    } catch (e) {
      console.error('Rename failed:', e);
    }
  }, [markDirty]);

  // Load demo notebook
  const loadDemo = useCallback(async () => {
    try {
      const res = await fetch(`${API}/demo/load`);
      if (res.ok) {
        const state = await res.json();
        loadNotebookState(state);
      }
    } catch (e) {
      console.error('Load demo failed:', e);
    }
  }, [loadNotebookState]);

  // --- Collaboration: Comments ---
  const [comments, setComments] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [userProfile, setUserProfile] = useState(null);

  // Fetch comments on mount
  useEffect(() => {
    fetch(`${API}/comments`).then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.comments) setComments(data.comments); })
      .catch(() => {});
    fetch(`${API}/reviews`).then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.reviews) setReviews(data.reviews); })
      .catch(() => {});
    fetch(`${API}/user/profile`).then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUserProfile(data); })
      .catch(() => {});
  }, []);

  const fetchComments = useCallback(async () => {
    try {
      const res = await fetch(`${API}/comments`);
      if (res.ok) { const data = await res.json(); setComments(data.comments || []); }
    } catch { /* ignore */ }
  }, []);

  const addComment = useCallback(async (comment) => {
    try {
      const res = await fetch(`${API}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(comment),
      });
      if (res.ok) {
        const newComment = await res.json();
        setComments(prev => [...prev, newComment]);
      }
    } catch (e) { console.error('Add comment failed:', e); }
  }, []);

  const resolveComment = useCallback(async (commentId) => {
    try {
      const res = await fetch(`${API}/comments/${commentId}/resolve`, { method: 'PUT' });
      if (res.ok) {
        const updated = await res.json();
        setComments(prev => prev.map(c => c.id === commentId ? updated : c));
      }
    } catch (e) { console.error('Resolve comment failed:', e); }
  }, []);

  const deleteComment = useCallback(async (commentId) => {
    try {
      await fetch(`${API}/comments/${commentId}`, { method: 'DELETE' });
      setComments(prev => prev.filter(c => c.id !== commentId));
    } catch (e) { console.error('Delete comment failed:', e); }
  }, []);

  const replyToComment = useCallback(async (commentId, text) => {
    try {
      const res = await fetch(`${API}/comments/${commentId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const updated = await res.json();
        setComments(prev => prev.map(c => c.id === commentId ? updated : c));
      }
    } catch (e) { console.error('Reply failed:', e); }
  }, []);

  // --- Collaboration: Reviews ---
  const requestReview = useCallback(async (reviewData = {}) => {
    try {
      const res = await fetch(`${API}/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reviewData),
      });
      if (res.ok) {
        const newReview = await res.json();
        setReviews(prev => [...prev, newReview]);
      }
    } catch (e) { console.error('Request review failed:', e); }
  }, []);

  const updateReview = useCallback(async (reviewId, update) => {
    try {
      const res = await fetch(`${API}/reviews/${reviewId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update),
      });
      if (res.ok) {
        const updated = await res.json();
        setReviews(prev => prev.map(r => r.id === reviewId ? updated : r));
      }
    } catch (e) { console.error('Update review failed:', e); }
  }, []);

  // --- Save As / Open File ---

  const [currentFilePath, setCurrentFilePath] = useState(null);
  const [recentFiles, setRecentFiles] = useState([]);

  // Fetch recent files on mount
  useEffect(() => {
    fetch(`${API}/recent-files`)
      .then(r => r.ok ? r.json() : [])
      .then(files => setRecentFiles(files))
      .catch(() => {});
  }, []);

  const saveAs = useCallback(async ({ path, name, format }) => {
    setSaveStatus('saving');
    try {
      const res = await fetch(`${API}/save-as`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, name, format }),
      });
      const data = await res.json();
      setCurrentFilePath(data.paths?.[0] || null);
      setMetadata(prev => ({ ...prev, name: data.name || prev.name }));
      setDirty(false);
      setSaveStatus('saved');
      setLastSaved(new Date().toISOString());
      setTimeout(() => setSaveStatus(prev => prev === 'saved' ? 'idle' : prev), 3000);
      // Refresh recent files
      fetch(`${API}/recent-files`).then(r => r.ok ? r.json() : []).then(setRecentFiles);
      return data;
    } catch {
      setSaveStatus('error');
    }
  }, []);

  const openFile = useCallback(async (filePath) => {
    try {
      const res = await fetch(`${API}/load-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath }),
      });
      if (!res.ok) throw new Error('Failed to load');
      const state = await res.json();
      setCells(state.notebook?.cells || state.cells || []);
      setGraph(state.graph || { cells: {}, var_producers: {} });
      setVariables(state.variables || {});
      setMetadata(state.notebook?.metadata || state.metadata || { name: 'untitled' });
      setCurrentFilePath(filePath);
      setDirty(false);
      setSaveStatus('idle');
      // Refresh recent files
      fetch(`${API}/recent-files`).then(r => r.ok ? r.json() : []).then(setRecentFiles);
      return state;
    } catch (e) {
      console.error('Open file failed:', e);
    }
  }, []);

  // --- Kernel switch/refresh ---

  const switchKernel = useCallback(async (pythonPath) => {
    setKernelStatus('starting');
    try {
      const res = await fetch(`${API}/kernel/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ python_path: pythonPath }),
      });
      const data = await res.json();
      if (res.ok) {
        setKernelStatus('ready');
        setVariables({});
        setCells(prev => prev.map(c => ({ ...c, outputs: [], execution_count: 0 })));
        // Refresh kernel info
        const infoRes = await fetch(`${API}/kernel/status`);
        if (infoRes.ok) setKernelInfo(await infoRes.json());
        return data;
      } else {
        setKernelStatus('error');
      }
    } catch (e) {
      console.error('Kernel switch failed:', e);
      setKernelStatus('error');
    }
  }, []);

  const refreshKernels = useCallback(async () => {
    try {
      const res = await fetch(`${API}/kernel/refresh`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setKernelInfo(prev => ({
          ...prev,
          available_kernels: data.available_kernels,
        }));
        return data.available_kernels;
      }
    } catch (e) { console.error('Refresh kernels failed:', e); }
  }, []);

  // --- Undo/Redo ---

  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const MAX_UNDO = 50;

  const pushUndo = useCallback((action) => {
    setUndoStack(prev => [...prev.slice(-(MAX_UNDO - 1)), action]);
    setRedoStack([]); // Clear redo on new action
  }, []);

  const undo = useCallback(() => {
    setUndoStack(prev => {
      if (prev.length === 0) return prev;
      const action = prev[prev.length - 1];
      const newStack = prev.slice(0, -1);

      // Reverse the action
      if (action.type === 'delete_cell') {
        setCells(c => {
          const next = [...c];
          next.splice(action.index, 0, action.cell);
          return next;
        });
      } else if (action.type === 'add_cell') {
        setCells(c => c.filter(cell => cell.id !== action.cellId));
      } else if (action.type === 'clear_output') {
        setCells(c => c.map(cell =>
          cell.id === action.cellId ? { ...cell, outputs: action.outputs } : cell
        ));
      } else if (action.type === 'clear_all_outputs') {
        setCells(action.previousCells);
      }

      setRedoStack(r => [...r, action]);
      markDirty();
      return newStack;
    });
  }, [markDirty]);

  const redo = useCallback(() => {
    setRedoStack(prev => {
      if (prev.length === 0) return prev;
      const action = prev[prev.length - 1];
      const newStack = prev.slice(0, -1);

      // Re-apply the action
      if (action.type === 'delete_cell') {
        setCells(c => c.filter(cell => cell.id !== action.cell.id));
      } else if (action.type === 'add_cell') {
        // Re-add is complex, just mark dirty
      } else if (action.type === 'clear_output') {
        setCells(c => c.map(cell =>
          cell.id === action.cellId ? { ...cell, outputs: [], execution_count: 0 } : cell
        ));
      } else if (action.type === 'clear_all_outputs') {
        setCells(c => c.map(cell => ({ ...cell, outputs: [], execution_count: 0 })));
      }

      setUndoStack(u => [...u, action]);
      markDirty();
      return newStack;
    });
  }, [markDirty]);

  // --- Smart Import Suggestions ---

  const suggestImports = useCallback(async (source, errorText = '') => {
    try {
      const res = await fetch(`${API}/suggest-imports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, error: errorText }),
      });
      if (res.ok) return (await res.json()).suggestions || [];
    } catch (e) { console.error('Suggest imports failed:', e); }
    return [];
  }, []);

  return {
    cells, setCells, graph, variables, metadata,
    sessionId, connected, executing,
    dirty, saveStatus, lastSaved,
    kernelStatus, kernelInfo,
    addCell, updateCell, deleteCell,
    executeCell, executeAll, resetKernel, saveNotebook, uploadCSV,
    clearCellOutput, clearAllOutputs,
    insertRecipe, insertCellWithSource, loadNotebookState, renameNotebook, loadDemo,
    // Reactive DAG
    staleCellIds, runStaleCells,
    // Save As / Open
    saveAs, openFile, currentFilePath, recentFiles,
    // Kernel management
    switchKernel, refreshKernels,
    // Undo/Redo
    undo, redo, pushUndo, undoStack, redoStack,
    // Smart imports
    suggestImports,
    // Collaboration
    comments, addComment, resolveComment, deleteComment, replyToComment,
    reviews, requestReview, updateReview,
    userProfile,
  };
}

