import React, { useState, useEffect, useCallback } from 'react';
import {
  Server, Wifi, WifiOff, Globe, Settings, Save,
  CheckCircle, AlertCircle, RefreshCw, ChevronDown, ExternalLink
} from 'lucide-react';

const DEFAULT_CONFIG = {
  mode: 'local', // 'local' | 'remote'
  remoteUrl: '',
  apiKey: '',
  autoConnect: true,
};

export default function ConnectionConfig({ onClose }) {
  const [config, setConfig] = useState(() => {
    try {
      const saved = localStorage.getItem('fml-connection-config');
      return saved ? { ...DEFAULT_CONFIG, ...JSON.parse(saved) } : DEFAULT_CONFIG;
    } catch {
      return DEFAULT_CONFIG;
    }
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saved, setSaved] = useState(false);

  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setTestResult(null);
    setSaved(false);
  };

  const saveConfig = () => {
    localStorage.setItem('fml-connection-config', JSON.stringify(config));
    // Also send to backend
    fetch('/api/config/connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    }).catch(() => {});
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const url = config.mode === 'local'
        ? '/api/health'
        : `${config.remoteUrl}/api/health`;
      
      const headers = {};
      if (config.apiKey) headers['Authorization'] = `Bearer ${config.apiKey}`;
      
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        setTestResult({ success: true, message: `Connected! v${data.version || '?'}` });
      } else {
        setTestResult({ success: false, message: `Error: HTTP ${res.status}` });
      }
    } catch (err) {
      setTestResult({ success: false, message: err.message });
    }
    setTesting(false);
  };

  return (
    <div className="connection-config">
      <div className="conn-header">
        <Server size={14} />
        <span>FlowyML Connection</span>
        {onClose && (
          <button className="btn-icon" onClick={onClose} style={{ marginLeft: 'auto', width: 20, height: 20 }}>×</button>
        )}
      </div>

      <div className="conn-body">
        {/* Mode selector */}
        <div className="conn-section">
          <label className="conn-label">Connection Mode</label>
          <div className="conn-mode-toggle">
            <button
              className={`conn-mode-btn ${config.mode === 'local' ? 'active' : ''}`}
              onClick={() => updateConfig('mode', 'local')}
            >
              <Wifi size={11} /> Local
            </button>
            <button
              className={`conn-mode-btn ${config.mode === 'remote' ? 'active' : ''}`}
              onClick={() => updateConfig('mode', 'remote')}
            >
              <Globe size={11} /> Remote
            </button>
          </div>
          <p className="conn-hint">
            {config.mode === 'local'
              ? 'Uses FlowyML on this machine (localhost)'
              : 'Connect to a remote FlowyML instance'}
          </p>
        </div>

        {/* Remote URL */}
        {config.mode === 'remote' && (
          <>
            <div className="conn-section">
              <label className="conn-label">FlowyML Server URL</label>
              <input
                className="conn-input"
                placeholder="https://flowyml.your-company.com"
                value={config.remoteUrl}
                onChange={e => updateConfig('remoteUrl', e.target.value)}
              />
            </div>
            <div className="conn-section">
              <label className="conn-label">API Key</label>
              <input
                className="conn-input"
                type="password"
                placeholder="fml_key_..."
                value={config.apiKey}
                onChange={e => updateConfig('apiKey', e.target.value)}
              />
            </div>
          </>
        )}

        {/* Auto-connect */}
        <div className="conn-section">
          <label className="conn-checkbox-label">
            <input
              type="checkbox"
              checked={config.autoConnect}
              onChange={e => updateConfig('autoConnect', e.target.checked)}
            />
            <span>Auto-connect on startup</span>
          </label>
        </div>

        {/* Actions */}
        <div className="conn-actions">
          <button className="conn-test-btn" onClick={testConnection} disabled={testing}>
            {testing ? <RefreshCw size={11} className="animate-spin" /> : <Wifi size={11} />}
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          <button className="conn-save-btn" onClick={saveConfig}>
            {saved ? <CheckCircle size={11} /> : <Save size={11} />}
            {saved ? 'Saved!' : 'Save'}
          </button>
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`conn-result ${testResult.success ? 'success' : 'error'}`}>
            {testResult.success ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
            <span>{testResult.message}</span>
          </div>
        )}

        {/* Info */}
        <div className="conn-info">
          <p>
            <strong>Local mode:</strong> FlowyML Notebook works standalone for data exploration.
            Connect to a FlowyML instance for experiment tracking, pipeline export, and deployment.
          </p>
          <p>
            <strong>Remote mode:</strong> Configure your centralized FlowyML server URL and API key.
            All experiments, models, and pipelines will sync to the remote instance.
          </p>
        </div>
      </div>
    </div>
  );
}
