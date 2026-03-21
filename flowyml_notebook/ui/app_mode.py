"""Notebook-as-App deployment mode.

Converts a notebook into an interactive web application by hiding code
cells and exposing only outputs and widgets. Supports custom layouts
(grid, tabs, sidebar) and shareable URLs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LayoutType(str, Enum):
    """App layout types."""

    LINEAR = "linear"       # Top-to-bottom (default)
    GRID = "grid"           # CSS grid layout
    TABS = "tabs"           # Tabbed sections
    SIDEBAR = "sidebar"     # Sidebar + main area
    DASHBOARD = "dashboard" # KPI cards + charts grid


@dataclass
class AppConfig:
    """Configuration for app mode deployment."""

    title: str = ""
    layout: LayoutType = LayoutType.LINEAR
    theme: str = "dark"  # "dark", "light", "auto"
    show_code: bool = False
    show_toolbar: bool = True
    allow_interaction: bool = True  # Allow widget interaction
    password: str = ""  # Optional password protection
    grid_columns: int = 2
    cell_visibility: dict[str, bool] = field(default_factory=dict)  # cell_id → visible
    cell_layout: dict[str, dict] = field(default_factory=dict)  # cell_id → {row, col, width, height}

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "layout": self.layout.value,
            "theme": self.theme,
            "show_code": self.show_code,
            "show_toolbar": self.show_toolbar,
            "allow_interaction": self.allow_interaction,
            "grid_columns": self.grid_columns,
            "cell_visibility": self.cell_visibility,
            "cell_layout": self.cell_layout,
        }


class AppMode:
    """Manages the notebook-as-app deployment."""

    def __init__(self, notebook: Any):
        self.notebook = notebook
        self.config = AppConfig(title=notebook.name)

    def configure(
        self,
        layout: str | LayoutType = LayoutType.LINEAR,
        theme: str = "dark",
        show_code: bool = False,
        title: str | None = None,
        grid_columns: int = 2,
    ) -> AppMode:
        if isinstance(layout, str):
            layout = LayoutType(layout)
        self.config.layout = layout
        self.config.theme = theme
        self.config.show_code = show_code
        self.config.grid_columns = grid_columns
        if title:
            self.config.title = title
        return self

    def hide_cell(self, cell_id: str) -> AppMode:
        self.config.cell_visibility[cell_id] = False
        return self

    def show_cell(self, cell_id: str) -> AppMode:
        self.config.cell_visibility[cell_id] = True
        return self

    def set_cell_position(
        self, cell_id: str, row: int = 0, col: int = 0, width: int = 1, height: int = 1
    ) -> AppMode:
        self.config.cell_layout[cell_id] = {
            "row": row, "col": col, "width": width, "height": height,
        }
        return self

    def get_app_state(self) -> dict:
        visible_cells = []
        for cell in self.notebook.cells:
            is_visible = self.config.cell_visibility.get(cell.id, True)
            if not is_visible:
                continue
            if cell.cell_type.value == "code" and not cell.outputs and not self.config.show_code:
                continue
            visible_cells.append({
                "cell": cell.to_dict(),
                "layout": self.config.cell_layout.get(cell.id, {}),
                "show_source": self.config.show_code,
            })

        return {
            "config": self.config.to_dict(),
            "cells": visible_cells,
            "graph": self.notebook.graph.to_dict(),
        }

    def to_html(self) -> str:
        """Export app as standalone HTML file with rich rendering."""
        state = self.get_app_state()
        layout_class = "grid-layout" if self.config.layout in (LayoutType.GRID, LayoutType.DASHBOARD) else ""
        cols = self.config.grid_columns

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="{self.config.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{self.config.title} — FlowyML App</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a; --bg-card: #1e293b; --bg-card-2: #334155;
            --fg: #e2e8f0; --fg-muted: #94a3b8; --fg-dim: #64748b;
            --accent: #6366f1; --accent-light: #818cf8; --accent-glow: rgba(99,102,241,0.12);
            --success: #10b981; --warning: #f59e0b; --error: #ef4444;
            --cyan: #22d3ee; --purple: #a78bfa;
            --border: rgba(255,255,255,0.06); --radius: 12px;
        }}
        [data-theme="light"] {{
            --bg: #f8fafc; --bg-card: #ffffff; --bg-card-2: #f1f5f9;
            --fg: #1e293b; --fg-muted: #64748b; --fg-dim: #94a3b8;
            --border: rgba(0,0,0,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--bg); color: var(--fg); font-family: 'Inter', system-ui, sans-serif; line-height: 1.7; }}

        .app-container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .app-header {{
            text-align: center; padding: 2.5rem 0 2rem; margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
        }}
        .app-header h1 {{
            font-size: 2rem; font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .app-header .meta {{ color: var(--fg-dim); font-size: 0.8rem; margin-top: 0.5rem; }}

        .grid-layout {{ display: grid; grid-template-columns: repeat({cols}, 1fr); gap: 1.25rem; }}

        .cell-card {{
            background: var(--bg-card); border-radius: var(--radius);
            border: 1px solid var(--border); margin-bottom: 1.25rem;
            overflow: hidden; animation: fadeIn 0.3s ease;
        }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .cell-card.markdown {{
            background: transparent; border: none; padding: 0.5rem 0;
        }}
        .cell-card.markdown h1 {{ font-size: 1.6rem; font-weight: 700; margin: 1.2rem 0 0.6rem; }}
        .cell-card.markdown h2 {{ font-size: 1.35rem; font-weight: 600; color: var(--accent-light); margin: 1rem 0 0.5rem; }}
        .cell-card.markdown h3 {{ font-size: 1.1rem; font-weight: 600; margin: 0.8rem 0 0.4rem; }}
        .cell-card.markdown p {{ margin-bottom: 0.7rem; color: var(--fg-muted); }}
        .cell-card.markdown ul, .cell-card.markdown ol {{ padding-left: 1.5rem; margin-bottom: 0.7rem; color: var(--fg-muted); }}

        .code-source {{
            background: var(--bg-card-2); padding: 1rem 1.25rem;
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
            line-height: 1.5; overflow-x: auto; border-bottom: 1px solid var(--border);
            color: var(--fg-muted);
        }}

        .cell-output {{ padding: 1.25rem; }}
        .cell-output pre {{
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
            line-height: 1.5; white-space: pre-wrap; word-break: break-word;
            color: var(--fg-muted);
        }}
        .cell-output .error-output {{
            color: var(--error); background: rgba(239,68,68,0.06);
            border-left: 3px solid var(--error); padding: 0.75rem 1rem;
            border-radius: 6px;
        }}

        /* DataFrame styles */
        .df-wrapper {{ overflow: hidden; border-radius: 8px; }}
        .df-header-bar {{
            display: flex; align-items: center; gap: 8px;
            padding: 8px 12px; font-size: 0.72rem;
            background: var(--accent-glow); color: var(--accent-light);
            font-weight: 600; font-family: 'JetBrains Mono', monospace;
        }}
        .df-shape {{ color: var(--fg-dim); font-weight: 400; }}

        /* Tab system */
        .df-tabs {{ display: flex; gap: 2px; padding: 6px 8px; background: var(--bg-card-2); border-bottom: 1px solid var(--border); flex-wrap: wrap; }}
        .df-tab-btn {{
            padding: 4px 10px; border-radius: 6px; font-size: 0.65rem; font-weight: 600;
            background: none; border: none; color: var(--fg-dim); cursor: pointer;
            transition: all 0.2s;
        }}
        .df-tab-btn:hover {{ color: var(--fg); background: rgba(255,255,255,0.05); }}
        .df-tab-btn.active {{ background: var(--accent-glow); color: var(--accent-light); }}
        .df-tab-content {{ display: none; }}
        .df-tab-content.active {{ display: block; }}

        table.df {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
        table.df th {{
            padding: 0.5rem 0.75rem; text-align: left;
            background: var(--bg-card-2); color: var(--accent-light);
            font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.04em; border-bottom: 2px solid var(--border);
            font-family: 'JetBrains Mono', monospace; position: sticky; top: 0; z-index: 1;
        }}
        table.df td {{
            padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
        }}
        table.df tr:hover td {{ background: var(--accent-glow); }}
        table.df td.num {{ text-align: right; color: var(--cyan); }}
        table.df td.null {{ color: var(--fg-dim); font-style: italic; }}

        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; padding: 12px; }}
        .stat-card {{ background: var(--bg-card-2); border-radius: 8px; padding: 10px 12px; border: 1px solid var(--border); }}
        .stat-card .stat-label {{ font-size: 0.6rem; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.05em; }}
        .stat-card .stat-value {{ font-size: 1rem; font-weight: 700; color: var(--fg); margin-top: 2px; font-family: 'JetBrains Mono', monospace; }}
        .stat-card .stat-detail {{ font-size: 0.62rem; color: var(--fg-muted); margin-top: 2px; }}
        .mini-hist {{ display: flex; align-items: flex-end; gap: 1px; height: 32px; margin: 4px 0; }}
        .mini-hist-bar {{ flex: 1; background: var(--accent); border-radius: 2px 2px 0 0; min-width: 3px; opacity: 0.7; transition: opacity 0.2s; }}
        .mini-hist-bar:hover {{ opacity: 1; }}

        /* Correlation heatmap */
        .corr-grid {{ font-size: 0.6rem; font-family: 'JetBrains Mono', monospace; }}
        .corr-cell {{
            display: flex; align-items: center; justify-content: center;
            padding: 3px; border-radius: 3px; font-size: 0.55rem; font-weight: 600;
            color: var(--fg); min-height: 28px;
        }}
        .corr-label {{ font-size: 0.6rem; color: var(--fg-muted); padding: 3px 4px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .corr-header {{ font-size: 0.55rem; color: var(--fg-dim); text-align: center; padding: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

        /* ML Insights */
        .insight-section {{ margin: 12px 0; }}
        .insight-title {{ font-size: 0.7rem; font-weight: 700; color: var(--fg-muted); margin-bottom: 8px; }}
        .feature-badge {{
            display: inline-flex; padding: 3px 8px; border-radius: 12px;
            font-size: 0.6rem; font-weight: 500; margin: 2px;
        }}
        .algo-card {{
            display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px;
            border-radius: 8px; background: var(--bg-card-2); border: 1px solid var(--border); margin: 4px 0;
        }}
        .algo-card .algo-name {{ font-size: 0.72rem; font-weight: 700; color: var(--fg); }}
        .algo-card .algo-reason {{ font-size: 0.62rem; color: var(--fg-muted); margin-top: 2px; }}

        /* Scatter plot */
        .scatter-controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 8px 12px; }}
        .scatter-controls label {{ font-size: 0.68rem; color: var(--fg-muted); display: flex; align-items: center; gap: 4px; }}
        .scatter-controls select {{
            font-size: 0.68rem; padding: 3px 6px; border-radius: 6px;
            background: var(--bg-card-2); color: var(--fg); border: 1px solid var(--border);
        }}

        .app-footer {{
            text-align: center; padding: 2rem 0; margin-top: 2.5rem;
            border-top: 1px solid var(--border); color: var(--fg-dim); font-size: 0.75rem;
        }}
        .app-footer a {{ color: var(--accent-light); text-decoration: none; }}
        .empty-msg {{ color: var(--fg-dim); font-size: 0.8rem; text-align: center; padding: 2rem; }}

        /* Resizable */
        .resizable-section {{ border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin: 8px 0; position: relative; }}
        .resizable-section .section-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 4px 8px; background: var(--bg-card-2); border-bottom: 1px solid var(--border);
            font-size: 0.68rem; font-weight: 600; color: var(--fg-muted); cursor: pointer;
        }}
        .resizable-section .section-body {{ padding: 8px; overflow: auto; }}
        .section-collapse-btn {{ background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; }}
        .section-collapse-btn:hover {{ background: rgba(255,255,255,0.05); }}
    </style>
</head>
<body>
    <div class="app-container">
        <header class="app-header">
            <h1>{self.config.title}</h1>
            <div class="meta">Published from FlowyML Notebook</div>
        </header>
        <div class="{layout_class}" id="app-content">
        </div>
        <footer class="app-footer">
            Powered by <a href="#">FlowyML Notebook</a>
        </footer>
    </div>
    <script>
        const APP_STATE = {json.dumps(state, default=str)};
        const container = document.getElementById('app-content');
        let dfCounter = 0;

        function escapeHtml(s) {{
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }}

        function corrColor(val) {{
            const abs = Math.abs(val);
            if (val > 0) return `rgba(99,102,241,${{abs*0.8}})`;
            return `rgba(244,63,94,${{abs*0.8}})`;
        }}

        function computeLocalStats(data, cols) {{
            const stats = {{}}, hists = {{}};
            for (const col of cols) {{
                const vals = data.map(r => r[col]).filter(v => v != null && v !== '');
                const nums = vals.filter(v => typeof v === 'number' && !isNaN(v));
                if (nums.length > 0) {{
                    const sorted = [...nums].sort((a,b) => a-b);
                    const mean = nums.reduce((a,b) => a+b,0)/nums.length;
                    const variance = nums.reduce((a,b) => a+(b-mean)**2,0)/nums.length;
                    const std = Math.sqrt(variance);
                    const q = p => {{ const i = p*(sorted.length-1); const lo = Math.floor(i); return sorted[lo]+(sorted[Math.ceil(i)]-(sorted[lo]||0))*(i-lo); }};
                    stats[col] = {{
                        type: 'numeric', count: nums.length, null_count: data.length-vals.length,
                        mean: +mean.toFixed(4), std: +std.toFixed(4),
                        min: sorted[0], max: sorted[sorted.length-1],
                        q25: +q(0.25).toFixed(4), median: +q(0.5).toFixed(4), q75: +q(0.75).toFixed(4),
                    }};
                    const binCount = Math.min(20, Math.max(5, Math.floor(nums.length/5)));
                    const minVal = sorted[0], maxVal = sorted[sorted.length-1];
                    const binWidth = (maxVal-minVal)/binCount || 1;
                    const counts = new Array(binCount).fill(0);
                    const edges = Array.from({{length:binCount+1}}, (_,i) => +(minVal+i*binWidth).toFixed(4));
                    for (const v of nums) {{ const idx = Math.min(Math.floor((v-minVal)/binWidth), binCount-1); counts[idx]++; }}
                    hists[col] = {{ counts, bin_edges: edges }};
                }} else {{
                    const freq = {{}};
                    for (const v of vals) {{ const k = String(v); freq[k] = (freq[k]||0)+1; }}
                    const top = Object.entries(freq).sort((a,b) => b[1]-a[1]);
                    stats[col] = {{
                        type: 'categorical', count: vals.length, null_count: data.length-vals.length,
                        unique: top.length, top_values: Object.fromEntries(top.slice(0,10)),
                    }};
                }}
            }}
            return {{ stats, hists }};
        }}

        function computeCorrelation(data, numCols) {{
            if (numCols.length < 2) return null;
            const means = {{}}, stds = {{}};
            numCols.forEach(c => {{
                const vals = data.map(r => r[c]).filter(v => typeof v === 'number');
                means[c] = vals.reduce((a,b) => a+b,0)/vals.length;
                stds[c] = Math.sqrt(vals.reduce((a,b) => a+(b-means[c])**2,0)/vals.length) || 1;
            }});
            const matrix = numCols.map(c1 => numCols.map(c2 => {{
                if (c1 === c2) return 1;
                const pairs = data.filter(r => typeof r[c1]==='number' && typeof r[c2]==='number');
                if (pairs.length < 3) return 0;
                return +(pairs.reduce((a,r) => a+((r[c1]-means[c1])/stds[c1])*((r[c2]-means[c2])/stds[c2]),0)/pairs.length).toFixed(3);
            }}));
            return {{ columns: numCols, matrix }};
        }}

        function renderDataFrame(output) {{
            const rawData = typeof output.data === 'string' ? JSON.parse(output.data) : output.data;
            const data = Array.isArray(rawData) ? rawData : [];
            const meta = output.metadata || {{}};
            const totalRows = meta.rows || data.length;
            const cols = meta.columns || (data.length > 0 ? Object.keys(data[0]) : []);
            const dtypes = meta.dtypes || {{}};
            const varName = meta.variable_name || 'DataFrame';
            const id = 'df' + (dfCounter++);

            if (data.length === 0) return '<div class="empty-msg">Empty DataFrame — 0 rows</div>';

            const {{ stats, hists }} = computeLocalStats(data, cols);
            const numCols = cols.filter(c => stats[c]?.type === 'numeric');
            const catCols = cols.filter(c => stats[c]?.type !== 'numeric');
            const corr = computeCorrelation(data, numCols);

            let html = '<div class="df-wrapper">';
            // Header
            html += `<div class="df-header-bar"><span>📊 ${{varName}}</span><span class="df-shape">${{totalRows.toLocaleString()}} × ${{cols.length}}</span></div>`;

            // Tabs
            const tabs = ['Table','Stats','Charts','Correlations','Insights','Compare'];
            html += `<div class="df-tabs">`;
            tabs.forEach((tab,i) => {{
                html += `<button class="df-tab-btn ${{i===0?'active':''}}" onclick="switchTab('${{id}}','${{tab.toLowerCase()}}',this)">` +
                    `${{tab}}</button>`;
            }});
            html += '</div>';

            // --- Table Tab ---
            html += `<div class="df-tab-content active" id="${{id}}-table">`;
            html += '<div style="overflow-x:auto;max-height:500px;overflow-y:auto;">';
            html += '<table class="df"><thead><tr><th style="width:40px;text-align:center">#</th>';
            cols.forEach(c => html += `<th>${{escapeHtml(c)}}</th>`);
            html += '</tr></thead><tbody>';
            data.slice(0,100).forEach((row,i) => {{
                html += `<tr><td style="text-align:center;color:var(--fg-dim);font-size:0.65rem">${{i}}</td>`;
                cols.forEach(c => {{
                    const v = row[c];
                    if (v===null||v===undefined) html += '<td class="null">—</td>';
                    else if (typeof v==='number') html += `<td class="num">${{Number.isInteger(v)?v.toLocaleString():v.toFixed(4)}}</td>`;
                    else html += `<td>${{escapeHtml(String(v))}}</td>`;
                }});
                html += '</tr>';
            }});
            html += '</tbody></table></div>';
            if (totalRows > 100) html += `<div style="padding:6px;font-size:0.65rem;color:var(--fg-dim);text-align:center">Showing 100 of ${{totalRows.toLocaleString()}} rows</div>`;
            html += '</div>';

            // --- Stats Tab ---
            html += `<div class="df-tab-content" id="${{id}}-stats"><div class="stats-grid">`;
            numCols.forEach(col => {{
                const s = stats[col]; const h = hists[col];
                html += `<div class="stat-card"><div class="stat-label">${{escapeHtml(col)}}</div>` +
                    `<div class="stat-value">${{s.mean.toFixed(2)}}</div>` +
                    `<div class="stat-detail">min: ${{s.min}} / max: ${{s.max}} / std: ${{s.std.toFixed(2)}}</div>`;
                if (h) {{
                    const maxC = Math.max(...h.counts);
                    html += '<div class="mini-hist">';
                    h.counts.forEach(c => html += `<div class="mini-hist-bar" style="height:${{Math.max(2,(c/maxC)*100)}}%"></div>`);
                    html += '</div>';
                }}
                html += '</div>';
            }});
            catCols.forEach(col => {{
                const s = stats[col];
                html += `<div class="stat-card"><div class="stat-label">${{escapeHtml(col)}}</div>` +
                    `<div class="stat-value">${{s.unique}} unique</div>` +
                    `<div class="stat-detail">${{s.count}} non-null / ${{s.null_count}} null</div></div>`;
            }});
            html += '</div></div>';

            // --- Charts Tab (large histograms) ---
            html += `<div class="df-tab-content" id="${{id}}-charts"><div style="padding:12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;">`;
            numCols.forEach(col => {{
                const h = hists[col]; if (!h) return;
                const maxC = Math.max(...h.counts);
                html += `<div style="background:var(--bg-card-2);border-radius:8px;padding:12px;border:1px solid var(--border)">` +
                    `<div style="font-size:0.68rem;font-weight:600;color:var(--fg-muted);margin-bottom:8px">${{escapeHtml(col)}}</div>` +
                    `<div style="display:flex;align-items:flex-end;gap:1px;height:80px;">`;
                h.counts.forEach((c,i) => {{
                    html += `<div style="flex:1;background:var(--accent);border-radius:2px 2px 0 0;height:${{Math.max(2,(c/maxC)*100)}}%;opacity:0.7;" title="${{h.bin_edges[i].toFixed(1)}}-${{h.bin_edges[i+1].toFixed(1)}}: ${{c}}"></div>`;
                }});
                html += '</div>';
                html += `<div style="display:flex;justify-content:space-between;font-size:0.55rem;color:var(--fg-dim);margin-top:4px"><span>${{h.bin_edges[0].toFixed(1)}}</span><span>${{h.bin_edges[h.bin_edges.length-1].toFixed(1)}}</span></div>`;
                html += '</div>';
            }});
            catCols.forEach(col => {{
                const s = stats[col]; if (!s.top_values) return;
                const entries = Object.entries(s.top_values).slice(0,8);
                const maxV = Math.max(...entries.map(e => e[1]));
                html += `<div style="background:var(--bg-card-2);border-radius:8px;padding:12px;border:1px solid var(--border)">` +
                    `<div style="font-size:0.68rem;font-weight:600;color:var(--fg-muted);margin-bottom:8px">${{escapeHtml(col)}}</div>`;
                entries.forEach(([label,val]) => {{
                    html += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0"><span style="font-size:0.6rem;color:var(--fg-muted);min-width:70px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{escapeHtml(label)}}</span>` +
                        `<div style="flex:1;height:8px;border-radius:4px;background:var(--border);overflow:hidden"><div style="height:100%;width:${{(val/maxV)*100}}%;background:var(--purple);border-radius:4px"></div></div>` +
                        `<span style="font-size:0.55rem;color:var(--fg-dim)">${{val}}</span></div>`;
                }});
                html += '</div>';
            }});
            html += '</div></div>';

            // --- Correlations Tab ---
            html += `<div class="df-tab-content" id="${{id}}-correlations"><div style="padding:12px">`;
            if (corr && corr.columns.length >= 2) {{
                const n = corr.columns.length;
                html += `<div style="font-size:0.65rem;color:var(--fg-dim);margin-bottom:8px">Pearson Correlation Matrix</div>`;
                html += `<div class="corr-grid" style="display:grid;grid-template-columns:80px repeat(${{n}},1fr);gap:1px;">`;
                html += '<div></div>';
                corr.columns.forEach(c => html += `<div class="corr-header" title="${{escapeHtml(c)}}">${{c.length>6?c.slice(0,5)+'…':c}}</div>`);
                corr.matrix.forEach((row,i) => {{
                    html += `<div class="corr-label" title="${{escapeHtml(corr.columns[i])}}">${{corr.columns[i].length>9?corr.columns[i].slice(0,8)+'…':corr.columns[i]}}</div>`;
                    row.forEach(val => html += `<div class="corr-cell" style="background:${{corrColor(val)}}">${{Math.abs(val)>0.01?val.toFixed(2):''}}</div>`);
                }});
                html += '</div>';
                // Strong correlations
                const pairs = [];
                for (let i=0;i<corr.matrix.length;i++) for (let j=i+1;j<corr.matrix[i].length;j++) {{
                    if (Math.abs(corr.matrix[i][j])>=0.5) pairs.push({{a:corr.columns[i],b:corr.columns[j],val:corr.matrix[i][j]}});
                }}
                if (pairs.length > 0) {{
                    pairs.sort((a,b) => Math.abs(b.val)-Math.abs(a.val));
                    html += '<div style="margin-top:12px;font-size:0.65rem;font-weight:600;color:var(--fg-muted);margin-bottom:4px">Notable Correlations (|r| ≥ 0.5)</div><div style="display:flex;flex-wrap:wrap;gap:4px">';
                    pairs.slice(0,8).forEach(p => {{
                        const clr = p.val > 0 ? 'rgba(99,102,241,0.3)' : 'rgba(244,63,94,0.3)';
                        html += `<span style="padding:2px 8px;border-radius:10px;font-size:0.58rem;border:1px solid ${{clr}};color:${{p.val>0?'var(--accent-light)':'var(--error)'}}">${{escapeHtml(p.a)}} ↔ ${{escapeHtml(p.b)}}: <strong>${{p.val.toFixed(2)}}</strong></span>`;
                    }});
                    html += '</div>';
                }}
            }} else {{
                html += '<div class="empty-msg">Need at least 2 numeric columns for correlation analysis</div>';
            }}
            html += '</div></div>';

            // --- Insights Tab (ML) ---
            html += `<div class="df-tab-content" id="${{id}}-insights"><div style="padding:12px;display:flex;flex-direction:column;gap:16px">`;
            // Dataset summary
            html += `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px">`;
            [['📊 Samples', data.length], ['🔢 Features', cols.length], ['#️⃣ Numeric', numCols.length], ['🏷️ Categorical', catCols.length]].forEach(([l,v]) => {{
                html += `<div style="padding:8px 12px;border-radius:8px;background:var(--bg-card-2);border:1px solid var(--border);display:flex;align-items:center;gap:8px">` +
                    `<div><div style="font-size:0.85rem;font-weight:700;color:var(--fg)">${{v}}</div><div style="font-size:0.58rem;color:var(--fg-dim)">${{l}}</div></div></div>`;
            }});
            html += '</div>';

            // Feature types
            const typeColors = {{continuous:'#6366f1',binary:'#10b981',ordinal:'#f59e0b',nominal:'#8b5cf6',high_cardinality:'#ef4444'}};
            html += '<div class="insight-section"><div class="insight-title">Feature Type Classification</div><div style="display:flex;flex-wrap:wrap;gap:4px">';
            cols.forEach(col => {{
                const s = stats[col]; let ftype = 'unknown';
                if (s?.type === 'numeric') {{
                    const uniq = new Set(data.map(r=>r[col])).size;
                    if (uniq <= 2) ftype = 'binary';
                    else if (uniq <= 10) ftype = 'ordinal';
                    else ftype = 'continuous';
                }} else {{
                    if ((s?.unique||0) > 50) ftype = 'high_cardinality';
                    else if ((s?.unique||0) <= 2) ftype = 'binary';
                    else ftype = 'nominal';
                }}
                const c = typeColors[ftype] || '#666';
                html += `<span class="feature-badge" style="background:${{c}}18;color:${{c}};border:1px solid ${{c}}30">${{escapeHtml(col)}} <span style="opacity:0.7">• ${{ftype}}</span></span>`;
            }});
            html += '</div></div>';

            // Variance ranking
            if (numCols.length > 0) {{
                const variances = numCols.map(c => ({{col:c,v:stats[c].std**2}})).sort((a,b)=>b.v-a.v);
                const maxVar = variances[0]?.v || 1;
                html += '<div class="insight-section"><div class="insight-title">📊 Feature Variance Ranking</div>';
                variances.forEach(item => {{
                    html += `<div style="display:flex;align-items:center;gap:8px;padding:3px 0"><span style="font-size:0.68rem;min-width:100px;color:var(--fg)">${{escapeHtml(item.col)}}</span>` +
                        `<div style="flex:1;height:8px;border-radius:4px;background:var(--border);overflow:hidden"><div style="height:100%;width:${{(item.v/maxVar)*100}}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:4px"></div></div>` +
                        `<span style="font-size:0.58rem;color:var(--fg-dim);font-family:monospace;min-width:60px;text-align:right">${{item.v.toFixed(2)}}</span></div>`;
                }});
                html += '</div>';
            }}

            // Algorithm suggestions
            html += '<div class="insight-section"><div class="insight-title">🤖 Algorithm Suggestions</div>';
            const algos = [];
            if (data.length < 1000) algos.push({{name:'Random Forest',icon:'✅',reason:'Good default for small datasets'}});
            else algos.push({{name:'XGBoost / LightGBM',icon:'✅',reason:'Excellent for large tabular datasets'}});
            if (numCols.length > 10) algos.push({{name:'PCA + Dimensionality Reduction',icon:'🔧',reason:`${{numCols.length}} numeric features — consider reducing`}});
            if (catCols.length > 0) algos.push({{name:'CatBoost',icon:'🔄',reason:'Native categorical feature support'}});
            algos.push({{name:'Linear/Logistic Regression',icon:'🔄',reason:'Good baseline for interpretability'}});
            algos.forEach(a => {{
                html += `<div class="algo-card"><span style="font-size:1rem">${{a.icon}}</span><div><div class="algo-name">${{a.name}}</div><div class="algo-reason">${{a.reason}}</div></div></div>`;
            }});
            html += '</div></div></div>';

            // --- Compare Tab (Scatter Plot) ---
            html += `<div class="df-tab-content" id="${{id}}-compare"><div style="padding:12px">`;
            if (numCols.length >= 2) {{
                html += `<div class="scatter-controls">` +
                    `<label>X: <select id="${{id}}-sx" onchange="updateScatter('${{id}}')">${{numCols.map(c => `<option value="${{c}}">${{c}}</option>`).join('')}}</select></label>` +
                    `<label>Y: <select id="${{id}}-sy" onchange="updateScatter('${{id}}')">${{numCols.map((c,i) => `<option value="${{c}}" ${{i===1?'selected':''}}>${{c}}</option>`).join('')}}</select></label>` +
                    `<label>Color: <select id="${{id}}-sc" onchange="updateScatter('${{id}}')"><option value="">None</option>${{cols.map(c => `<option value="${{c}}">${{c}}</option>`).join('')}}</select></label></div>`;
                html += `<div id="${{id}}-scatter-area" style="padding:8px"></div>`;

                // Store data globally for scatter updates
                html += `<script>window['${{id}}_data']=${{JSON.stringify(data.slice(0,500))}};window['${{id}}_cols']=${{JSON.stringify(numCols)}}</` + 'script>';
            }} else {{
                html += '<div class="empty-msg">Need at least 2 numeric columns for scatter plots</div>';
            }}
            html += '</div></div>';

            html += '</div>';
            return html;
        }}

        function switchTab(dfId, tabName, btn) {{
            document.querySelectorAll(`#${{dfId}}-table,#${{dfId}}-stats,#${{dfId}}-charts,#${{dfId}}-correlations,#${{dfId}}-insights,#${{dfId}}-compare`).forEach(el => el.classList.remove('active'));
            const target = document.getElementById(`${{dfId}}-${{tabName}}`);
            if (target) target.classList.add('active');
            btn.parentElement.querySelectorAll('.df-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Auto-render scatter on switch to compare
            if (tabName === 'compare') {{
                setTimeout(() => updateScatter(dfId), 50);
            }}
        }}

        function updateScatter(dfId) {{
            const data = window[dfId+'_data'];
            if (!data) return;
            const xSel = document.getElementById(dfId+'-sx');
            const ySel = document.getElementById(dfId+'-sy');
            const cSel = document.getElementById(dfId+'-sc');
            if (!xSel || !ySel) return;
            const xCol = xSel.value, yCol = ySel.value, cCol = cSel?.value || '';

            const points = data.filter(r => typeof r[xCol]==='number' && typeof r[yCol]==='number');
            if (points.length === 0) return;

            const PALETTE = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#ec4899'];
            let colorMap = null;
            if (cCol) {{
                const uniq = [...new Set(points.map(r => String(r[cCol])))];
                colorMap = {{}};
                uniq.forEach((v,i) => colorMap[v] = PALETTE[i % PALETTE.length]);
            }}

            const xs = points.map(r => r[xCol]), ys = points.map(r => r[yCol]);
            const xMin = Math.min(...xs), xMax = Math.max(...xs);
            const yMin = Math.min(...ys), yMax = Math.max(...ys);
            const xPad = (xMax-xMin)*0.05 || 1, yPad = (yMax-yMin)*0.05 || 1;
            const W = 600, H = 350, m = {{t:20,r:20,b:35,l:55}};
            const pW = W-m.l-m.r, pH = H-m.t-m.b;
            const sx = v => m.l + (v-(xMin-xPad))/((xMax+xPad)-(xMin-xPad))*pW;
            const sy = v => m.t + pH - (v-(yMin-yPad))/((yMax+yPad)-(yMin-yPad))*pH;

            let svg = `<svg viewBox="0 0 ${{W}} ${{H}}" style="width:100%;max-height:400px">`;
            // Grid
            for (let i=0; i<5; i++) {{
                const xv = xMin + (xMax-xMin)*i/4, yv = yMin + (yMax-yMin)*i/4;
                svg += `<line x1="${{sx(xv)}}" x2="${{sx(xv)}}" y1="${{m.t}}" y2="${{m.t+pH}}" stroke="var(--border)" stroke-width="0.5"/>`;
                svg += `<text x="${{sx(xv)}}" y="${{H-5}}" text-anchor="middle" font-size="8" fill="var(--fg-dim)">${{xv>1000?(xv/1000).toFixed(0)+'k':xv.toFixed(1)}}</text>`;
                svg += `<line x1="${{m.l}}" x2="${{m.l+pW}}" y1="${{sy(yv)}}" y2="${{sy(yv)}}" stroke="var(--border)" stroke-width="0.5"/>`;
                svg += `<text x="${{m.l-5}}" y="${{sy(yv)+3}}" text-anchor="end" font-size="8" fill="var(--fg-dim)">${{yv>1000?(yv/1000).toFixed(0)+'k':yv.toFixed(1)}}</text>`;
            }}
            // Axes
            svg += `<line x1="${{m.l}}" x2="${{m.l+pW}}" y1="${{m.t+pH}}" y2="${{m.t+pH}}" stroke="var(--fg-dim)" stroke-width="1"/>`;
            svg += `<line x1="${{m.l}}" x2="${{m.l}}" y1="${{m.t}}" y2="${{m.t+pH}}" stroke="var(--fg-dim)" stroke-width="1"/>`;
            svg += `<text x="${{m.l+pW/2}}" y="${{H}}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--fg-muted)">${{xCol}}</text>`;
            svg += `<text x="10" y="${{m.t+pH/2}}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--fg-muted)" transform="rotate(-90,10,${{m.t+pH/2}})">${{yCol}}</text>`;
            // Points
            points.forEach(r => {{
                const c = cCol && colorMap ? (colorMap[String(r[cCol])] || '#6366f1') : '#6366f1';
                svg += `<circle cx="${{sx(r[xCol])}}" cy="${{sy(r[yCol])}}" r="3" fill="${{c}}" opacity="0.6"><title>${{xCol}}: ${{r[xCol].toFixed(2)}}, ${{yCol}}: ${{r[yCol].toFixed(2)}}${{cCol?', '+cCol+': '+r[cCol]:''}}</title></circle>`;
            }});
            svg += '</svg>';

            // Legend
            if (colorMap) {{
                svg += '<div style="display:flex;flex-wrap:wrap;gap:6px;padding:4px 0">';
                Object.entries(colorMap).forEach(([label,color]) => {{
                    svg += `<span style="display:inline-flex;align-items:center;gap:4px;font-size:0.58rem;color:var(--fg-muted)"><span style="width:8px;height:8px;border-radius:50%;background:${{color}};display:inline-block"></span>${{escapeHtml(label)}}</span>`;
                }});
                svg += '</div>';
            }}

            // Correlation readout
            if (xCol !== yCol) {{
                const mx = xs.reduce((a,b)=>a+b,0)/xs.length, my = ys.reduce((a,b)=>a+b,0)/ys.length;
                const ssx = Math.sqrt(xs.reduce((a,b)=>a+(b-mx)**2,0)/xs.length)||1;
                const ssy = Math.sqrt(ys.reduce((a,b)=>a+(b-my)**2,0)/ys.length)||1;
                const r = points.reduce((a,row)=>a+((row[xCol]-mx)/ssx)*((row[yCol]-my)/ssy),0)/points.length;
                const strength = Math.abs(r)>0.7?'Strong':Math.abs(r)>0.4?'Moderate':'Weak';
                svg += `<div style="padding:6px 10px;border-radius:8px;background:var(--bg-card-2);border:1px solid var(--border);font-size:0.68rem;color:var(--fg-muted);margin-top:8px">` +
                    `📈 Pearson r = <strong style="color:${{r>0?'var(--accent-light)':'var(--error)'}}">${{r.toFixed(3)}}</strong> — ${{strength}} ${{r>0?'positive':'negative'}} correlation</div>`;
            }}

            document.getElementById(dfId+'-scatter-area').innerHTML = svg;
        }}

        function renderOutput(output) {{
            const otype = output.output_type;
            const data = output.data;

            if (otype === 'dataframe') return renderDataFrame(output);
            if (otype === 'text') return `<pre>${{escapeHtml(String(data))}}</pre>`;
            if (otype === 'html') return `<div>${{data}}</div>`;
            if (otype === 'error') return `<div class="error-output"><pre>${{escapeHtml(String(data))}}</pre></div>`;
            if (otype === 'image') return `<img src="${{data}}" style="max-width:100%;border-radius:8px;" alt="Output">`;
            if (otype === 'json') return `<pre>${{escapeHtml(JSON.stringify(data, null, 2))}}</pre>`;
            return `<pre>${{escapeHtml(JSON.stringify(data, null, 2))}}</pre>`;
        }}

        function renderMarkdown(source) {{
            if (!source) return '';
            return source.split('\\n').map(line => {{
                if (line.startsWith('### ')) return `<h3>${{escapeHtml(line.slice(4))}}</h3>`;
                if (line.startsWith('## ')) return `<h2>${{escapeHtml(line.slice(3))}}</h2>`;
                if (line.startsWith('# ')) return `<h1>${{escapeHtml(line.slice(2))}}</h1>`;
                if (line.startsWith('- ')) return `<li>${{escapeHtml(line.slice(2))}}</li>`;
                if (line.startsWith('**') && line.endsWith('**')) return `<p><strong>${{escapeHtml(line.slice(2,-2))}}</strong></p>`;
                if (line.trim()) return `<p>${{escapeHtml(line)}}</p>`;
                return '<br>';
            }}).join('\\n');
        }}

        // Render all cells
        APP_STATE.cells.forEach((item, idx) => {{
            const cell = item.cell;
            const outputs = cell.outputs || [];
            const div = document.createElement('div');
            div.style.animationDelay = `${{idx * 0.05}}s`;

            if (cell.cell_type === 'markdown') {{
                div.className = 'cell-card markdown';
                div.innerHTML = renderMarkdown(cell.source);
                container.appendChild(div);
                return;
            }}

            div.className = 'cell-card';
            if (item.show_source && cell.source) {{
                div.innerHTML += `<div class="code-source"><pre>${{escapeHtml(cell.source)}}</pre></div>`;
            }}
            if (outputs.length > 0) {{
                let outputHTML = '';
                outputs.forEach(output => outputHTML += renderOutput(output));
                div.innerHTML += `<div class="cell-output">${{outputHTML}}</div>`;
            }}
            if (div.innerHTML) container.appendChild(div);
        }});

        if (container.children.length === 0) {{
            container.innerHTML = '<div class="empty-msg">No cell outputs to display. Execute cells first, then publish.</div>';
        }}
    </script>
</body>
</html>"""
