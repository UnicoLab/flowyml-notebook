import React, { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  Handle, Position, MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import {
  X, Maximize2, Minimize2, Code, Type, Database,
  Play, CheckCircle, AlertCircle, Circle, Zap, Eye,
  AlertTriangle, LayoutGrid, ArrowDownRight,
} from 'lucide-react';
import {
  detectFlowyML, DETECTION_BADGES,
  extractAllArtifacts, getArtifactType,
} from '../data/flowymlSnippets';

// ═══════════════════════════════════════════════════════════════
// Dagre Auto-Layout Helper
// ═══════════════════════════════════════════════════════════════
const CELL_WIDTH = 320;
const CELL_HEIGHT = 130;
const ART_WIDTH = 180;
const ART_HEIGHT = 90;

function applyDagreLayout(nodes, edges, direction = 'TB') {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: direction,
    nodesep: 70,
    ranksep: 120,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach(node => {
    const isArt = node.type === 'artifactNode';
    g.setNode(node.id, {
      width: isArt ? ART_WIDTH : CELL_WIDTH,
      height: isArt ? ART_HEIGHT : CELL_HEIGHT,
    });
  });

  edges.forEach(edge => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  return nodes.map(node => {
    const pos = g.node(node.id);
    const isArt = node.type === 'artifactNode';
    return {
      ...node,
      position: {
        x: pos.x - (isArt ? ART_WIDTH : CELL_WIDTH) / 2,
        y: pos.y - (isArt ? ART_HEIGHT : CELL_HEIGHT) / 2,
      },
    };
  });
}

// ═══════════════════════════════════════════════════════════════
// ArtifactNode — visual artifact node
// ═══════════════════════════════════════════════════════════════
function ArtifactNode({ data }) {
  const artType = data.artifactType || {};
  const isHighlighted = data.highlighted;
  const hasWarning = data.warning;

  return (
    <div
      className={`artifact-node ${isHighlighted ? 'highlighted' : ''} ${hasWarning ? 'has-warning' : ''}`}
      style={{ '--art-color': artType.color || '#818cf8', borderColor: artType.color || '#818cf8' }}
      title={`Artifact: ${data.label}\nType: ${artType.label || 'Unknown'}${data.producerName ? `\nProducer: ${data.producerName}` : ''}${data.consumers?.length ? `\nConsumed by: ${data.consumers.join(', ')}` : ''}${hasWarning ? `\n⚠️ ${data.warning}` : ''}`}
    >
      <Handle type="target" position={Position.Top} className="artifact-handle" />
      {hasWarning && <div className="artifact-warning-badge"><AlertTriangle size={10} /></div>}
      <div className="artifact-node-icon">{artType.icon || '📦'}</div>
      <div className="artifact-node-label">{data.label}</div>
      <div className="artifact-node-type">{artType.label || 'Artifact'}</div>
      {data.assetNames?.length > 0 && (
        <div className="artifact-node-assets">
          {data.assetNames.map((a, i) => (
            <span key={i} className="artifact-asset-tag">{a.icon} {a.name}</span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="artifact-handle" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CellNode — enhanced code cell node
// ═══════════════════════════════════════════════════════════════
function CellNode({ data }) {
  const stateColors = {
    idle: 'var(--border)', running: 'var(--accent)',
    success: 'var(--green)', error: 'var(--error)', stale: 'var(--warning)',
  };
  const typeIcons = { code: Code, markdown: Type, sql: Database };
  const Icon = typeIcons[data.cellType] || Code;
  const stateColor = stateColors[data.state] || stateColors.idle;
  const hasDecorators = data.flowymlDetections?.length > 0;
  const isHighlighted = data.highlighted;

  return (
    <div
      className={`dag-node ${data.state || 'idle'} ${hasDecorators ? 'decorated' : ''} ${isHighlighted ? 'highlighted' : ''}`}
      style={{ borderColor: isHighlighted ? '#818cf8' : stateColor }}
      onClick={() => data.onCellClick?.(data.cellId)}
    >
      <Handle type="target" position={Position.Top} className="dag-handle" />
      <div className="dag-node-state" style={{ background: stateColor }}>
        {data.state === 'running' && <Play size={8} className="animate-pulse" />}
        {data.state === 'success' && <CheckCircle size={8} />}
        {data.state === 'error' && <AlertCircle size={8} />}
        {data.state === 'stale' && <Zap size={8} />}
        {(!data.state || data.state === 'idle') && <Circle size={8} />}
      </div>
      <div className="dag-node-body">
        <div className="dag-node-header">
          <Icon size={10} />
          <span className="dag-node-label">{data.label || `Cell ${data.index + 1}`}</span>
          {data.executionCount > 0 && <span className="dag-node-count">[{data.executionCount}]</span>}
        </div>
        {hasDecorators && (
          <div className="dag-node-decorators">
            {data.flowymlDetections.map(det => {
              const badge = DETECTION_BADGES[det];
              if (!badge) return null;
              return (
                <span key={det} className="dag-decorator"
                  style={{ background: badge.color + '22', color: badge.color, borderColor: badge.color + '44' }}>
                  {badge.icon} {badge.label}
                </span>
              );
            })}
          </div>
        )}
        <div className="dag-node-preview">{data.preview || '(empty)'}</div>
        {data.variables?.length > 0 && (
          <div className="dag-node-vars">
            {data.variables.map(v => <span key={v} className="dag-var">{v}</span>)}
          </div>
        )}
        {(data.declaredInputs?.length > 0 || data.declaredOutputs?.length > 0) && (
          <div className="dag-node-io">
            {data.declaredInputs?.length > 0 && (
              <span className="dag-io input" title="Declared inputs">← {data.declaredInputs.join(', ')}</span>
            )}
            {data.declaredOutputs?.length > 0 && (
              <span className="dag-io output" title="Declared outputs">→ {data.declaredOutputs.join(', ')}</span>
            )}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="dag-handle" />
    </div>
  );
}

const nodeTypes = { cellNode: CellNode, artifactNode: ArtifactNode };

// ═══════════════════════════════════════════════════════════════
// Main PipelineDAG Component
// ═══════════════════════════════════════════════════════════════
export default function PipelineDAG({ cells, graph, executing, onClose, onCellClick }) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [highlightedArtifact, setHighlightedArtifact] = useState(null);
  const [showArtifacts, setShowArtifacts] = useState(true);
  const [layoutDir, setLayoutDir] = useState('TB');

  const { initialNodes, initialEdges, stats, artifactInventory } = useMemo(() => {
    let nodes = [];
    const edges = [];
    const varProducers = graph?.var_producers || {};
    const cellStates = graph?.cells || {};
    const artifactProducers = {};
    const artifactConsumers = {};
    const artifactAssets = {};
    const allArtifactKeys = new Set();

    // First pass — detect constructs & artifact IO
    const cellData = cells.map((cell, i) => {
      const detections = detectFlowyML(cell.source) || [];
      const io = extractAllArtifacts(cell.source);
      const state = cellStates[cell.id]?.state || 'idle';
      io.outputs.forEach(art => { artifactProducers[art] = cell.id; allArtifactKeys.add(art); });
      io.inputs.forEach(art => {
        if (!artifactConsumers[art]) artifactConsumers[art] = [];
        artifactConsumers[art].push(cell.id);
        allArtifactKeys.add(art);
      });
      if (io.assets?.length > 0) {
        io.outputs.forEach(art => {
          if (!artifactAssets[art]) artifactAssets[art] = [];
          artifactAssets[art].push(...io.assets);
        });
      }
      return { cell, index: i, detections, io, state };
    });

    const cellProductions = {};
    for (const [v, pid] of Object.entries(varProducers)) {
      if (!cellProductions[pid]) cellProductions[pid] = [];
      cellProductions[pid].push(v);
    }

    // Cell nodes
    cellData.forEach(({ cell, index, detections, io, state }) => {
      const preview = (cell.source || '').split('\n')[0]?.slice(0, 50) || '';
      const name = cell.name || (detections.includes('step')
        ? cell.source?.match(/def\s+(\w+)/)?.[1] || `step_${index}`
        : `cell_${index + 1}`);
      const isHighlighted = highlightedArtifact && (
        io.inputs.includes(highlightedArtifact) || io.outputs.includes(highlightedArtifact)
      );
      nodes.push({
        id: cell.id, type: 'cellNode',
        position: { x: 0, y: 0 },
        data: {
          cellId: cell.id, cellType: cell.cell_type, label: name, index,
          state: cell.id === executing ? 'running' : state,
          executionCount: cell.execution_count || 0, preview,
          variables: cellProductions[cell.id] || [],
          flowymlDetections: detections,
          declaredInputs: io.inputs, declaredOutputs: io.outputs,
          highlighted: isHighlighted, onCellClick,
        },
      });
    });

    // Always compute artifact inventory (for issue detection)
    const artifactInventory = [];
    for (const artKey of allArtifactKeys) {
      const artType = getArtifactType(artKey);
      const producerCellId = artifactProducers[artKey];
      const consumerCellIds = artifactConsumers[artKey] || [];
      const producerCell = cellData.find(d => d.cell.id === producerCellId);
      const producerName = producerCell
        ? (producerCell.cell.name || producerCell.cell.source?.match(/def\s+(\w+)/)?.[1] || `cell_${producerCell.index + 1}`)
        : null;

      // Warning: consumed but never produced
      const warning = (!producerCellId && consumerCellIds.length > 0)
        ? `Artifact "${artKey}" is consumed but has no producer step`
        : null;

      const isHighlighted = highlightedArtifact === artKey;
      const consumerNames = consumerCellIds.map(cid => {
        const cd = cellData.find(d => d.cell.id === cid);
        return cd ? (cd.cell.name || `cell_${cd.index + 1}`) : cid;
      });

      // Only add visual nodes if showArtifacts is on
      if (showArtifacts) {
        nodes.push({
          id: `art-${artKey}`, type: 'artifactNode',
          position: { x: 0, y: 0 },
          data: {
            label: artKey, artifactType: artType,
            producerName, highlighted: isHighlighted,
            assetNames: artifactAssets[artKey] || [],
            warning, consumers: consumerNames,
          },
        });

        // Produce edge
        if (producerCellId) {
          edges.push({
            id: `produce-${producerCellId}-${artKey}`,
            source: producerCellId, target: `art-${artKey}`,
            type: 'smoothstep', animated: executing === producerCellId,
            markerEnd: { type: MarkerType.ArrowClosed, color: artType.color },
            style: { stroke: artType.color, strokeWidth: 2 },
            label: 'produces', labelStyle: { fontSize: 8, fill: artType.color },
          });
        }

        // Consume edges
        for (const consumerId of consumerCellIds) {
          edges.push({
            id: `consume-${artKey}-${consumerId}`,
            source: `art-${artKey}`, target: consumerId,
            type: 'smoothstep', animated: executing === consumerId,
            markerEnd: { type: MarkerType.ArrowClosed, color: artType.color },
            style: { stroke: artType.color, strokeWidth: 2, strokeDasharray: '6 3' },
            label: 'consumes', labelStyle: { fontSize: 8, fill: artType.color },
          });
        }
      }

      artifactInventory.push({
        key: artKey, type: artType, producer: producerName,
        producerCellId, consumers: consumerNames,
        assets: artifactAssets[artKey] || [], warning,
      });
    }

    // Variable dependency edges (cell-to-cell)
    const edgeSet = new Set(edges.map(e => e.id));
    for (const { cell } of cellData) {
      const cellInfo = cellStates[cell.id];
      if (cellInfo?.depends_on) {
        for (const dep of cellInfo.depends_on) {
          const pid = varProducers[dep];
          if (pid && pid !== cell.id) {
            const eid = `var-${pid}-${cell.id}-${dep}`;
            if (!edgeSet.has(eid)) {
              edgeSet.add(eid);
              edges.push({
                id: eid, source: pid, target: cell.id,
                label: dep, type: 'smoothstep',
                animated: executing === cell.id || executing === pid,
                style: { stroke: 'var(--accent)', strokeWidth: 1.5, strokeDasharray: '4 2' },
                labelStyle: { fontSize: 9, fontFamily: "'JetBrains Mono', monospace", fill: 'var(--fg-dim)' },
              });
            }
          }
        }
      }
    }

    // Fallback: sequential flow if no edges
    if (edges.length === 0 && cellData.length > 1) {
      for (let i = 0; i < cellData.length - 1; i++) {
        edges.push({
          id: `seq-${i}`, source: cellData[i].cell.id, target: cellData[i + 1].cell.id,
          type: 'smoothstep',
          style: { stroke: 'var(--border)', strokeWidth: 1, strokeDasharray: '4 4' },
        });
      }
    }

    // Apply dagre layout
    nodes = applyDagreLayout(nodes, edges, layoutDir);

    const allDet = cellData.flatMap(d => d.detections);
    const warnings = artifactInventory.filter(a => a.warning).length;
    const stats = {
      total: cells.length,
      steps: allDet.filter(d => d === 'step').length,
      pipelines: allDet.filter(d => d === 'pipeline').length,
      variables: Object.keys(varProducers).length,
      artifacts: allArtifactKeys.size,
      branches: allDet.filter(d => d === 'branch').length,
      docker: allDet.filter(d => d === 'docker').length,
      serving: allDet.filter(d => d === 'serving').length,
      warnings,
    };

    return { initialNodes: nodes, initialEdges: edges, stats, artifactInventory };
  }, [cells, graph, executing, onCellClick, showArtifacts, highlightedArtifact, layoutDir]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const handleArtifactClick = useCallback((artKey) => {
    setHighlightedArtifact(prev => prev === artKey ? null : artKey);
  }, []);

  const toggleLayout = useCallback(() => {
    setLayoutDir(prev => prev === 'TB' ? 'LR' : 'TB');
  }, []);

  return (
    <div className={`dag-panel ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="dag-toolbar">
        <div className="dag-toolbar-left">
          <span className="dag-title">Pipeline DAG</span>
          <div className="dag-stats">
            <span className="dag-stat">{stats.total} cells</span>
            {stats.steps > 0 && <span className="dag-stat step">{stats.steps} steps</span>}
            {stats.pipelines > 0 && <span className="dag-stat pipeline">{stats.pipelines} pipelines</span>}
            {stats.artifacts > 0 && <span className="dag-stat artifact">{stats.artifacts} artifacts</span>}
            {stats.variables > 0 && <span className="dag-stat var">{stats.variables} vars</span>}
            {stats.branches > 0 && <span className="dag-stat branch">{stats.branches} branches</span>}
            {stats.docker > 0 && <span className="dag-stat docker">🐳 docker</span>}
            {stats.serving > 0 && <span className="dag-stat serving">🌐 serving</span>}
            {stats.warnings > 0 && <span className="dag-stat warning">⚠️ {stats.warnings} issues</span>}
          </div>
        </div>
        <div className="dag-toolbar-right">
          <button className={`btn-icon ${showArtifacts ? 'active' : ''}`}
            onClick={() => setShowArtifacts(!showArtifacts)}
            title={showArtifacts ? 'Hide artifact nodes' : 'Show artifact nodes'}
            style={{ width: 24, height: 24 }}>
            <Eye size={12} />
          </button>
          <button className="btn-icon" onClick={toggleLayout}
            title={`Switch to ${layoutDir === 'TB' ? 'horizontal' : 'vertical'} layout`}
            style={{ width: 24, height: 24 }}>
            {layoutDir === 'TB' ? <ArrowDownRight size={12} /> : <LayoutGrid size={12} />}
          </button>
          <button className="btn-icon"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            style={{ width: 24, height: 24 }}>
            {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
          <button className="btn-icon" onClick={onClose} style={{ width: 24, height: 24 }}>
            <X size={12} />
          </button>
        </div>
      </div>

      {/* ── Issues Banner ── */}
      {stats.warnings > 0 && (
        <div className="dag-issues-banner">
          <div className="dag-issues-header">
            <AlertTriangle size={14} />
            <span className="dag-issues-title">{stats.warnings} Issue{stats.warnings > 1 ? 's' : ''} Detected</span>
          </div>
          <div className="dag-issues-list">
            {artifactInventory.filter(a => a.warning).map(a => (
              <div key={`issue-${a.key}`} className="dag-issue-item" onClick={() => handleArtifactClick(a.key)}>
                <span className="dag-issue-icon">{a.type.icon}</span>
                <span className="dag-issue-text">
                  <strong>{a.key}</strong> — consumed by {a.consumers.join(', ')} but has no producer
                </span>
                <span className="dag-issue-action">→ Add output</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="dag-canvas"
        style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15, minZoom: 0.35 }}
          minZoom={0.35} maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => {
            if (node.type === 'artifactNode') handleArtifactClick(node.data.label);
          }}
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: { stroke: 'var(--accent)', strokeWidth: 1.5 },
          }}
        >
          <Background variant="dots" gap={16} size={1} color="var(--border-subtle)" />
          <Controls showInteractive={false} style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
          }} />
          <MiniMap
            nodeColor={(node) => {
              if (node.type === 'artifactNode') return node.data?.artifactType?.color || '#818cf8';
              const st = node.data?.state;
              if (st === 'success') return 'var(--green)';
              if (st === 'error') return 'var(--error)';
              if (st === 'running') return 'var(--accent)';
              const d = node.data?.flowymlDetections || [];
              if (d.includes('step')) return '#818cf8';
              if (d.includes('pipeline')) return '#a78bfa';
              if (d.includes('docker')) return '#38bdf8';
              return 'var(--border)';
            }}
            style={{
              background: 'var(--bg-secondary)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
            maskColor="rgba(0,0,0,0.15)"
          />
        </ReactFlow>
      </div>

      {/* Artifact Inventory Panel */}
      {artifactInventory.length > 0 && (
        <div className="dag-artifact-inventory">
          <div className="dag-inventory-title">📦 Artifact Lineage ({artifactInventory.length})</div>
          <div className="dag-inventory-list">
            {artifactInventory.map(art => (
              <div key={art.key}
                className={`dag-inventory-item ${highlightedArtifact === art.key ? 'highlighted' : ''} ${art.warning ? 'has-warning' : ''}`}
                onClick={() => handleArtifactClick(art.key)}>
                <span className="inventory-icon">{art.type.icon}</span>
                <span className="inventory-key">{art.key}</span>
                {art.warning && <span className="inventory-warning" title={art.warning}><AlertTriangle size={10} /></span>}
                <span className="inventory-flow">
                  {art.producer && <span className="inventory-producer">← {art.producer}</span>}
                  {art.consumers.length > 0 && (
                    <span className="inventory-consumers">→ {art.consumers.join(', ')}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="dag-legend">
        <span className="dag-legend-item"><Circle size={8} fill="var(--border)" stroke="var(--border)" /> Idle</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--accent)" stroke="var(--accent)" /> Running</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--green)" stroke="var(--green)" /> Success</span>
        <span className="dag-legend-item"><Circle size={8} fill="var(--error)" stroke="var(--error)" /> Error</span>
        <span className="dag-legend-item"><Circle size={8} fill="#818cf8" stroke="#818cf8" /> @step</span>
        <span className="dag-legend-item dag-legend-divider">|</span>
        <span className="dag-legend-item"><span className="legend-line solid" style={{ background: '#22d3ee' }}></span> produces</span>
        <span className="dag-legend-item"><span className="legend-line dashed" style={{ background: '#22d3ee' }}></span> consumes</span>
        <span className="dag-legend-item dag-legend-divider">|</span>
        <span className="dag-legend-item"><span className="legend-diamond" style={{ background: '#22d3ee' }}>◆</span> Data</span>
        <span className="dag-legend-item"><span className="legend-diamond" style={{ background: '#34d399' }}>◆</span> Model</span>
        <span className="dag-legend-item"><span className="legend-diamond" style={{ background: '#fbbf24' }}>◆</span> Metrics</span>
        <span className="dag-legend-item"><span className="legend-diamond" style={{ background: '#fb923c' }}>◆</span> Features</span>
      </div>
    </div>
  );
}
