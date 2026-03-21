import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell
} from 'recharts';
import { BarChart3, TrendingUp, Circle, PieChart as PieIcon, Layers } from 'lucide-react';

const CHART_COLORS = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#f43f5e',
  '#a855f7', '#ec4899', '#14b8a6', '#f97316', '#3b82f6',
];

const CHART_TYPES = [
  { id: 'line', icon: TrendingUp, label: 'Line' },
  { id: 'bar', icon: BarChart3, label: 'Bar' },
  { id: 'area', icon: Layers, label: 'Area' },
  { id: 'scatter', icon: Circle, label: 'Scatter' },
  { id: 'pie', icon: PieIcon, label: 'Pie' },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(17, 24, 39, 0.95)', backdropFilter: 'blur(12px)',
      border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
      padding: '0.5rem 0.75rem', fontSize: '0.78rem',
      boxShadow: '0 8px 30px rgba(0,0,0,0.4)',
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 4, fontWeight: 600 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
          <span style={{ color: '#e2e8f0' }}>{p.name}: </span>
          <span style={{ color: p.color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>
            {typeof p.value === 'number' ? p.value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function ChartRenderer({ data, config }) {
  const [chartType, setChartType] = useState(config?.kind || 'line');

  const rows = useMemo(() => {
    if (!data) return [];
    if (typeof data === 'string') try { return JSON.parse(data); } catch { return []; }
    if (data.rows) return data.rows;
    if (Array.isArray(data)) return data;
    return [];
  }, [data]);

  const xKey = config?.x || data?.x || (rows.length > 0 ? Object.keys(rows[0])[0] : '');
  const yKeys = config?.y || data?.y || (rows.length > 0 ? Object.keys(rows[0]).filter(k => k !== xKey && typeof rows[0][k] === 'number') : []);
  const title = config?.title || '';

  if (!rows.length) return null;

  const renderChart = () => {
    const commonProps = {
      data: rows,
      margin: { top: 5, right: 20, left: 10, bottom: 5 },
    };
    const axisProps = {
      tick: { fontSize: 11, fill: '#64748b' },
      axisLine: { stroke: 'rgba(255,255,255,0.06)' },
      tickLine: false,
    };
    const gridProps = {
      strokeDasharray: '3 3',
      stroke: 'rgba(255,255,255,0.04)',
    };

    switch (chartType) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {yKeys.map((key, i) => (
              <Line key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]}
                strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2 }} />
            ))}
          </LineChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {yKeys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]}
                radius={[4, 4, 0, 0]} opacity={0.85} />
            ))}
          </BarChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <defs>
              {yKeys.map((key, i) => (
                <linearGradient key={key} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {yKeys.map((key, i) => (
              <Area key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]}
                fill={`url(#grad-${i})`} strokeWidth={2} />
            ))}
          </AreaChart>
        );

      case 'scatter':
        return (
          <ScatterChart {...commonProps}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey={xKey} {...axisProps} name={xKey} />
            <YAxis dataKey={yKeys[0]} {...axisProps} name={yKeys[0]} />
            <Tooltip content={<CustomTooltip />} />
            <Scatter data={rows} fill={CHART_COLORS[0]} opacity={0.7} />
          </ScatterChart>
        );

      case 'pie':
        return (
          <PieChart>
            <Pie data={rows} dataKey={yKeys[0] || 'value'} nameKey={xKey || 'name'}
              cx="50%" cy="50%" outerRadius={100} innerRadius={50} paddingAngle={2}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={{ stroke: '#64748b' }}>
              {rows.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="chart-container">
      {title && <div className="chart-title">{title}</div>}
      <div className="chart-toolbar">
        {CHART_TYPES.map(ct => (
          <button key={ct.id}
            className={`chart-type-btn ${chartType === ct.id ? 'active' : ''}`}
            onClick={() => setChartType(ct.id)}>
            <ct.icon size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: -2 }} />
            {ct.label}
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
