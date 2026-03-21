import React, { useCallback } from 'react';
import CellEditor from './CellEditor';
import CellOutput from './CellOutput';
import FileUploader from './FileUploader';
import { Plus, Code, Type, Database } from 'lucide-react';

export default function CellList({
  cells, graph, executing, focusedCellId, theme,
  onFocusCell, onUpdateCell, onExecuteCell, onDeleteCell, onAddCell,
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
          <div style={{ marginTop: 20, width: '100%', maxWidth: 480 }}>
            <FileUploader />
          </div>
        </div>
      )}

      {cells.map((cell, index) => (
        <React.Fragment key={cell.id}>
          {/* Add cell button between cells */}
          {index > 0 && (
            <AddCellButton onAdd={(type) => onAddCell(type, index)} />
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
            theme={theme}
          />
        </React.Fragment>
      ))}

      {/* Add cell at end */}
      {cells.length > 0 && (
        <AddCellButton onAdd={(type) => onAddCell(type)} />
      )}
    </div>
  );
}

function AddCellButton({ onAdd }) {
  return (
    <div className="add-cell-container">
      <button className="add-cell-btn" onClick={() => onAdd('code')}>
        <Plus size={12} /> Code
      </button>
      <button className="add-cell-btn ml-1" onClick={() => onAdd('markdown')}>
        <Plus size={12} /> Markdown
      </button>
      <button className="add-cell-btn ml-1" onClick={() => onAdd('sql')}>
        <Plus size={12} /> SQL
      </button>
    </div>
  );
}
