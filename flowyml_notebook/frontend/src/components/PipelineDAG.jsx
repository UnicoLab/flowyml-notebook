import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  X, Maximize2, Minimize2, Code, Type, Database,
  Play, CheckCircle, AlertCircle, Circle, Zap
} from 'lucide-react';

// Custom node component
function CellNode({ data }) {
  const stateColors = {
    idle: 'var(--border)',
    running: 'var(--accent)',
    success: 'var(--green)',
    error: 'var(--error)',
    stale: 'var(--warning)',
  };

  const typeIcons = {
    code: Code,
    markdown: Type,
    sql: Database,
  };

  const Icon = typeIcons[data.cellType] || Code;
  const stateColor = stateColors[data.state] || stateColors.idle;
  const isDecorated = data.isStep || data.isPipeline;

  return (
    <div
      className={`dag-node ${data.state || 'idle'} ${isDecorated ? 'decorated' : ''}`}
      style={{ borderColor: stateColor }}
      onClick={() => data.onCellClick?.(data.cellId)}
    >
      {/* State indicator */}
      <div className="dag-node-state" style={{ background: stateColor }}>
        {data.state === 'running' && <Play size={8} className="animate-pulse" />}
        {data.state === 'success' && <CheckCircle size={8} />}
        {data.state === 'error' && <AlertCircle size={8} />}
        {data.state === 'stale' && <Zap size={8} />}
        {(!data.state || data.state === 'idle') && <Circle size={8} />}
      </div>

      {/* Node content */}
      <div className="dag-node-body">
        <div className="dag-node-header">
          <Icon size={10} />
          <span className="dag-node-label">
            {data.label || `Cell ${data.index + 1}`}
          </span>
          {data.executionCount > 0 && (
            <span className="dag-node-count">[{data.executionCount}]</span>
          )}
        </div>

        {/* Decorators */}
        {isDecorated && (
          <div className="dag-node-decorators">
            {data.isStep && <span className="dag-decorator step">@step</span>}
            {data.isPipeline && <span className="dag-decorator pipeline">@pipeline</span>}
          </div>
        )}

        {/* Preview */}
        <div className="dag-node-preview">
          {data.preview || '(empty)'}
        </div>

        {/* Variables produced */}
        {data.variables && data.variables.length > 0 && (
          <div className="dag-node-vars">
            {data.variables.map(v => (
              <span key={v} className="dag-var">{v}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const nodeTypes = { cellNode: CellNode };

export default function PipelineDAG({ cells, graph, executing, onClose, onCellClick }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Build nodes and edges from cells + graph
  const { initialNodes, initialEdges, stats } = useMemo(() => {
    const nodes = [];
    const edges = [];
    const varProducers = graph?.var_producers || {};
    const cellStates = graph?.cells || {};

    // Detect @step and @pipeline decorators
    const detectDecorators = (source) => {
      const isStep = /@step|@flowyml\.step|FlowyML\.step/.test(source || '');
      const isPipeline = /@pipeline|@flowyml\.pipeline|FlowyML\.pipeline/.test(source || '');
      return { isStep, isPipeline };
    };

    // Find which variables each cell produces
    const cellProductions = {};
    for (const [varName, producerId] of Object.entries(varProducers)) {
      if (!cellProductions[producerId]) cellProductions[producerId] = [];
      cellProductions[producerId].push(varName);
    }

    // Create nodes
    cells.forEach((cell, i) => {
      const decorators = detectDecorators(cell.source);
      const state = cellStates[cell.id]?.state || 'idle';
      const preview = (cell.source || '').split('\n')[0]?.slice(0, 50) || '';
      const name = cell.name || (decorators.isStep ? `step_${i}` : `cell_${i + 1}`);

      nodes.push({
        id: cell.id,
        type: 'cellNode',
        position: { x: 60, y: i * 140 + 40 },
        data: {
          cellId: cell.id,
          cellType: cell.cell_type,
          label: name,
          index: i,
          state: cell.id === executing ? 'running' : state,
          executionCount: cell.execution_count || 0,
          preview,
          variables: cellProductions[cell.id] || [],
          isStep: decorators.isStep,
          isPipeline: decorators.isPipeline,
          onCellClick,
        },
      });

      // Create edges based on variable dependencies
      const cellInfo = cellStates[cell.id];
      if (cellInfo?.depends_on) {
        for (const depVarName of cellInfo.depends_on) {
          const producerId = varProducers[depVarName];
          if (producerId && producerId !== cell.id) {
            edges.push({
              id: `${producerId}-${cell.id}-${depVarName}`,
              source: producerId,
              target: cell.id,
              label: depVarName,
              type: 'smoothstep',
              animated: executing === cell.id || executing === producerId,
              style: {
                stroke: 'var(--accent)',
                strokeWidth: 1.5,
              },
              labelStyle: {
                fontSize: 9,
                fontFamily: "'JetBrains Mono', monospace",
                fill: 'var(--fg-dim)',
              },
            });
          }
        }
      }
    });

    // If no dependency edges, create sequential edges for visual flow
    if (edges.length === 0 && nodes.length > 1) {
      for (let i = 0; i < nodes.length - 1; i++) {
        edges.push({
          id: `seq-${i}`,
          source: nodes[i].id,
          target: nodes[i + 1].id,
          type: 'smoothstep',
          style: { stroke: 'var(--border)', strokeWidth: 1, strokeDasharray: '4 4' },
        });
      }
    }

    // Stats
    const stepCount = cells.filter(c => detectDecorators(c.source).isStep).length;
    const pipelineCount = cells.filter(c => detectDecorators(c.source).isPipeline).length;

    return {
      initialNodes: nodes,
      initialEdges: edges,
      stats: {
        total: cells.length,
        steps: stepCount,
        pipelines: pipelineCount,
        variables: Object.keys(varProducers).length,
      },
    };
  }, [cells, graph, executing, onCellClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when cells/graph change
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  return (
    <div className={`dag-panel ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Toolbar */}
      <div className="dag-toolbar">
        <div className="dag-toolbar-left">
          <span className="dag-title">Pipeline DAG</span>
          <div className="dag-stats">
            <span className="dag-stat">{stats.total} cells</span>
            {stats.steps > 0 && <span className="dag-stat step">{stats.steps} steps</span>}
            {stats.pipelines > 0 && <span className="dag-stat pipeline">{stats.pipelines} pipelines</span>}
            {stats.variables > 0 && <span className="dag-stat var">{stats.variables} vars</span>}
          </div>
        </div>
        <div className="dag-toolbar-right">
          <button
            className="btn-icon"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            style={{ width: 24, height: 24 }}
          >
            {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
          <button className="btn-icon" onClick={onClose} style={{ width: 24, height: 24 }}>
            <X size={12} />
          </button>
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <div className="dag-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: { stroke: 'var(--accent)', strokeWidth: 1.5 },
          }}
        >
          <Background
            variant="dots"
            gap={16}
            size={1}
            color="var(--border-subtle)"
          />
          <Controls
            showInteractive={false}
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
          />
          <MiniMap
            nodeColor={(node) => {
              const state = node.data?.state;
              if (state === 'success') return 'var(--green)';
              if (state === 'error') return 'var(--error)';
              if (state === 'running') return 'var(--accent)';
              return 'var(--border)';
            }}
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
            maskColor="rgba(0,0,0,0.15)"
          />
        </ReactFlow>
      </div>

      {/* Legend */}
      <div className="dag-legend">
        <span className="dag-legend-item"><Circle size={8} fill="var(--border)" stroke="var(--border)" /> Idle</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--accent)" stroke="var(--accent)" /> Running</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--green)" stroke="var(--green)" /> Success</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--error)" stroke="var(--error)" /> Error</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--warning)" stroke="var(--warning)" /> Stale</span>
      </div>
    </div>
  );
}
