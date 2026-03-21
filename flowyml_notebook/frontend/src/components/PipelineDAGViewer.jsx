import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  Handle, Position, useNodesState, useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  CheckCircle2, AlertCircle, Clock, Loader2, Circle,
  Zap, Database, Cpu, Package, ArrowRight, Eye
} from 'lucide-react';

/* ============================================================
   Custom DAG Node
   ========================================================= */
const STATE_STYLES = {
  success: {
    border: '1px solid rgba(16, 185, 129, 0.5)',
    boxShadow: '0 0 20px rgba(16, 185, 129, 0.1)',
    icon: CheckCircle2, color: '#10b981',
  },
  error: {
    border: '1px solid rgba(244, 63, 94, 0.5)',
    boxShadow: '0 0 20px rgba(244, 63, 94, 0.1)',
    icon: AlertCircle, color: '#f43f5e',
  },
  running: {
    border: '1px solid rgba(168, 85, 247, 0.5)',
    boxShadow: '0 0 20px rgba(168, 85, 247, 0.15)',
    icon: Loader2, color: '#a855f7',
  },
  stale: {
    border: '1px solid rgba(245, 158, 11, 0.5)',
    boxShadow: '0 0 12px rgba(245, 158, 11, 0.08)',
    icon: Clock, color: '#f59e0b',
  },
  idle: {
    border: '1px solid rgba(255, 255, 255, 0.08)',
    boxShadow: 'none',
    icon: Circle, color: '#64748b',
  },
};

function DAGNode({ data }) {
  const state = STATE_STYLES[data.state] || STATE_STYLES.idle;
  const StateIcon = state.icon;
  const isRunning = data.state === 'running';

  const TYPE_ICONS = { code: Zap, markdown: null, sql: Database };
  const TypeIcon = TYPE_ICONS[data.cellType] || Zap;

  return (
    <div style={{
      background: 'rgba(17, 24, 39, 0.95)',
      backdropFilter: 'blur(12px)',
      borderRadius: 12,
      padding: '12px 16px',
      minWidth: 180,
      maxWidth: 260,
      border: state.border,
      boxShadow: state.boxShadow,
      transition: 'all 0.2s ease',
      cursor: 'pointer',
    }}>
      {/* Input handle */}
      <Handle type="target" position={Position.Top}
        style={{ background: '#6366f1', width: 8, height: 8, border: '2px solid #0a0f1e' }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <StateIcon size={14} style={{ color: state.color }}
          className={isRunning ? 'animate-spin' : ''} />
        <span style={{
          fontSize: 13, fontWeight: 600, color: '#f1f5f9',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
        }}>
          {data.label}
        </span>
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#64748b' }}>
        {TypeIcon && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            padding: '1px 6px', borderRadius: 4,
            background: data.cellType === 'sql' ? 'rgba(245,158,11,0.1)' : 'rgba(99,102,241,0.1)',
            color: data.cellType === 'sql' ? '#f59e0b' : '#818cf8',
            fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
            <TypeIcon size={9} /> {data.cellType}
          </span>
        )}
        {data.executionCount > 0 && (
          <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            [{data.executionCount}]
          </span>
        )}
      </div>

      {/* Variables produced */}
      {data.writes && data.writes.length > 0 && (
        <div style={{
          marginTop: 8, paddingTop: 6,
          borderTop: '1px solid rgba(255,255,255,0.04)',
          display: 'flex', flexWrap: 'wrap', gap: 4,
        }}>
          {data.writes.slice(0, 5).map(v => (
            <span key={v} style={{
              fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
              padding: '1px 5px', borderRadius: 3,
              background: 'rgba(6, 182, 212, 0.08)', color: '#06b6d4',
            }}>
              {v}
            </span>
          ))}
          {data.writes.length > 5 && (
            <span style={{ fontSize: 10, color: '#475569' }}>+{data.writes.length - 5}</span>
          )}
        </div>
      )}

      {/* Output handle */}
      <Handle type="source" position={Position.Bottom}
        style={{ background: '#6366f1', width: 8, height: 8, border: '2px solid #0a0f1e' }} />
    </div>
  );
}

const nodeTypes = { dagNode: DAGNode };

/* ============================================================
   Layout algorithm — simple layered layout
   ========================================================= */
