import React, { useState, useRef, useCallback } from 'react';
import { X, Send, Sparkles, Code, HelpCircle, Bug, Wand2 } from 'lucide-react';

const QUICK_ACTIONS = [
  { icon: Code, label: 'Generate code', action: 'generate' },
  { icon: HelpCircle, label: 'Explain code', action: 'explain' },
  { icon: Bug, label: 'Debug error', action: 'debug' },
  { icon: Wand2, label: 'Optimize', action: 'optimize' },
];

export default function AIPanel({ onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm your FlowyML AI assistant. I can help you generate code, explain concepts, debug errors, and optimize your ML pipelines. What would you like to do?",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // For now, echo back with a placeholder response
      // In production, this would call the AI assistant API
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      }).then(r => r.ok ? r.json() : null);

      const assistantMsg = {
        role: 'assistant',
        content: response?.content ||
          "I'll help with that! (AI endpoint not configured yet. Set OPENAI_API_KEY and install `flowyml-notebook[ai]`)",
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "AI assistant not available. Install with: `pip install 'flowyml-notebook[ai]'`",
      }]);
    }

    setLoading(false);
  }, [loading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="ai-panel">
      {/* Header */}
      <div className="ai-panel-header">
        <h3 className="flex items-center gap-2">
          <Sparkles size={16} />
          AI Assistant
        </h3>
        <button className="btn-icon" onClick={onClose}>
          <X size={16} />
        </button>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-1 p-2 border-b border-white/5">
        {QUICK_ACTIONS.map(action => (
          <button
            key={action.action}
            className="btn btn-ghost text-xs flex-1"
            onClick={() => sendMessage(`${action.label}: `)}
          >
            <action.icon size={12} />
            {action.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="ai-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`ai-message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="ai-message assistant">
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="ai-input-area">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about FlowyML, generate code, debug errors..."
            rows={2}
          />
          <button
            className="absolute right-2 bottom-2 btn-icon text-accent"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
