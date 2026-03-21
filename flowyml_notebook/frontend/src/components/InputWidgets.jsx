import React, { useState, useCallback } from 'react';

/**
 * InputWidgets — renders interactive parameter widgets within cell outputs.
 * Supports: slider, dropdown, text, number, checkbox, date.
 * Values sync back to the kernel namespace via /api/widgets/update.
 */

function WidgetSlider({ widget, onChange }) {
  const { min = 0, max = 100, step = 1 } = widget.config || {};
  const [val, setVal] = useState(widget.value ?? min);

  const handleChange = (e) => {
    const v = parseFloat(e.target.value);
    setVal(v);
    onChange(widget.id, v);
  };

  return (
    <div style={widgetContainer}>
      <label style={widgetLabel}>{widget.label || widget.id}</label>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <input
          type="range" min={min} max={max} step={step} value={val}
          onChange={handleChange}
          style={{ flex: 1, accentColor: '#3b82f6' }}
        />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#93c5fd', minWidth: 40, textAlign: 'right' }}>
          {val}
        </span>
      </div>
    </div>
  );
}

function WidgetDropdown({ widget, onChange }) {
  const options = widget.config?.options || [];
  const [val, setVal] = useState(widget.value ?? options[0] ?? '');

  const handleChange = (e) => {
    setVal(e.target.value);
    onChange(widget.id, e.target.value);
  };

  return (
    <div style={widgetContainer}>
      <label style={widgetLabel}>{widget.label || widget.id}</label>
      <select
        value={val}
        onChange={handleChange}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: 8,
          background: 'var(--bg-primary)', border: '1px solid var(--border)',
          color: 'var(--fg-primary)', fontSize: 13,
        }}
      >
        {options.map(opt => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  );
}

function WidgetText({ widget, onChange }) {
  const [val, setVal] = useState(widget.value ?? '');

  const handleBlur = () => {
    onChange(widget.id, val);
  };

  return (
    <div style={widgetContainer}>
      <label style={widgetLabel}>{widget.label || widget.id}</label>
      <input
        type="text"
        value={val}
        onChange={e => setVal(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={e => { if (e.key === 'Enter') handleBlur(); }}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: 8,
          background: 'var(--bg-primary)', border: '1px solid var(--border)',
          color: 'var(--fg-primary)', fontSize: 13,
        }}
      />
    </div>
  );
}

function WidgetNumber({ widget, onChange }) {
  const [val, setVal] = useState(widget.value ?? 0);

  const handleBlur = () => {
    onChange(widget.id, parseFloat(val) || 0);
  };

  return (
    <div style={widgetContainer}>
      <label style={widgetLabel}>{widget.label || widget.id}</label>
      <input
        type="number"
        value={val}
        onChange={e => setVal(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={e => { if (e.key === 'Enter') handleBlur(); }}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: 8,
          background: 'var(--bg-primary)', border: '1px solid var(--border)',
          color: 'var(--fg-primary)', fontSize: 13,
        }}
      />
    </div>
  );
}

function WidgetCheckbox({ widget, onChange }) {
  const [val, setVal] = useState(widget.value ?? false);

  const handleChange = (e) => {
    setVal(e.target.checked);
    onChange(widget.id, e.target.checked);
  };

  return (
    <div style={widgetContainer}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
        <input
          type="checkbox" checked={val} onChange={handleChange}
          style={{ accentColor: '#3b82f6', width: 16, height: 16 }}
        />
        <span style={{ fontSize: 13, fontWeight: 500 }}>{widget.label || widget.id}</span>
      </label>
    </div>
  );
}

function WidgetDate({ widget, onChange }) {
  const [val, setVal] = useState(widget.value ?? new Date().toISOString().split('T')[0]);

  const handleChange = (e) => {
    setVal(e.target.value);
    onChange(widget.id, e.target.value);
  };

  return (
    <div style={widgetContainer}>
      <label style={widgetLabel}>{widget.label || widget.id}</label>
      <input
        type="date" value={val} onChange={handleChange}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: 8,
          background: 'var(--bg-primary)', border: '1px solid var(--border)',
          color: 'var(--fg-primary)', fontSize: 13,
        }}
      />
    </div>
  );
}

const WIDGET_MAP = {
  slider: WidgetSlider,
  dropdown: WidgetDropdown,
  select: WidgetDropdown,
  text: WidgetText,
  number: WidgetNumber,
  checkbox: WidgetCheckbox,
  toggle: WidgetCheckbox,
  date: WidgetDate,
};

/**
 * Renders a widget output from a cell.
 * widget data shape: { id, widget_type, label, value, config }
 */
export default function InputWidgets({ widgets = [] }) {
  const handleWidgetChange = useCallback(async (widgetId, value) => {
    try {
      await fetch('/api/widgets/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widget_id: widgetId, value }),
      });
    } catch (e) {
      console.error('Widget sync error:', e);
    }
  }, []);

  if (!widgets.length) return null;

  return (
    <div style={{
      padding: '12px 16px', borderRadius: 8,
      background: 'rgba(59,130,246,0.04)', border: '1px solid rgba(59,130,246,0.1)',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
        ⚡ Interactive Parameters
      </div>
      {widgets.map(widget => {
        const WidgetComponent = WIDGET_MAP[widget.widget_type] || WidgetText;
        return <WidgetComponent key={widget.id} widget={widget} onChange={handleWidgetChange} />;
      })}
    </div>
  );
}

// Re-export for rendering a single widget
export function renderWidget(widgetData, onChange) {
  const WidgetComponent = WIDGET_MAP[widgetData.widget_type] || WidgetText;
  return <WidgetComponent widget={widgetData} onChange={onChange} />;
}

const widgetContainer = {
  padding: '6px 0',
};

const widgetLabel = {
  display: 'block', fontSize: 11, fontWeight: 600,
  color: 'var(--fg-muted)', marginBottom: 4,
};
