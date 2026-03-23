import React, { useState, useRef, useCallback, useEffect } from 'react';
import { X, Send, Sparkles, Code, HelpCircle, Bug, Wand2, Settings, Check, AlertCircle, RefreshCw, ChevronDown } from 'lucide-react';

const QUICK_ACTIONS = [
  { icon: Code, label: 'Generate code', action: 'generate' },
  { icon: HelpCircle, label: 'Explain code', action: 'explain' },
  { icon: Bug, label: 'Debug error', action: 'debug' },
  { icon: Wand2, label: 'Optimize', action: 'optimize' },
];

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  { id: 'ollama', name: 'Ollama (Local)', models: ['llama3.1', 'llama3.1:70b', 'mistral', 'codellama', 'phi3'] },
  { id: 'anthropic', name: 'Anthropic', models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'] },
  { id: 'google', name: 'Google AI', models: ['gemini-pro', 'gemini-ultra'] },
  { id: 'custom', name: 'Custom Endpoint', models: [] },
];

function AISettings({ onClose }) {
  const [config, setConfig] = useState({ provider: 'openai', model: '', api_key: '', base_url: '', temperature: 0.3 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch('/api/ai/config').then(r => r.json()).then(data => {
      setConfig(prev => ({ ...prev, ...data }));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const selectedProvider = PROVIDERS.find(p => p.id === config.provider) || PROVIDERS[0];

  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setSaved(false);
    setTestResult(null);
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      await fetch('/api/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/ai/test', { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    }
    setTesting(false);
  };

  if (loading) return <div className="p-4 text-xs text-white/40">Loading...</div>;

  return (
    <div className="ai-settings">
      <div className="ai-settings-header">
        <Settings size={13} />
        <span>AI Provider Settings</span>
        <button className="btn-icon ml-auto" onClick={onClose} style={{ width: 18, height: 18 }}>
          <X size={12} />
        </button>
      </div>

      <div className="ai-settings-body">
        {/* Provider */}
        <div className="ai-field">
          <label>Provider</label>
          <select value={config.provider} onChange={e => { updateConfig('provider', e.target.value); updateConfig('model', ''); }}>
            {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>

        {/* Model */}
        <div className="ai-field">
          <label>Model</label>
          {selectedProvider.models.length > 0 ? (
            <select value={config.model} onChange={e => updateConfig('model', e.target.value)}>
              <option value="">Default</option>
              {selectedProvider.models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          ) : (
            <input placeholder="model-name" value={config.model || ''} onChange={e => updateConfig('model', e.target.value)} />
          )}
        </div>

        {/* API Key (not for Ollama) */}
        {config.provider !== 'ollama' && (
          <div className="ai-field">
            <label>API Key {config.api_key_set && <span className="text-green-400 text-[9px]">✓ Set</span>}</label>
            <input
              type="password"
              placeholder={config.api_key_set ? `${config.api_key_preview}` : 'sk-...'}
              value={config.api_key || ''}
              onChange={e => updateConfig('api_key', e.target.value)}
            />
          </div>
        )}

        {/* Base URL (for Ollama & Custom) */}
        {(config.provider === 'ollama' || config.provider === 'custom') && (
          <div className="ai-field">
            <label>Base URL</label>
            <input
              placeholder={config.provider === 'ollama' ? 'http://localhost:11434/v1' : 'https://your-api.com/v1'}
              value={config.base_url || ''}
              onChange={e => updateConfig('base_url', e.target.value)}
            />
          </div>
        )}

        {/* Ollama tip */}
        {config.provider === 'ollama' && (
          <div className="ai-tip">
            💡 100% private — no data leaves your machine. Run <code>ollama serve</code> first.
          </div>
        )}

        {/* Actions */}
        <div className="ai-settings-actions">
          <button className="ai-test-btn" onClick={testConnection} disabled={testing}>
            {testing ? <RefreshCw size={11} className="animate-spin" /> : <Sparkles size={11} />}
            {testing ? 'Testing...' : 'Test'}
          </button>
          <button className="ai-save-btn" onClick={saveConfig} disabled={saving}>
            {saved ? <Check size={11} /> : <Settings size={11} />}
            {saved ? 'Saved!' : 'Save'}
          </button>
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`ai-test-result ${testResult.success ? 'success' : 'error'}`}>
            {testResult.success ? <Check size={11} /> : <AlertCircle size={11} />}
            <span>{testResult.success ? `Connected! Model: ${testResult.model}` : testResult.error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AIPanel({ onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm your FlowyML AI assistant. I can help you generate code, explain concepts, debug errors, and optimize your ML pipelines. What would you like to do?",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      }).then(r => r.ok ? r.json() : null);

      const assistantMsg = {
        role: 'assistant',
        content: response?.content ||
          "AI assistant not configured. Click the ⚙ button above to set up your AI provider.",
        code: response?.code || null,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "AI assistant not available. Click ⚙ to configure your provider (OpenAI, Ollama, etc.)",
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
        <div className="flex items-center gap-1">
          <button
            className="btn-icon"
            onClick={() => setShowSettings(!showSettings)}
            title="AI Settings"
          >
            <Settings size={14} />
          </button>
          <button className="btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Settings Panel (collapsible) */}
      {showSettings && <AISettings onClose={() => setShowSettings(false)} />}

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
            <div className="ai-message-content">{msg.content}</div>
            {msg.code && (
              <pre className="ai-code-block"><code>{msg.code}</code></pre>
            )}
          </div>
        ))}
        {loading && (
          <div className="ai-message assistant">
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
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
