import React, { useState, useRef, useEffect } from 'react';
import { Cpu, Zap, Database, Code, Check, Loader, AlertCircle, Cloud, ChevronDown, Terminal } from 'lucide-react';

export default function StatusBar({
  sessionId, connected, cellCount, executing, variables,
  saveStatus, lastSaved, dirty,
  kernelStatus, kernelInfo,
}) {
  const varCount = Object.keys(variables || {}).length;
  const dfCount = Object.values(variables || {}).filter(v => v.type === 'DataFrame').length;
  const [kernelPickerOpen, setKernelPickerOpen] = useState(false);
  const pickerRef = useRef(null);

  // Close kernel picker on outside click
  useEffect(() => {
    if (!kernelPickerOpen) return;
    const handler = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setKernelPickerOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [kernelPickerOpen]);

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

  const renderKernelStatus = () => {
    if (kernelStatus === 'starting') {
      return (
        <span className="status-item kernel-starting">
          <Loader size={10} className="status-kernel-spin" />
          Starting kernel…
        </span>
      );
    }
    if (kernelStatus === 'ready') {
      return (
        <span className="status-item kernel-ready">
          <span className="indicator connected" />
          Kernel Ready
        </span>
      );
    }
    if (kernelStatus === 'error') {
      return (
        <span className="status-item kernel-error">
          <AlertCircle size={10} />
          Kernel Error
        </span>
      );
    }
    // idle
    return (
      <span className="status-item kernel-idle">
        <span className="indicator idle" />
        Kernel Idle
      </span>
    );
  };

  const availableKernels = kernelInfo?.available_kernels || [];

  return (
    <div className="status-bar">
      <div className="status-bar-left">
        {/* Connection */}
        <span className="status-item">
          <span className={`indicator ${connected ? 'connected' : 'disconnected'}`} />
          {connected ? 'Connected' : 'Local'}
        </span>

        {/* Kernel Status */}
        {renderKernelStatus()}

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

        {/* Kernel Picker */}
        <div className="status-kernel-picker-wrapper" ref={pickerRef}>
          <button
            className="status-kernel-picker-btn"
            onClick={() => setKernelPickerOpen(!kernelPickerOpen)}
            title="Select kernel"
          >
            <Terminal size={10} />
            <span>{kernelInfo?.kernel_name || 'Python 3'} · IPython</span>
            <ChevronDown size={9} />
          </button>

          {kernelPickerOpen && (
            <div className="status-kernel-picker-dropdown">
              <div className="status-kernel-picker-header">Select Kernel</div>
              {availableKernels.map((k, i) => (
                <button
                  key={i}
                  className={`status-kernel-picker-item ${k.current ? 'current' : ''}`}
                  onClick={() => setKernelPickerOpen(false)}
                  title={k.path}
                >
                  <Terminal size={11} />
                  <span className="kernel-item-name">{k.name}</span>
                  {k.current && <Check size={11} className="kernel-item-check" />}
                </button>
              ))}
              {availableKernels.length === 0 && (
                <div className="status-kernel-picker-empty">No kernels detected</div>
              )}
            </div>
          )}
        </div>

        <span className="status-item mono">
          {sessionId?.slice(0, 8) || '—'}
        </span>
        <span className="status-brand">
          FlowyML Notebook
        </span>
      </div>
    </div>
  );
}
