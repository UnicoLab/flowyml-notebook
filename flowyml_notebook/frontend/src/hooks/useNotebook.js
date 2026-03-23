/**
 * useNotebook hook — central state management for the notebook.
 * Manages cells, execution state, WebSocket kernel, reactive graph,
 * and auto-save functionality.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

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
    setGraph(prev => ({
      ...prev,
      cells: {
        ...prev.cells,
        [cellId]: { ...prev.cells?.[cellId], state: 'running' },
      },
    }));

    try {
      const res = await fetch(`${API}/cells/${cellId}/execute`, { method: 'POST' });

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
      if (data.graph) setGraph(prev => ({ ...data.graph, cells: { ...data.graph.cells, ...prev.cells } }));
      if (data.variables) setVariables(data.variables);
      markDirty();
    } catch (err) {
      console.error('Execute cell error:', err);
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
  }, [markDirty]);

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
  }, []);

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

  return {
    cells, setCells, graph, variables, metadata,
    sessionId, connected, executing,
    dirty, saveStatus, lastSaved,
    addCell, updateCell, deleteCell,
    executeCell, executeAll, resetKernel, saveNotebook, uploadCSV,
    insertRecipe, insertCellWithSource, loadNotebookState, renameNotebook, loadDemo,
    // Collaboration
    comments, addComment, resolveComment, deleteComment, replyToComment,
    reviews, requestReview, updateReview,
    userProfile,
  };
}
