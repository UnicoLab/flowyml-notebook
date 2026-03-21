import React, { useState, useCallback } from 'react';
import {
  FileText, Download, Eye, X, Code, FileCode, Settings,
  CheckCircle, Loader, ExternalLink
} from 'lucide-react';

export default function ReportGenerator({ onClose, metadata }) {
  const [title, setTitle] = useState(metadata?.name ? `${metadata.name} — Report` : 'Notebook Report');
  const [format, setFormat] = useState('html');
  const [includeCode, setIncludeCode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(null);

  const handlePreview = useCallback(async () => {
    const params = new URLSearchParams({
      include_code: includeCode.toString(),
      title: title,
    });
    window.open(`/api/report/preview?${params}`, '_blank');
  }, [title, includeCode]);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const res = await fetch('/api/report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, format, include_code: includeCode }),
      });
      if (res.ok) {
        const data = await res.json();
        setGenerated(data);
      }
    } catch (e) {
      console.error('Report generation failed:', e);
    }
    setGenerating(false);
  }, [title, format, includeCode]);

  const handleDownload = useCallback(() => {
    const params = new URLSearchParams({
      format,
      include_code: includeCode.toString(),
      title: title,
    });
    window.open(`/api/report/download?${params}`, '_blank');
  }, [title, format, includeCode]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <FileText size={16} style={{ color: '#3b82f6' }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>Generate Report</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--fg-muted)', cursor: 'pointer' }}>
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {/* Title */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Report Title
          </label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={{
              width: '100%', padding: '8px 12px', borderRadius: 8,
              background: 'var(--bg-primary)', border: '1px solid var(--border)',
              color: 'var(--fg-primary)', fontSize: 13,
            }}
          />
        </div>

        {/* Format */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Format
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            {['html', 'pdf'].map(f => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                style={{
                  flex: 1, padding: '10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: format === f ? 'rgba(59,130,246,0.15)' : 'var(--bg-primary)',
                  border: `1px solid ${format === f ? '#3b82f6' : 'var(--border)'}`,
                  color: format === f ? '#93c5fd' : 'var(--fg-muted)',
                  cursor: 'pointer', textTransform: 'uppercase',
                  transition: 'all 0.2s',
                }}
              >
                <FileCode size={14} style={{ marginBottom: 4, display: 'block', margin: '0 auto 4px' }} />
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Include Code */}
        <div style={{ marginBottom: 24 }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
            padding: '10px 12px', borderRadius: 8,
            background: 'var(--bg-primary)', border: '1px solid var(--border)',
          }}>
            <input
              type="checkbox"
              checked={includeCode}
              onChange={e => setIncludeCode(e.target.checked)}
              style={{ accentColor: '#3b82f6' }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Include Code Cells</div>
              <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>Show source code alongside outputs</div>
            </div>
          </label>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            onClick={handlePreview}
            style={{
              padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--bg-primary)', color: 'var(--fg-primary)',
              cursor: 'pointer', fontSize: 13, fontWeight: 500,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
          >
            <Eye size={14} /> Preview in Browser
          </button>

          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              opacity: generating ? 0.7 : 1,
            }}
          >
            {generating ? <Loader size={14} className="animate-spin" /> : <FileText size={14} />}
            {generating ? 'Generating...' : 'Generate Report'}
          </button>

          <button
            onClick={handleDownload}
            style={{
              padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--bg-primary)', color: 'var(--fg-primary)',
              cursor: 'pointer', fontSize: 13, fontWeight: 500,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
          >
            <Download size={14} /> Download {format.toUpperCase()}
          </button>
        </div>

        {/* Generated result */}
        {generated && (
          <div style={{
            marginTop: 16, padding: 12, borderRadius: 8,
            background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <CheckCircle size={14} style={{ color: '#4ade80' }} />
              <span style={{ fontWeight: 600, fontSize: 12, color: '#4ade80' }}>Report Generated</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--fg-muted)', wordBreak: 'break-all' }}>
              {generated.path}
            </div>
          </div>
        )}

        {/* Info */}
        <div style={{
          marginTop: 20, padding: 12, borderRadius: 8,
          background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.1)',
          fontSize: 11, color: 'var(--fg-muted)', lineHeight: 1.6,
        }}>
          <strong style={{ color: '#93c5fd' }}>💡 Report Features</strong>
          <ul style={{ paddingLeft: 16, marginTop: 6 }}>
            <li>Beautiful styled HTML with dark theme</li>
            <li>DataFrame tables with hover effects</li>
            <li>Markdown cells rendered as rich text</li>
            <li>Optional code cell inclusion</li>
            <li>Shareable standalone HTML file</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
