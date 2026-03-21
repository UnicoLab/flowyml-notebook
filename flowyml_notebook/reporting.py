"""Report generation from notebook sessions.

Generates HTML and PDF reports from notebook outputs,
with optional Slack/email distribution.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from flowyml_notebook.cells import CellType, NotebookFile

logger = logging.getLogger(__name__)


def generate_report(
    notebook: NotebookFile,
    format: str = "html",
    output_path: str | None = None,
    title: str | None = None,
    include_code: bool = False,
) -> str:
    """Generate a report from a notebook.

    Args:
        notebook: The NotebookFile to report on.
        format: Output format ("html" or "pdf").
        output_path: Output file path.
        title: Report title.
        include_code: Whether to include code cells.

    Returns:
        Path to generated report.
    """
    report_title = title or f"{notebook.metadata.name} — Report"
    save_path = output_path or f"{notebook.metadata.name}_report.{format}"

    if format == "html":
        content = _generate_html_report(notebook, report_title, include_code)
    elif format == "pdf":
        # Generate HTML first, then convert
        html_content = _generate_html_report(notebook, report_title, include_code)
        content = html_content  # PDF conversion would use weasyprint/puppeteer
        save_path = save_path.replace(".pdf", ".html")
        logger.info("PDF generation not yet available, saved as HTML")
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'.")

    Path(save_path).write_text(content, encoding="utf-8")
    logger.info(f"Report generated: {save_path}")
    return save_path


def _generate_html_report(
    notebook: NotebookFile,
    title: str,
    include_code: bool,
) -> str:
    """Generate a beautiful HTML report."""
    cells_html = []

    for cell in notebook.cells:
        if cell.cell_type == CellType.MARKDOWN:
            cells_html.append(f'<div class="cell markdown-cell">{_md_to_html(cell.source)}</div>')

        elif cell.cell_type == CellType.CODE:
            # Code cell
            parts = []
            if include_code:
                parts.append(
                    f'<div class="code-source"><pre><code>{_escape_html(cell.source)}</code></pre></div>'
                )
            # Outputs
            for output in cell.outputs:
                parts.append(_render_output_html(output))
            if parts:
                cells_html.append(f'<div class="cell code-cell">{"".join(parts)}</div>')

        elif cell.cell_type == CellType.SQL:
            if include_code:
                cells_html.append(
                    f'<div class="cell sql-cell"><pre><code class="sql">{_escape_html(cell.source)}</code></pre></div>'
                )
            for output in cell.outputs:
                cells_html.append(f'<div class="cell">{_render_output_html(output)}</div>')

    body = "\n".join(cells_html)
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_escape_html(title)}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-2: #334155;
            --fg: #e2e8f0;
            --fg-muted: #94a3b8;
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.15);
            --success: #10b981;
            --error: #ef4444;
            --border: rgba(255, 255, 255, 0.06);
            --radius: 12px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            background: var(--bg);
            color: var(--fg);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.7;
            padding: 2rem;
        }}

        .report-container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        .report-header {{
            text-align: center;
            padding: 3rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
        }}

        .report-header h1 {{
            font-size: 2.25rem;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .report-header .meta {{
            color: var(--fg-muted);
            font-size: 0.875rem;
        }}

        .cell {{
            margin-bottom: 1.5rem;
            padding: 1.5rem;
            background: var(--surface);
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }}

        .markdown-cell {{
            background: transparent;
            border: none;
            padding: 1rem 0;
        }}

        .markdown-cell h1, .markdown-cell h2, .markdown-cell h3 {{
            font-weight: 600;
            margin: 1.5rem 0 0.75rem;
        }}

        .markdown-cell h1 {{ font-size: 1.75rem; }}
        .markdown-cell h2 {{ font-size: 1.5rem; color: var(--accent); }}
        .markdown-cell h3 {{ font-size: 1.25rem; }}

        .markdown-cell p {{ margin-bottom: 0.75rem; }}
        .markdown-cell ul, .markdown-cell ol {{ padding-left: 1.5rem; margin-bottom: 0.75rem; }}

        .code-source {{
            background: var(--surface-2);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            overflow-x: auto;
        }}

        pre {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; line-height: 1.6; }}
        code {{ color: #e2e8f0; }}
        code.sql {{ color: #93c5fd; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0.5rem 0;
            font-size: 0.875rem;
        }}

        th, td {{
            padding: 0.625rem 0.875rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            font-weight: 600;
            color: var(--accent);
            background: var(--surface-2);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        tr:hover td {{ background: var(--accent-glow); }}

        .output-text {{ white-space: pre-wrap; }}
        .output-error {{ color: var(--error); }}

        .report-footer {{
            text-align: center;
            padding: 2rem 0;
            margin-top: 3rem;
            border-top: 1px solid var(--border);
            color: var(--fg-muted);
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <header class="report-header">
            <h1>{_escape_html(title)}</h1>
            <div class="meta">Generated on {timestamp} • FlowyML Notebook</div>
        </header>
        {body}
        <footer class="report-footer">
            Generated by FlowyML Notebook v0.1.0 • {_escape_html(notebook.metadata.name)}
        </footer>
    </div>
</body>
</html>"""


