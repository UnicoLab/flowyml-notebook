import React, { useCallback, useState } from 'react';
import CellEditor from './CellEditor';
import CellOutput from './CellOutput';
import FileUploader from './FileUploader';
import { Plus, Code, Type, Database, Zap, ChevronDown, ChevronUp } from 'lucide-react';
import { FLOWYML_SNIPPETS, QUICK_INSERT_SNIPPETS } from '../data/flowymlSnippets';

export default function CellList({
  cells, graph, executing, focusedCellId, theme,
  onFocusCell, onUpdateCell, onExecuteCell, onDeleteCell, onAddCell,
  onInsertSnippet,
}) {
  const getCellState = useCallback((cellId) => {
    return graph?.cells?.[cellId]?.state || 'idle';
  }, [graph]);

  return (
    <div className="cell-container" id="cell-scroll-container">
      {cells.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <p className="text-lg mb-4">No cells yet</p>
          <div className="flex gap-2">
            <button className="btn btn-primary" onClick={() => onAddCell('code')}>
              <Code size={14} /> Add Code Cell
            </button>
            <button className="btn btn-ghost" onClick={() => onAddCell('markdown')}>
              <Type size={14} /> Add Markdown
            </button>
          </div>

          {/* FlowyML quick-start when empty */}
          <div className="flowyml-quickstart">
            <div className="flowyml-quickstart-label">
              <Zap size={12} /> Quick Start with FlowyML
            </div>
            <div className="flowyml-quickstart-grid">
              {FLOWYML_SNIPPETS.filter(s => ['fml-step', 'fml-pipeline', 'fml-context', 'fml-dataset'].includes(s.id)).map(snippet => (
                <button
                  key={snippet.id}
                  className="flowyml-quickstart-btn"
                  onClick={() => onInsertSnippet?.(snippet.source, snippet.name)}
                  title={snippet.shortDesc}
                >
                  <span className="flowyml-quickstart-icon">{snippet.icon}</span>
                  <span>{snippet.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 20, width: '100%', maxWidth: 480 }}>
            <FileUploader />
          </div>
        </div>
      )}

      {cells.map((cell, index) => (
        <React.Fragment key={cell.id}>
          {/* FlowyML-aware add cell button between cells */}
          {index > 0 && (
            <FlowyMLQuickInsert
              onAdd={(type) => onAddCell(type, index)}
              onInsertSnippet={(source, name) => onInsertSnippet?.(source, name, index)}
            />
          )}

          <CellEditor
            cell={cell}
            state={getCellState(cell.id)}
            focused={focusedCellId === cell.id}
            executing={executing === cell.id || executing === 'all'}
            upstream={graph?.cells?.[cell.id]?.upstream || []}
            downstream={graph?.cells?.[cell.id]?.downstream || []}
            onFocus={() => onFocusCell(cell.id)}
            onUpdate={(source) => onUpdateCell(cell.id, source)}
            onExecute={() => onExecuteCell(cell.id)}
            onDelete={() => onDeleteCell(cell.id)}
            onWrapInStep={onInsertSnippet ? (newSource) => {
              onUpdateCell(cell.id, newSource);
            } : undefined}
            theme={theme}
          />
        </React.Fragment>
      ))}

      {/* Add cell at end */}
      {cells.length > 0 && (
        <FlowyMLQuickInsert
          onAdd={(type) => onAddCell(type)}
          onInsertSnippet={(source, name) => onInsertSnippet?.(source, name)}
        />
      )}
    </div>
  );
}

function FlowyMLQuickInsert({ onAdd, onInsertSnippet }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="add-cell-container">
      {/* Primary row: standard cell types */}
      <div className="add-cell-row">
        <button className="add-cell-btn" onClick={() => onAdd('code')}>
          <Plus size={12} /> Code
        </button>
        <button className="add-cell-btn ml-1" onClick={() => onAdd('markdown')}>
          <Plus size={12} /> Markdown
        </button>
        <button className="add-cell-btn ml-1" onClick={() => onAdd('sql')}>
          <Plus size={12} /> SQL
        </button>

        <div className="add-cell-divider" />

        <button
          className={`add-cell-btn flowyml-toggle ${expanded ? 'active' : ''}`}
          onClick={() => setExpanded(!expanded)}
          title="FlowyML constructs"
        >
          <Zap size={11} />
          FlowyML
          {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        </button>
      </div>

      {/* FlowyML expansion row */}
      {expanded && (
        <div className="flowyml-insert-grid">
          {QUICK_INSERT_SNIPPETS.map(snippet => (
            <button
              key={snippet.id}
              className="flowyml-insert-btn"
              onClick={() => {
                onInsertSnippet(snippet.source, snippet.name);
                setExpanded(false);
              }}
              title={snippet.shortDesc}
            >
              <span className="flowyml-insert-icon">{snippet.icon}</span>
              <span className="flowyml-insert-label">{snippet.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
