import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  MessageSquare, Send, Check, X, Reply, ChevronDown, ChevronRight,
  User, Clock, CheckCircle2, AlertCircle, MessageCircle
} from 'lucide-react';

/**
 * CommentsPanel — cell-level and notebook-level comments with reply threads.
 * Data is persisted to the backend (comments.json alongside notebook data).
 */
export default function CommentsPanel({ comments = [], onAddComment, onResolveComment, onDeleteComment, onReplyComment, cells = [], activeCellFilter = null, onClose }) {
  const [newComment, setNewComment] = useState('');
  const [selectedCell, setSelectedCell] = useState(activeCellFilter || '');
  const [expandedThreads, setExpandedThreads] = useState(new Set());
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [filter, setFilter] = useState('all'); // 'all' | 'open' | 'resolved'
  const inputRef = useRef(null);
  const replyRef = useRef(null);

  useEffect(() => {
    if (activeCellFilter) setSelectedCell(activeCellFilter);
  }, [activeCellFilter]);

  useEffect(() => {
    if (replyingTo && replyRef.current) replyRef.current.focus();
  }, [replyingTo]);

  const filteredComments = comments.filter(c => {
    if (filter === 'open' && c.resolved) return false;
    if (filter === 'resolved' && !c.resolved) return false;
    if (activeCellFilter && c.cell_id !== activeCellFilter) return false;
    return true;
  });

  const toggleThread = (id) => {
    setExpandedThreads(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleSubmit = () => {
    const text = newComment.trim();
    if (!text) return;
    onAddComment?.({
      cell_id: selectedCell || null,
      text,
    });
    setNewComment('');
  };

  const handleReply = (commentId) => {
    const text = replyText.trim();
    if (!text) return;
    onReplyComment?.(commentId, text);
    setReplyText('');
    setReplyingTo(null);
  };

  const getCellName = (cellId) => {
    if (!cellId) return 'Notebook';
    const cell = cells.find(c => c.id === cellId);
    return cell?.name || `Cell ${cellId.slice(0, 6)}`;
  };

  const formatTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return 'now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return d.toLocaleDateString();
  };

  const openCount = comments.filter(c => !c.resolved).length;
  const resolvedCount = comments.filter(c => c.resolved).length;

  return (
    <div className="comments-panel" style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <MessageSquare size={14} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>Comments</span>
        <span className="cell-metric-badge" style={{ fontSize: 10 }}>
          {openCount} open
        </span>
        {onClose && (
          <button className="btn-icon" onClick={onClose} style={{ width: 20, height: 20 }}>
            <X size={12} />
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div style={{
        display: 'flex', gap: 4, padding: '6px 12px',
        borderBottom: '1px solid var(--border)',
      }}>
        {['all', 'open', 'resolved'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '3px 10px', borderRadius: 12, fontSize: 10,
              fontWeight: filter === f ? 600 : 400,
              background: filter === f ? 'var(--accent-muted)' : 'transparent',
              color: filter === f ? 'var(--accent)' : 'var(--fg-secondary)',
              border: 'none', cursor: 'pointer', textTransform: 'capitalize',
            }}
          >
            {f} {f === 'open' ? `(${openCount})` : f === 'resolved' ? `(${resolvedCount})` : `(${comments.length})`}
          </button>
        ))}
      </div>

      {/* Comments list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
        {filteredComments.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: 24, color: 'var(--fg-tertiary)',
            fontSize: 11,
          }}>
            <MessageCircle size={24} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
            <div>No comments yet</div>
            <div style={{ fontSize: 10, marginTop: 4 }}>
              Add comments to cells for code review and collaboration
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {filteredComments.map(comment => (
              <div
                key={comment.id}
                style={{
                  background: 'var(--bg-tertiary)',
                  borderRadius: 8, padding: '8px 10px',
                  border: '1px solid var(--border)',
                  opacity: comment.resolved ? 0.6 : 1,
                }}
              >
                {/* Comment header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <div style={{
                    width: 18, height: 18, borderRadius: '50%',
                    background: `hsl(${(comment.author?.name || 'U').charCodeAt(0) * 37 % 360}, 60%, 45%)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 9, fontWeight: 700, color: '#fff',
                  }}>
                    {(comment.author?.name || 'U')[0].toUpperCase()}
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, flex: 1, color: 'var(--fg-primary)' }}>
                    {comment.author?.name || 'Unknown'}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--fg-tertiary)' }}>
                    {formatTime(comment.created_at)}
                  </span>
                </div>

                {/* Cell reference badge */}
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '1px 6px', borderRadius: 4, fontSize: 9,
                  background: 'var(--bg-primary)', color: 'var(--fg-secondary)',
                  marginBottom: 4,
                }}>
                  {comment.cell_id ? '📎' : '📓'} {getCellName(comment.cell_id)}
                </div>

                {/* Comment text */}
                <div style={{ fontSize: 11, lineHeight: 1.5, color: 'var(--fg-primary)', marginBottom: 6 }}>
                  {comment.text}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <button
                    className="btn-icon"
                    style={{ width: 'auto', height: 18, fontSize: 9, gap: 3, display: 'flex', alignItems: 'center', padding: '0 6px' }}
                    onClick={() => onResolveComment?.(comment.id)}
                  >
                    {comment.resolved ? <AlertCircle size={10} /> : <CheckCircle2 size={10} />}
                    {comment.resolved ? 'Reopen' : 'Resolve'}
                  </button>
                  <button
                    className="btn-icon"
                    style={{ width: 'auto', height: 18, fontSize: 9, gap: 3, display: 'flex', alignItems: 'center', padding: '0 6px' }}
                    onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
                  >
                    <Reply size={10} /> Reply
                  </button>
                  {(comment.replies?.length > 0) && (
                    <button
                      className="btn-icon"
                      style={{ width: 'auto', height: 18, fontSize: 9, gap: 3, display: 'flex', alignItems: 'center', padding: '0 6px' }}
                      onClick={() => toggleThread(comment.id)}
                    >
                      {expandedThreads.has(comment.id) ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                      {comment.replies.length} {comment.replies.length === 1 ? 'reply' : 'replies'}
                    </button>
                  )}
                  <div style={{ flex: 1 }} />
                  <button
                    className="btn-icon"
                    style={{ width: 18, height: 18, color: '#666' }}
                    onClick={() => onDeleteComment?.(comment.id)}
                  >
                    <X size={10} />
                  </button>
                </div>

                {/* Replies */}
                {expandedThreads.has(comment.id) && comment.replies?.map((reply, i) => (
                  <div
                    key={i}
                    style={{
                      marginTop: 6, marginLeft: 16, paddingLeft: 8,
                      borderLeft: '2px solid var(--border)', fontSize: 11,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                      <div style={{
                        width: 14, height: 14, borderRadius: '50%',
                        background: `hsl(${(reply.author?.name || 'U').charCodeAt(0) * 37 % 360}, 60%, 45%)`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 7, fontWeight: 700, color: '#fff',
                      }}>
                        {(reply.author?.name || 'U')[0].toUpperCase()}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: 10 }}>{reply.author?.name || 'Unknown'}</span>
                      <span style={{ fontSize: 9, color: 'var(--fg-tertiary)' }}>{formatTime(reply.created_at)}</span>
                    </div>
                    <div style={{ color: 'var(--fg-primary)' }}>{reply.text}</div>
                  </div>
                ))}

                {/* Reply input */}
                {replyingTo === comment.id && (
                  <div style={{ marginTop: 6, display: 'flex', gap: 4 }}>
                    <input
                      ref={replyRef}
                      style={{
                        flex: 1, padding: '4px 8px', borderRadius: 6,
                        border: '1px solid var(--border)', background: 'var(--bg-primary)',
                        color: 'var(--fg-primary)', fontSize: 11, outline: 'none',
                      }}
                      placeholder="Reply..."
                      value={replyText}
                      onChange={e => setReplyText(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleReply(comment.id);
                        if (e.key === 'Escape') setReplyingTo(null);
                      }}
                    />
                    <button
                      className="btn-icon"
                      style={{ width: 24, height: 24, color: 'var(--accent)' }}
                      onClick={() => handleReply(comment.id)}
                    >
                      <Send size={11} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New comment input */}
      <div style={{
        padding: '8px 10px', borderTop: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        {/* Cell selector */}
        <select
          value={selectedCell}
          onChange={e => setSelectedCell(e.target.value)}
          style={{
            padding: '4px 8px', borderRadius: 6,
            border: '1px solid var(--border)', background: 'var(--bg-primary)',
            color: 'var(--fg-primary)', fontSize: 10, outline: 'none',
          }}
        >
          <option value="">📓 Notebook-level</option>
          {cells.map(c => (
            <option key={c.id} value={c.id}>
              📎 {c.name || `Cell ${c.id.slice(0, 6)}`}
            </option>
          ))}
        </select>
        <div style={{ display: 'flex', gap: 4 }}>
          <input
            ref={inputRef}
            style={{
              flex: 1, padding: '6px 10px', borderRadius: 8,
              border: '1px solid var(--border)', background: 'var(--bg-primary)',
              color: 'var(--fg-primary)', fontSize: 11, outline: 'none',
            }}
            placeholder="Add a comment..."
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
            }}
          />
          <button
            className="btn-icon"
            style={{
              width: 30, height: 30, borderRadius: 8,
              background: newComment.trim() ? 'var(--accent)' : 'transparent',
              color: newComment.trim() ? '#fff' : 'var(--fg-tertiary)',
            }}
            onClick={handleSubmit}
            disabled={!newComment.trim()}
          >
            <Send size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}