function layoutDAG(cells, graphData, cellsList) {
  const nodes = [];
  const edges = [];
  const cellMap = {};
  cellsList.forEach(c => { cellMap[c.id] = c; });

  const cellIds = Object.keys(graphData.cells || {});
  if (cellIds.length === 0) return { nodes: [], edges: [] };

  // Build adjacency
  const adj = {};
  const inDegree = {};
  cellIds.forEach(id => {
    adj[id] = [];
    inDegree[id] = 0;
  });
  cellIds.forEach(id => {
    const info = graphData.cells[id];
    (info.downstream || []).forEach(ds => {
      if (adj[id]) adj[id].push(ds);
      inDegree[ds] = (inDegree[ds] || 0) + 1;
    });
  });

  // Topological sort into layers
  const layers = [];
  const queue = cellIds.filter(id => (inDegree[id] || 0) === 0);
  const visited = new Set();

  while (queue.length > 0) {
    const layer = [...queue];
    layers.push(layer);
    queue.length = 0;
    layer.forEach(id => {
      visited.add(id);
      (adj[id] || []).forEach(next => {
        inDegree[next]--;
        if (inDegree[next] === 0 && !visited.has(next)) {
          queue.push(next);
        }
      });
    });
  }

  // Position nodes
  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 90;
  const H_GAP = 60;
  const V_GAP = 50;

  layers.forEach((layer, layerIdx) => {
    const layerWidth = layer.length * NODE_WIDTH + (layer.length - 1) * H_GAP;
    const startX = -layerWidth / 2;

    layer.forEach((cellId, idx) => {
      const cell = cellMap[cellId];
      const info = graphData.cells[cellId] || {};
      nodes.push({
        id: cellId,
        type: 'dagNode',
        position: {
          x: startX + idx * (NODE_WIDTH + H_GAP),
          y: layerIdx * (NODE_HEIGHT + V_GAP),
        },
        data: {
          label: cell?.name || cellId.slice(0, 8),
          state: info.state || 'idle',
          cellType: cell?.cell_type || 'code',
          executionCount: cell?.execution_count || 0,
          writes: info.writes || [],
        },
      });
    });
  });

  // Create edges
  cellIds.forEach(id => {
    const info = graphData.cells[id] || {};
    (info.downstream || []).forEach(ds => {
      edges.push({
        id: `${id}-${ds}`,
        source: id,
        target: ds,
        animated: graphData.cells[ds]?.state === 'running',
        style: {
          stroke: graphData.cells[ds]?.state === 'running' ? '#a855f7' : '#6366f1',
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#6366f1',
          width: 16, height: 16,
        },
      });
    });
  });

  return { nodes, edges };
}

/* ============================================================
   Main Component
   ========================================================= */
export default function PipelineDAGViewer({ graph, cells, onCellClick }) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => layoutDAG(cells, graph, cells),
    [graph, cells]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update when graph changes
  React.useEffect(() => {
    const { nodes: n, edges: e } = layoutDAG(cells, graph, cells);
    setNodes(n);
    setEdges(e);
  }, [graph, cells]);

  const onNodeClick = useCallback((_, node) => {
    if (onCellClick) onCellClick(node.id);
  }, [onCellClick]);

  if (Object.keys(graph?.cells || {}).length === 0) {
    return (
      <div className="dag-container flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
        <div className="text-center">
          <Zap size={32} className="mx-auto text-gray-700 mb-3" />
          <div className="text-gray-500 text-sm">No dependency graph yet</div>
          <div className="text-gray-700 text-xs mt-1">Run cells to build the reactive DAG</div>
        </div>
      </div>
    );
  }

  return (
    <div className="dag-container">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 1.2 }}
        proOptions={{ hideAttribution: true }}
        style={{ background: '#0a0f1e' }}
      >
        <Background
          variant="dots"
          gap={20}
          size={1}
          color="rgba(255, 255, 255, 0.03)"
        />
        <Controls
          style={{
            background: 'rgba(17, 24, 39, 0.9)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 8,
          }}
        />
        <MiniMap
          nodeColor={(node) => {
            const state = node.data?.state;
            if (state === 'success') return '#10b981';
            if (state === 'error') return '#f43f5e';
            if (state === 'running') return '#a855f7';
            if (state === 'stale') return '#f59e0b';
            return '#334155';
          }}
          maskColor="rgba(10, 15, 30, 0.8)"
          style={{
            background: 'rgba(17, 24, 39, 0.9)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 8,
          }}
        />
      </ReactFlow>
    </div>
  );
}
