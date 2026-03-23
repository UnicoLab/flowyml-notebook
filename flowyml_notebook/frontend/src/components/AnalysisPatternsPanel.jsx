import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen, Plus, Search, Tag, Play, Trash2, X,
  ChevronDown, CheckCircle, Loader2, Clock, Users,
  Bookmark, Filter, Star, Copy, ArrowRight
} from 'lucide-react';

const PROBLEM_TYPES = ['any', 'classification', 'regression', 'clustering', 'eda', 'preprocessing'];
const DATA_TYPES = ['any', 'tabular', 'time_series', 'text', 'image'];

export default function AnalysisPatternsPanel({ cells = [], onInsertCells }) {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterProblem, setFilterProblem] = useState('any');
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  // Create form state
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newTags, setNewTags] = useState('');
  const [newProblem, setNewProblem] = useState('any');
  const [newDataType, setNewDataType] = useState('any');
  const [selectedCells, setSelectedCells] = useState(new Set());
  const [saving, setSaving] = useState(false);

  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/patterns');
      if (res.ok) {
        const data = await res.json();
        setPatterns(data.patterns || []);
      }
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchPatterns(); }, [fetchPatterns]);

  const handleSearch = useCallback(async () => {
    if (!searchQuery && filterProblem === 'any') {
      fetchPatterns();
      return;
    }
    try {
      const res = await fetch('/api/patterns/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, problem_type: filterProblem }),
      });
      if (res.ok) {
        const data = await res.json();
        setPatterns(data.patterns || []);
      }
    } catch (e) { /* ignore */ }
  }, [searchQuery, filterProblem, fetchPatterns]);

  useEffect(() => {
    const timeout = setTimeout(handleSearch, 300);
    return () => clearTimeout(timeout);
  }, [searchQuery, filterProblem]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setSaving(true);
    try {
      const patternCells = cells
        .filter((_, i) => selectedCells.has(i))
        .map(c => ({ source: c.source, cell_type: c.cell_type, name: c.name }));

      const res = await fetch('/api/patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName.trim(),
          description: newDesc.trim(),
          tags: newTags.split(',').map(t => t.trim()).filter(Boolean),
          cells: patternCells,
          problem_type: newProblem,
          data_type: newDataType,
        }),
      });
      if (res.ok) {
        setShowCreate(false);
        setNewName(''); setNewDesc(''); setNewTags('');
        setSelectedCells(new Set());
        fetchPatterns();
      }
    } catch (e) { /* ignore */ }
    setSaving(false);
  }, [newName, newDesc, newTags, newProblem, newDataType, selectedCells, cells, fetchPatterns]);

  const handleApply = useCallback(async (patternId) => {
    try {
      const res = await fetch(`/api/patterns/${patternId}/apply`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        // Dispatch event to insert cells
        if (data.cells && data.cells.length > 0) {
          data.cells.forEach(cell => {
            window.dispatchEvent(new CustomEvent('flowyml:insert-cell', {
              detail: { code: cell.source, below: true },
            }));
          });
        }
        fetchPatterns(); // Update usage count
      }
    } catch (e) { /* ignore */ }
  }, [fetchPatterns]);

  const handleDelete = useCallback(async (patternId) => {
    try {
      await fetch(`/api/patterns/${patternId}`, { method: 'DELETE' });
      fetchPatterns();
    } catch (e) { /* ignore */ }
  }, [fetchPatterns]);

  const toggleCellSelection = (index) => {
    setSelectedCells(prev => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });
  };

  const problemColors = {
    classification: '#10b981', regression: '#6366f1', clustering: '#f59e0b',
    eda: '#8b5cf6', preprocessing: '#06b6d4', any: '#64748b',
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BookOpen size={16} style={{ color: '#8b5cf6' }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>Analysis Patterns</span>
          <span style={{
            padding: '1px 6px', borderRadius: 8, fontSize: 10, fontWeight: 600,
            background: 'rgba(139,92,246,0.15)', color: '#c4b5fd',
          }}>
            {patterns.length}
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
            borderRadius: 6, fontSize: 11, fontWeight: 600,
            background: showCreate ? 'rgba(239,68,68,0.15)' : 'rgba(139,92,246,0.15)',
            color: showCreate ? '#ef4444' : '#c4b5fd',
            border: `1px solid ${showCreate ? 'rgba(239,68,68,0.3)' : 'rgba(139,92,246,0.3)'}`,
            cursor: 'pointer',
          }}>
          {showCreate ? <><X size={11} /> Cancel</> : <><Plus size={11} /> New Pattern</>}
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* Create Form */}
        <AnimatePresence>
          {showCreate && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ overflow: 'hidden', marginBottom: 12 }}>
              <div style={{
                padding: 12, borderRadius: 10,
                background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.15)',
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#c4b5fd', marginBottom: 8 }}>
                  Create Analysis Pattern
                </div>
                <input
                  value={newName} onChange={e => setNewName(e.target.value)}
                  placeholder="Pattern name..."
                  style={{ ...inputStyle, marginBottom: 6 }}
                />
                <textarea
                  value={newDesc} onChange={e => setNewDesc(e.target.value)}
                  placeholder="Description (optional)..."
                  rows={2}
                  style={{ ...inputStyle, resize: 'vertical', marginBottom: 6 }}
                />
                <input
                  value={newTags} onChange={e => setNewTags(e.target.value)}
                  placeholder="Tags (comma-separated)..."
                  style={{ ...inputStyle, marginBottom: 8 }}
                />
                <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                  <select value={newProblem} onChange={e => setNewProblem(e.target.value)}
                    style={{ ...selectStyle, flex: 1 }}>
                    {PROBLEM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <select value={newDataType} onChange={e => setNewDataType(e.target.value)}
                    style={{ ...selectStyle, flex: 1 }}>
                    {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>

                {/* Cell Selection */}
                <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 4 }}>
                  Select cells to include ({selectedCells.size} selected):
                </div>
                <div style={{
                  maxHeight: 120, overflow: 'auto', borderRadius: 6,
                  border: '1px solid var(--border)', marginBottom: 8,
                }}>
                  {cells.map((cell, i) => (
                    <button
                      key={i}
                      onClick={() => toggleCellSelection(i)}
                      style={{
                        width: '100%', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: 6,
                        background: selectedCells.has(i) ? 'rgba(139,92,246,0.1)' : 'none',
                        border: 'none', borderBottom: '1px solid var(--border)',
                        color: selectedCells.has(i) ? '#c4b5fd' : 'var(--fg-muted)',
                        cursor: 'pointer', fontSize: 10, textAlign: 'left',
                      }}>
                      <input type="checkbox" checked={selectedCells.has(i)} readOnly
                        style={{ accentColor: '#8b5cf6' }} />
                      <span>{cell.name || `Cell ${i + 1}`}</span>
                      <span style={{
                        marginLeft: 'auto', padding: '0 4px', borderRadius: 3, fontSize: 8,
                        background: 'rgba(255,255,255,0.05)', fontWeight: 600,
                      }}>{cell.cell_type}</span>
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleCreate}
                  disabled={saving || !newName.trim() || selectedCells.size === 0}
                  style={{
                    width: '100%', padding: '8px', borderRadius: 6, border: 'none',
                    background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                    color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    opacity: saving || !newName.trim() || selectedCells.size === 0 ? 0.5 : 1,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}>
                  {saving ? <Loader2 size={12} className="animate-spin" /> : <Bookmark size={12} />}
                  {saving ? 'Saving...' : 'Save Pattern'}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search & Filters */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={11} style={{
              position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--fg-dim)',
            }} />
            <input
              value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search patterns..."
              style={{ ...inputStyle, paddingLeft: 26 }}
            />
          </div>
          <select value={filterProblem} onChange={e => setFilterProblem(e.target.value)}
            style={{ ...selectStyle, width: 100 }}>
            <option value="any">All types</option>
            {PROBLEM_TYPES.filter(t => t !== 'any').map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* Pattern List */}
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 30, gap: 8 }}>
            <Loader2 size={14} className="animate-spin" style={{ color: '#8b5cf6' }} />
            <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Loading patterns...</span>
          </div>
        ) : patterns.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 30 }}>
            <BookOpen size={24} style={{ color: 'var(--fg-dim)', margin: '0 auto 8px' }} />
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)' }}>No patterns yet</div>
            <div style={{ fontSize: 10, color: 'var(--fg-dim)', marginTop: 4 }}>
              Create reusable analysis patterns from your notebook cells
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {patterns.map(p => {
              const isExpanded = expandedId === p.id;
              const pColor = problemColors[p.problem_type] || problemColors.any;
              return (
                <motion.div key={p.id}
                  layout
                  style={{
                    borderRadius: 8, overflow: 'hidden',
                    background: 'var(--bg-primary)', border: '1px solid var(--border)',
                  }}>
                  {/* Card Header */}
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : p.id)}
                    style={{
                      padding: '8px 10px', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                    <Bookmark size={12} style={{ color: pColor, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {p.name}
                      </div>
                      <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
                        <span style={{
                          fontSize: 8, padding: '1px 5px', borderRadius: 6,
                          background: `${pColor}15`, color: pColor, fontWeight: 600,
                        }}>
                          {p.problem_type}
                        </span>
                        <span style={{ fontSize: 8, color: 'var(--fg-dim)' }}>
                          {p.cells?.length || 0} cells · {p.uses || 0} uses
                        </span>
                      </div>
                    </div>
                    <ChevronDown size={12} style={{
                      color: 'var(--fg-dim)', transform: isExpanded ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s',
                    }} />
                  </div>

                  {/* Expanded */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        style={{ overflow: 'hidden' }}>
                        <div style={{ padding: '0 10px 10px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {p.description && (
                            <div style={{ fontSize: 10, color: 'var(--fg-muted)', lineHeight: 1.4 }}>
                              {p.description}
                            </div>
                          )}
                          {p.tags && p.tags.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                              {p.tags.map(t => (
                                <span key={t} style={{
                                  padding: '1px 6px', borderRadius: 8, fontSize: 8, fontWeight: 600,
                                  background: 'rgba(139,92,246,0.1)', color: '#c4b5fd',
                                }}>{t}</span>
                              ))}
                            </div>
                          )}
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button
                              onClick={() => handleApply(p.id)}
                              style={{
                                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                                padding: '6px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                                background: 'rgba(99,102,241,0.12)', color: '#6366f1',
                                border: '1px solid rgba(99,102,241,0.25)', cursor: 'pointer',
                              }}>
                              <Play size={10} /> Apply
                            </button>
                            <button
                              onClick={() => handleDelete(p.id)}
                              style={{
                                padding: '6px 10px', borderRadius: 6, fontSize: 10,
                                background: 'rgba(239,68,68,0.08)', color: '#ef4444',
                                border: '1px solid rgba(239,68,68,0.2)', cursor: 'pointer',
                              }}>
                              <Trash2 size={10} />
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const inputStyle = {
  width: '100%', padding: '6px 10px', borderRadius: 6,
  background: 'var(--bg-primary)', border: '1px solid var(--border)',
  color: 'var(--fg-primary)', fontSize: 11,
};

const selectStyle = {
  padding: '4px 6px', borderRadius: 6, fontSize: 10,
  background: 'var(--bg-primary)', border: '1px solid var(--border)',
  color: 'var(--fg-primary)',
};
