import React from 'react';
import { Cpu, Zap, Database, Code, Check, Loader, AlertCircle, Cloud } from 'lucide-react';

export default function StatusBar({ sessionId, connected, cellCount, executing, variables, saveStatus, lastSaved, dirty }) {
  const varCount = Object.keys(variables || {}).length;
  const dfCount = Object.values(variables || {}).filter(v => v.type === 'DataFrame').length;

  const renderSaveIndicator = () => {
    if (saveStatus === 'saving') {
      return (
        <span className="status-save saving">
          <Loader size={10} className="status-save-spin" />
          Saving...
        </span>
      );
    }
    if (saveStatus === 'saved') {
      return (
        <span className="status-save saved">
          <Check size={10} />
          Saved
        </span>
      );
    }
    if (saveStatus === 'error') {
      return (
        <span className="status-save error">
          <AlertCircle size={10} />
          Save failed
        </span>
      );
    }
    if (dirty) {
      return (
        <span className="status-save dirty">
          <Cloud size={10} />
          Unsaved
        </span>
      );
    }
    return null;
  };

  return (
    <div className="status-bar">
      <div className="status-bar-left">
        {/* Connection */}
        <span className="status-item">
          <span className={`indicator ${connected ? 'connected' : 'disconnected'}`} />
          {connected ? 'Connected' : 'Local'}
        </span>

        {/* Cell count */}
        <span className="status-item">
          <Code size={10} /> {cellCount} cell{cellCount !== 1 ? 's' : ''}
        </span>

        {/* Variables */}
        {varCount > 0 && (
          <span className="status-item">
            <Cpu size={10} /> {varCount} var{varCount !== 1 ? 's' : ''}
          </span>
        )}

        {/* DataFrames */}
        {dfCount > 0 && (
          <span className="status-item dataframe">
            <Database size={10} /> {dfCount} DataFrame{dfCount !== 1 ? 's' : ''}
          </span>
        )}

        {/* Execution indicator */}
        {executing && (
          <span className="status-item executing">
            <Zap size={10} />
            Executing{executing !== 'all' ? ` cell` : ' all'}...
          </span>
        )}
      </div>

      <div className="status-bar-right">
        {/* Save indicator */}
        {renderSaveIndicator()}

        <span className="status-item">Reactive Engine</span>
        <span className="status-item mono">
          Python 3 · IPython · {sessionId?.slice(0, 8) || '—'}
        </span>
        <span className="status-brand">
          FlowyML Notebook
        </span>
      </div>
    </div>
  );
}
