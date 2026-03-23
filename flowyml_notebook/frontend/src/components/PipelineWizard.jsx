import React, { useState, useCallback } from 'react';
import {
  X, Workflow, Plus, Trash2, GripVertical, ChevronRight,
  ChevronLeft, Check, Zap, Settings, GitBranch, Play,
  ArrowDown, ArrowUp
} from 'lucide-react';

/**
 * Pipeline Builder Wizard — generates a complete multi-cell pipeline
 * from a step-by-step form. Outputs separate cells for context, steps,
 * and the pipeline assembly.
 */
export default function PipelineWizard({ onClose, onGenerateCells }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [config, setConfig] = useState({
    name: 'my_pipeline',
    version: '1.0.0',
    params: [
      { key: 'data_path', value: '"data.csv"' },
      { key: 'learning_rate', value: '0.01' },
    ],
    steps: [
      { name: 'load_data', inputs: '', outputs: 'data/raw', cache: false, desc: 'Load raw data' },
      { name: 'preprocess', inputs: 'data/raw', outputs: 'data/clean', cache: true, desc: 'Clean and preprocess' },
      { name: 'train', inputs: 'data/clean', outputs: 'model/trained', cache: false, desc: 'Train the model' },
    ],
    enableBranch: false,
    branchCondition: 'accuracy > 0.9',
    branchThen: 'deploy',
    branchElse: 'retrain',
    enableSchedule: false,
    cronExpr: '0 2 * * *',
  });

  const WIZARD_STEPS = ['Name & Config', 'Pipeline Steps', 'Control Flow', 'Review & Generate'];

  // --- Param helpers ---
  const addParam = () => setConfig(c => ({
    ...c, params: [...c.params, { key: 'new_param', value: '"value"' }]
  }));
  const removeParam = (i) => setConfig(c => ({
    ...c, params: c.params.filter((_, idx) => idx !== i)
  }));
  const updateParam = (i, field, value) => setConfig(c => ({
    ...c, params: c.params.map((p, idx) => idx === i ? { ...p, [field]: value } : p)
  }));

  // --- Step helpers ---
  const addStep = () => setConfig(c => ({
    ...c, steps: [...c.steps, { name: `step_${c.steps.length + 1}`, inputs: '', outputs: '', cache: false, desc: '' }]
  }));
  const removeStep = (i) => setConfig(c => ({
    ...c, steps: c.steps.filter((_, idx) => idx !== i)
  }));
  const updateStep = (i, field, value) => setConfig(c => ({
    ...c, steps: c.steps.map((s, idx) => idx === i ? { ...s, [field]: value } : s)
  }));
  const moveStep = (i, dir) => setConfig(c => {
    const steps = [...c.steps];
    const newI = i + dir;
    if (newI < 0 || newI >= steps.length) return c;
    [steps[i], steps[newI]] = [steps[newI], steps[i]];
    return { ...c, steps };
  });

  // --- Generate cells ---
  const handleGenerate = useCallback(() => {
    const cells = [];

    // 1. Context cell
    const paramLines = config.params.map(p => `    ${p.key}=${p.value},`).join('\n');
    cells.push({
      name: `${config.name}_context`,
      source: `from flowyml import context\n\nctx = context(\n${paramLines}\n)`,
    });

    // 2. Step cells
    config.steps.forEach(step => {
      const decoratorParts = [];
      if (step.inputs) decoratorParts.push(`inputs=[${step.inputs.split(',').map(i => `"${i.trim()}"`).join(', ')}]`);
      if (step.outputs) decoratorParts.push(`outputs=[${step.outputs.split(',').map(o => `"${o.trim()}"`).join(', ')}]`);
      if (step.cache) decoratorParts.push('cache=True');
      const decoratorArgs = decoratorParts.length > 0 ? decoratorParts.join(', ') : '';
      
      cells.push({
        name: step.name,
        source: `from flowyml import step\n\n@step(${decoratorArgs})\ndef ${step.name}(${step.inputs ? step.inputs.split(',').map(i => i.trim().split('/').pop()).join(', ') : ''}):\n    """${step.desc || 'TODO: Add description.'}"""\n    # TODO: Implement ${step.name}\n    pass`,
      });
    });

    // 3. Branch cell (optional)
    if (config.enableBranch) {
      cells.push({
        name: `${config.name}_branch`,
        source: `from flowyml import step, If\n\n@step(outputs=["deploy/status"])\ndef ${config.branchThen}(model):\n    print("🚀 Deploying!")\n    return {"status": "deployed"}\n\n@step()\ndef ${config.branchElse}(metrics):\n    print("🔄 Retraining needed")\n\ndef check_condition(ctx):\n    """${config.branchCondition}"""\n    return True  # TODO: Implement condition\n\n# pipeline.add_control_flow(If(condition=check_condition, then_step=${config.branchThen}, else_step=${config.branchElse}))`,
      });
    }

    // 4. Pipeline assembly cell
    const stepAddLines = config.steps.map(s => `pipeline.add_step(${s.name})`).join('\n');
    cells.push({
      name: `${config.name}_run`,
      source: `from flowyml import Pipeline\n\npipeline = Pipeline("${config.name}", context=ctx, version="${config.version}")\n${stepAddLines}\n\nresult = pipeline.run()\nprint(f"{'✅' if result.success else '❌'} Pipeline {'completed' if result.success else 'failed'}")`,
    });

    // 5. Schedule cell (optional)
    if (config.enableSchedule) {
      cells.push({
        name: `${config.name}_schedule`,
        source: `from flowyml import PipelineScheduler\n\nscheduler = PipelineScheduler()\nscheduler.schedule_cron(\n    name="${config.name}_cron",\n    pipeline_func=lambda: pipeline.run(),\n    cron="${config.cronExpr}",\n)\n\n# scheduler.start()\nprint("📅 Schedule configured")`,
      });
    }

    onGenerateCells(cells);
    onClose();
  }, [config, onClose, onGenerateCells]);

  return (
    <div className="wizard-overlay" onClick={onClose}>
      <div className="wizard-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="wizard-header">
          <div className="wizard-header-left">
            <Workflow size={18} className="text-indigo-400" />
            <h2>Pipeline Builder</h2>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Step indicators */}
        <div className="wizard-steps">
          {WIZARD_STEPS.map((label, i) => (
            <button
              key={i}
              className={`wizard-step-indicator ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'completed' : ''}`}
              onClick={() => setCurrentStep(i)}
            >
              <span className="wizard-step-number">{i < currentStep ? '✓' : i + 1}</span>
              <span className="wizard-step-label">{label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="wizard-content">
          {/* Step 0: Name & Config */}
          {currentStep === 0 && (
            <div className="wizard-section">
              <div className="wizard-field">
                <label>Pipeline Name</label>
                <input
                  className="wizard-input"
                  value={config.name}
                  onChange={e => setConfig(c => ({ ...c, name: e.target.value }))}
                  placeholder="my_pipeline"
                />
              </div>
              <div className="wizard-field">
                <label>Version</label>
                <input
                  className="wizard-input"
                  value={config.version}
                  onChange={e => setConfig(c => ({ ...c, version: e.target.value }))}
                  placeholder="1.0.0"
                />
              </div>

              <div className="wizard-field">
                <label>
                  Context Parameters
                  <button className="wizard-add-btn" onClick={addParam}>
                    <Plus size={10} /> Add
                  </button>
                </label>
                <div className="wizard-param-list">
                  {config.params.map((p, i) => (
                    <div key={i} className="wizard-param-row">
                      <input
                        className="wizard-input wizard-input-sm"
                        value={p.key}
                        onChange={e => updateParam(i, 'key', e.target.value)}
                        placeholder="key"
                      />
                      <span className="wizard-param-eq">=</span>
                      <input
                        className="wizard-input wizard-input-sm"
                        value={p.value}
                        onChange={e => updateParam(i, 'value', e.target.value)}
                        placeholder="value"
                      />
                      <button className="wizard-remove-btn" onClick={() => removeParam(i)}>
                        <Trash2 size={10} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Pipeline Steps */}
          {currentStep === 1 && (
            <div className="wizard-section">
              <div className="wizard-steps-list">
                {config.steps.map((step, i) => (
                  <div key={i} className="wizard-step-card">
                    <div className="wizard-step-card-header">
                      <div className="wizard-step-card-grip">
                        <button className="btn-icon" style={{ width: 18, height: 18 }} onClick={() => moveStep(i, -1)} disabled={i === 0}>
                          <ArrowUp size={10} />
                        </button>
                        <button className="btn-icon" style={{ width: 18, height: 18 }} onClick={() => moveStep(i, 1)} disabled={i === config.steps.length - 1}>
                          <ArrowDown size={10} />
                        </button>
                      </div>
                      <span className="wizard-step-num">Step {i + 1}</span>
                      <button className="wizard-remove-btn" onClick={() => removeStep(i)}>
                        <Trash2 size={10} />
                      </button>
                    </div>
                    <div className="wizard-step-card-body">
                      <div className="wizard-field-row">
                        <div className="wizard-field" style={{ flex: 2 }}>
                          <label>Function Name</label>
                          <input className="wizard-input" value={step.name} onChange={e => updateStep(i, 'name', e.target.value)} placeholder="step_name" />
                        </div>
                        <div className="wizard-field" style={{ flex: 1 }}>
                          <label>
                            <input type="checkbox" checked={step.cache} onChange={e => updateStep(i, 'cache', e.target.checked)} />
                            {' '}Cache
                          </label>
                        </div>
                      </div>
                      <div className="wizard-field-row">
                        <div className="wizard-field">
                          <label>Inputs <span className="wizard-hint">(comma-separated)</span></label>
                          <input className="wizard-input" value={step.inputs} onChange={e => updateStep(i, 'inputs', e.target.value)} placeholder="data/raw" />
                        </div>
                        <div className="wizard-field">
                          <label>Outputs <span className="wizard-hint">(comma-separated)</span></label>
                          <input className="wizard-input" value={step.outputs} onChange={e => updateStep(i, 'outputs', e.target.value)} placeholder="data/clean" />
                        </div>
                      </div>
                      <div className="wizard-field">
                        <label>Description</label>
                        <input className="wizard-input" value={step.desc} onChange={e => updateStep(i, 'desc', e.target.value)} placeholder="What this step does..." />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <button className="wizard-add-step-btn" onClick={addStep}>
                <Plus size={12} /> Add Step
              </button>
            </div>
          )}

          {/* Step 2: Control Flow */}
          {currentStep === 2 && (
            <div className="wizard-section">
              <div className="wizard-toggle-row">
                <label className="wizard-toggle">
                  <input type="checkbox" checked={config.enableBranch}
                    onChange={e => setConfig(c => ({ ...c, enableBranch: e.target.checked }))} />
                  <GitBranch size={14} />
                  <span>Conditional Branching</span>
                </label>
              </div>

              {config.enableBranch && (
                <div className="wizard-branch-config">
                  <div className="wizard-field">
                    <label>Condition Description</label>
                    <input className="wizard-input" value={config.branchCondition}
                      onChange={e => setConfig(c => ({ ...c, branchCondition: e.target.value }))}
                      placeholder="accuracy > 0.9" />
                  </div>
                  <div className="wizard-field-row">
                    <div className="wizard-field">
                      <label>Then Step (if true)</label>
                      <input className="wizard-input" value={config.branchThen}
                        onChange={e => setConfig(c => ({ ...c, branchThen: e.target.value }))}
                        placeholder="deploy" />
                    </div>
                    <div className="wizard-field">
                      <label>Else Step (if false)</label>
                      <input className="wizard-input" value={config.branchElse}
                        onChange={e => setConfig(c => ({ ...c, branchElse: e.target.value }))}
                        placeholder="retrain" />
                    </div>
                  </div>
                </div>
              )}

              <div className="wizard-toggle-row" style={{ marginTop: 16 }}>
                <label className="wizard-toggle">
                  <input type="checkbox" checked={config.enableSchedule}
                    onChange={e => setConfig(c => ({ ...c, enableSchedule: e.target.checked }))} />
                  <Settings size={14} />
                  <span>Schedule Pipeline</span>
                </label>
              </div>

              {config.enableSchedule && (
                <div className="wizard-field" style={{ marginTop: 8 }}>
                  <label>Cron Expression</label>
                  <input className="wizard-input" value={config.cronExpr}
                    onChange={e => setConfig(c => ({ ...c, cronExpr: e.target.value }))}
                    placeholder="0 2 * * *" />
                  <div className="wizard-cron-presets">
                    {['0 2 * * *', '0 */6 * * *', '0 0 * * 1', '*/30 * * * *'].map(c => (
                      <button key={c} className="wizard-cron-btn" onClick={() => setConfig(cfg => ({ ...cfg, cronExpr: c }))}>
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Review & Generate */}
          {currentStep === 3 && (
            <div className="wizard-section">
              <div className="wizard-review">
                <div className="wizard-review-card">
                  <h4>📋 Pipeline: <code>{config.name}</code> v{config.version}</h4>
                  <div className="wizard-review-row">
                    <span className="wizard-review-label">Context params:</span>
                    <span>{config.params.length}</span>
                  </div>
                  <div className="wizard-review-row">
                    <span className="wizard-review-label">Steps:</span>
                    <span>{config.steps.length}</span>
                  </div>
                  {config.enableBranch && (
                    <div className="wizard-review-row">
                      <span className="wizard-review-label">Branch:</span>
                      <span>If {config.branchCondition} → {config.branchThen} / {config.branchElse}</span>
                    </div>
                  )}
                  {config.enableSchedule && (
                    <div className="wizard-review-row">
                      <span className="wizard-review-label">Schedule:</span>
                      <span>{config.cronExpr}</span>
                    </div>
                  )}
                </div>

                <div className="wizard-review-summary">
                  <Zap size={12} className="text-indigo-400" />
                  Will generate <strong>{1 + config.steps.length + (config.enableBranch ? 1 : 0) + 1 + (config.enableSchedule ? 1 : 0)}</strong> cells:
                  <ul>
                    <li>1 Context cell</li>
                    <li>{config.steps.length} Step cell{config.steps.length !== 1 ? 's' : ''}: {config.steps.map(s => s.name).join(' → ')}</li>
                    {config.enableBranch && <li>1 Branch cell</li>}
                    <li>1 Pipeline assembly cell</li>
                    {config.enableSchedule && <li>1 Schedule cell</li>}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer navigation */}
        <div className="wizard-footer">
          {currentStep > 0 ? (
            <button className="btn btn-ghost" onClick={() => setCurrentStep(s => s - 1)}>
              <ChevronLeft size={14} /> Back
            </button>
          ) : (
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          )}

          {currentStep < WIZARD_STEPS.length - 1 ? (
            <button className="btn btn-primary" onClick={() => setCurrentStep(s => s + 1)}>
              Next <ChevronRight size={14} />
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleGenerate}>
              <Zap size={14} /> Generate Pipeline
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