def _render_output_html(output: Any) -> str:
    """Render a cell output as HTML."""
    otype = output.output_type if hasattr(output, "output_type") else output.get("output_type", "text")
    data = output.data if hasattr(output, "data") else output.get("data", "")
    metadata = output.metadata if hasattr(output, "metadata") else output.get("metadata", {})

    if otype == "text":
        return f'<div class="output-text"><pre>{_escape_html(str(data))}</pre></div>'
    elif otype == "html":
        return f'<div class="output-html">{data}</div>'
    elif otype == "error":
        return f'<div class="output-error"><pre>{_escape_html(str(data))}</pre></div>'
    elif otype == "dataframe":
        return _dataframe_to_html(data, metadata)
    elif otype == "json":
        return f'<div class="output-text"><pre>{_escape_html(str(data))}</pre></div>'
    elif otype == "image":
        return f'<div class="output-image"><img src="{data}" alt="Output" style="max-width:100%;border-radius:8px;"></div>'
    else:
        return f'<div class="output-text"><pre>{_escape_html(str(data))}</pre></div>'


def _dataframe_to_html(data: Any, metadata: dict | None = None) -> str:
    """Convert DataFrame data to rich HTML with stats, charts, and inline visualizations."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return f"<pre>{_escape_html(data)}</pre>"

    if not isinstance(data, list) or not data:
        meta = metadata or {}
        cols = meta.get("columns", [])
        if cols:
            badges = " ".join(
                f'<span style="display:inline-flex;padding:2px 8px;border-radius:6px;font-size:0.65rem;'
                f'background:rgba(99,102,241,0.08);color:#94a3b8;border:1px solid rgba(99,102,241,0.12);'
                f'font-family:monospace">{_escape_html(c)}</span>'
                for c in cols
            )
            return (
                f'<div style="text-align:center;padding:16px;color:#94a3b8;font-size:0.8rem">'
                f'<div style="margin-bottom:10px">Empty DataFrame — 0 rows × {len(cols)} columns</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:4px;justify-content:center">{badges}</div></div>'
            )
        return '<pre style="color:#94a3b8">Empty DataFrame</pre>'

    meta = metadata or {}
    columns = meta.get("columns", list(data[0].keys()))
    dtypes = meta.get("dtypes", {})
    total_rows = meta.get("rows", len(data))
    var_name = meta.get("variable_name", "DataFrame")

    # Compute local stats for charts
    stats_map = {}
    hist_map = {}
    for col in columns:
        vals = [row.get(col) for row in data if row.get(col) is not None and row.get(col) != ""]
        nums = [v for v in vals if isinstance(v, (int, float))]
        if nums:
            sorted_nums = sorted(nums)
            mean = sum(nums) / len(nums)
            variance = sum((x - mean) ** 2 for x in nums) / len(nums)
            std = variance ** 0.5
            stats_map[col] = {
                "type": "numeric", "count": len(nums), "mean": round(mean, 4),
                "std": round(std, 4), "min": sorted_nums[0], "max": sorted_nums[-1],
            }
            # Histogram
            bin_count = min(15, max(5, len(nums) // 5))
            min_val, max_val = sorted_nums[0], sorted_nums[-1]
            bin_width = (max_val - min_val) / bin_count if max_val != min_val else 1
            counts = [0] * bin_count
            for v in nums:
                idx = min(int((v - min_val) / bin_width), bin_count - 1)
                counts[idx] += 1
            hist_map[col] = counts
        else:
            freq: dict = {}
            for v in vals:
                k = str(v)
                freq[k] = freq.get(k, 0) + 1
            stats_map[col] = {"type": "categorical", "count": len(vals), "unique": len(freq), "top": freq}

    # Build HTML
    parts = []

    # Header bar
    parts.append(
        f'<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;font-size:0.72rem;'
        f'background:rgba(99,102,241,0.08);color:#6366f1;font-weight:600;font-family:monospace">'
        f'<span>📊 {_escape_html(var_name)}</span>'
        f'<span style="color:#64748b;font-weight:400">{total_rows:,} × {len(columns)}</span></div>'
    )

    # Stats cards row
    numeric_cols = [c for c in columns if stats_map.get(c, {}).get("type") == "numeric"]
    cat_cols = [c for c in columns if stats_map.get(c, {}).get("type") == "categorical"]

    if numeric_cols:
        parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;padding:12px">')
        for col in numeric_cols:
            s = stats_map[col]
            h = hist_map.get(col, [])
            max_c = max(h) if h else 1
            hist_svg = ""
            if h:
                bar_w = 100 / len(h)
                bars = "".join(
                    f'<rect x="{i * bar_w}%" y="{100 - max(2, (c / max_c) * 100)}%" '
                    f'width="{bar_w * 0.85}%" height="{max(2, (c / max_c) * 100)}%" '
                    f'fill="#6366f1" opacity="0.7" rx="1"/>'
                    for i, c in enumerate(h)
                )
                hist_svg = f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" style="width:100%;height:32px;margin:4px 0">{bars}</svg>'

            parts.append(
                f'<div style="background:#334155;border-radius:8px;padding:10px 12px;border:1px solid rgba(255,255,255,0.06)">'
                f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">{_escape_html(col)}</div>'
                f'<div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-top:2px;font-family:monospace">{s["mean"]:.2f}</div>'
                f'<div style="font-size:0.62rem;color:#94a3b8;margin-top:2px">min: {s["min"]} / max: {s["max"]} / σ: {s["std"]:.2f}</div>'
                f'{hist_svg}</div>'
            )
        parts.append('</div>')

    # Categorical summary
    if cat_cols:
        parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;padding:0 12px 12px">')
        for col in cat_cols:
            s = stats_map[col]
            top_entries = sorted(s.get("top", {}).items(), key=lambda x: -x[1])[:5]
            max_v = top_entries[0][1] if top_entries else 1
            bars = "".join(
                f'<div style="display:flex;align-items:center;gap:4px;margin:2px 0">'
                f'<span style="font-size:0.55rem;color:#94a3b8;min-width:60px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{_escape_html(label)}</span>'
                f'<div style="flex:1;height:6px;border-radius:3px;background:rgba(255,255,255,0.06);overflow:hidden">'
                f'<div style="height:100%;width:{(val / max_v) * 100}%;background:#a78bfa;border-radius:3px"></div></div>'
                f'<span style="font-size:0.5rem;color:#64748b">{val}</span></div>'
                for label, val in top_entries
            )
            parts.append(
                f'<div style="background:#334155;border-radius:8px;padding:10px 12px;border:1px solid rgba(255,255,255,0.06)">'
                f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">{_escape_html(col)}</div>'
                f'<div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-top:2px">{s["unique"]} unique</div>'
                f'{bars}</div>'
            )
        parts.append('</div>')

    # Data table
    rows_html = []
    for i, row in enumerate(data[:100]):
        cells = [f'<td style="text-align:center;color:#64748b;font-size:0.65rem;width:40px">{i}</td>']
        for col in columns:
            v = row.get(col, "")
            dtype = dtypes.get(col, "")
            is_num = "int" in dtype or "float" in dtype
            if v is None:
                cells.append('<td style="color:#64748b;font-style:italic">—</td>')
            elif is_num:
                cells.append(f'<td style="text-align:right;color:#22d3ee">{_escape_html(str(v))}</td>')
            else:
                cells.append(f"<td>{_escape_html(str(v))}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    header = '<th style="width:40px;text-align:center">#</th>'
    for col in columns:
        header += f"<th>{_escape_html(col)}</th>"

    truncation = ""
    if total_rows > 100:
        truncation = f'<div style="padding:6px 12px;font-size:0.7rem;color:#64748b;text-align:center">Showing 100 of {total_rows:,} rows</div>'

    parts.append(
        f'<div style="overflow-x:auto;max-height:500px;overflow-y:auto">'
        f'<table><thead><tr>{header}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>{truncation}'
    )

    return "\n".join(parts)


def _md_to_html(md: str) -> str:
    """Basic markdown to HTML conversion."""
    import re

    lines = md.split("\n")
    html_lines = []

    for line in lines:
        if line.startswith("### "):
            html_lines.append(f"<h3>{_escape_html(line[4:])}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{_escape_html(line[3:])}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{_escape_html(line[2:])}</h1>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{_escape_html(line[2:])}</li>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<p><strong>{_escape_html(line[2:-2])}</strong></p>")
        elif line.strip():
            html_lines.append(f"<p>{_escape_html(line)}</p>")
        else:
            html_lines.append("<br>")

    return "\n".join(html_lines)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
