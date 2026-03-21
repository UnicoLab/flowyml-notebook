import React, { useState } from 'react';
import { ChevronDown, ChevronRight, AlertCircle, Table, Image, LineChart, Box, ExternalLink } from 'lucide-react';
import DataFrameExplorer from './DataFrameExplorer';
import ChartRenderer from './ChartRenderer';
import InputWidgets from './InputWidgets';

export default function CellOutput({ outputs }) {
  if (!outputs || outputs.length === 0) return null;

  return (
    <div className="cell-output">
      {outputs.map((output, i) => (
        <OutputRenderer key={i} output={output} />
      ))}
    </div>
  );
}

function OutputRenderer({ output }) {
  const type = output.output_type;
  const data = output.data;

  switch (type) {
    case 'text':
      return <pre className="output-text">{data}</pre>;

    case 'error':
      return (
        <div className="output-error">
          <div className="flex items-center gap-2 mb-2 font-semibold text-rose-400">
            <AlertCircle size={14} />
            <span>{output.metadata?.ename || 'Error'}</span>
          </div>
          <pre>{data}</pre>
        </div>
      );

    case 'html':
      return <div className="output-html" dangerouslySetInnerHTML={{ __html: data }} />;

    case 'dataframe':
      return <DataFrameExplorer data={data} metadata={output.metadata} variableName={output.metadata?.variable_name} />;

    case 'chart':
      return <ChartRenderer data={data} config={output.metadata} />;

    case 'json':
      return <JsonViewer data={data} />;

    case 'image':
      return (
        <div className="output-image">
          <img src={data} alt="Output" loading="lazy"
            style={{ borderRadius: 8, maxHeight: 400 }} />
        </div>
      );

    case 'asset':
      return <AssetOutput data={data} metadata={output.metadata} />;

    case 'widget':
      return <WidgetOutput data={data} metadata={output.metadata} />;

    case 'pipeline_result':
      return <PipelineResultOutput data={data} />;

    case 'model_info':
      return <ModelInfoOutput data={data} />;

    default:
      return <pre className="output-text">{String(data)}</pre>;
  }
}

/* JSON tree viewer */
function JsonViewer({ data }) {
  const [expanded, setExpanded] = useState(true);
  const parsed = typeof data === 'string' ? JSON.parse(data) : data;

  return (
    <div className="p-2 rounded-lg bg-black/20 border border-white/5">
      <button className="flex items-center gap-1 text-xs text-gray-500 mb-1" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        JSON
      </button>
      {expanded && (
        <pre className="output-text text-xs" style={{ maxHeight: 300, overflow: 'auto' }}>
          {JSON.stringify(parsed, null, 2)}
        </pre>
      )}
    </div>
  );
}

/* FlowyML Asset output */
function AssetOutput({ data, metadata }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/15">
      <div className="w-10 h-10 rounded-lg bg-indigo-500/15 flex items-center justify-center">
        <Box size={18} className="text-indigo-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-200">{metadata?.name || data}</div>
        <div className="text-xs text-gray-500 flex gap-3 mt-0.5">
          <span className="badge info">{metadata?.type || 'Asset'}</span>
          {metadata?.version && <span>v{metadata.version}</span>}
          {metadata?.size && <span>{metadata.size}</span>}
        </div>
      </div>
      <button className="btn-icon" title="Open in FlowyML">
        <ExternalLink size={14} />
      </button>
    </div>
  );
}

/* Widget output — interactive UI elements */
function WidgetOutput({ data, metadata }) {
  const widgetType = data?.widget_type || metadata?.widget_type || 'unknown';

  if (widgetType === 'slider') {
    return (
      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
        <label className="text-xs text-gray-400 mb-1 block">{data.label || 'Slider'}</label>
        <input type="range" min={data.config?.min ?? 0} max={data.config?.max ?? 100}
          defaultValue={data.value ?? 50}
          className="w-full accent-indigo-500" />
        <div className="text-xs text-right text-cyan-400 font-mono mt-1">{data.value ?? 50}</div>
      </div>
    );
  }

  if (widgetType === 'progress') {
    const pct = (data.value ?? 0) * 100;
    return (
      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-gray-400">{data.label || 'Progress'}</span>
          <span className="text-cyan-400 font-mono">{pct.toFixed(0)}%</span>
        </div>
        <div className="progress-bar">
          <div className="fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }

  if (widgetType === 'metrics_dashboard') {
    const metrics = data.metrics || {};
    return (
      <div className="grid grid-cols-3 gap-2 p-2">
        {Object.entries(metrics).map(([key, val]) => (
          <div key={key} className="metric-card">
            <div className="metric-label">{key.replace(/_/g, ' ')}</div>
            <div className="metric-value text-cyan-400 text-lg">
              {typeof val === 'number' ? val.toFixed(4) : val}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Interactive input types — render with bidirectional sync
  const INTERACTIVE_TYPES = ['dropdown', 'select', 'text', 'number', 'checkbox', 'toggle', 'date'];
  if (INTERACTIVE_TYPES.includes(widgetType)) {
    return <InputWidgets widgets={[{ ...data, widget_type: widgetType, id: data.id || `widget_${widgetType}` }]} />;
  }

  return (
    <div className="p-2 rounded-lg border border-white/5 bg-white/[0.02] text-sm">
      <span className="text-indigo-400 text-xs font-mono">Widget:{widgetType}</span>
      <pre className="text-xs text-gray-500 mt-1">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

/* Pipeline execution result */
function PipelineResultOutput({ data }) {
  const steps = data?.steps || [];
  return (
    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
      <div className="flex items-center gap-2 mb-3">
        <div className="text-sm font-semibold text-gray-200">Pipeline Run</div>
        <span className={`badge ${data?.status === 'completed' ? 'success' : 'error'}`}>
          {data?.status || 'unknown'}
        </span>
        {data?.duration && <span className="text-xs text-gray-600 font-mono">{data.duration}s</span>}
      </div>
      <div className="space-y-1">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 py-1">
            <div className={`w-2 h-2 rounded-full ${step.status === 'completed' ? 'bg-emerald-400' : step.status === 'failed' ? 'bg-rose-400' : 'bg-purple-400'}`} />
            <span className="text-xs text-gray-300 flex-1">{step.name}</span>
            <span className="text-[10px] text-gray-600 font-mono">{step.duration || '—'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Model info card */
function ModelInfoOutput({ data }) {
  return (
    <div className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/15">
      <div className="flex items-center gap-2 mb-2">
        <Box size={14} className="text-purple-400" />
        <span className="text-sm font-semibold text-gray-200">{data?.name || 'Model'}</span>
        <span className="badge info">{data?.framework || 'unknown'}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {data?.params && <div><span className="text-gray-600">Params: </span><span className="text-cyan-400 font-mono">{data.params.toLocaleString()}</span></div>}
        {data?.size && <div><span className="text-gray-600">Size: </span><span className="text-gray-300">{data.size}</span></div>}
        {data?.accuracy && <div><span className="text-gray-600">Accuracy: </span><span className="text-emerald-400 font-mono">{data.accuracy}</span></div>}
        {data?.version && <div><span className="text-gray-600">Version: </span><span className="text-gray-300">{data.version}</span></div>}
      </div>
    </div>
  );
}
