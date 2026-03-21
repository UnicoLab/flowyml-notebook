"""Notebook → Scheduled Pipeline bridge.

Converts notebook cells into a standalone production pipeline script
and registers it with the FlowyML scheduler for automated execution.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from flowyml_notebook.cells import CellType, NotebookFile, serialize_notebook

logger = logging.getLogger(__name__)


def schedule_notebook(
    notebook: Any,
    cron: str | None = None,
    interval_hours: int | None = None,
    pipeline_name: str | None = None,
) -> dict:
    """Schedule a notebook as a production pipeline.

    This performs two steps:
    1. Exports the notebook's code cells as a clean pipeline script
    2. Registers the pipeline with FlowyML's scheduler

    Args:
        notebook: The Notebook instance.
        cron: Cron expression (e.g., "0 2 * * *").
        interval_hours: Run every N hours.
        pipeline_name: Name for the scheduled pipeline.

    Returns:
        Schedule info dict.
    """
    name = pipeline_name or f"{notebook.name}_scheduled"

    # If connected to remote server, use the API
    if notebook._connection:
        return _schedule_remote(notebook, name, cron, interval_hours)
    else:
        return _schedule_local(notebook, name, cron, interval_hours)


def _schedule_remote(
    notebook: Any, name: str, cron: str | None, interval_hours: int | None
) -> dict:
    """Schedule via the FlowyML server API."""
    schedule_data = {
        "name": name,
        "pipeline_name": notebook.name,
        "enabled": True,
        "notebook_source": serialize_notebook(notebook.notebook),
    }

    if cron:
        schedule_data["schedule_type"] = "cron"
        schedule_data["cron_expression"] = cron
    elif interval_hours:
        schedule_data["schedule_type"] = "interval"
        schedule_data["interval_hours"] = interval_hours
    else:
        raise ValueError("Provide either 'cron' or 'interval_hours'")

    result = notebook._connection.create_schedule(schedule_data)
    logger.info(f"Scheduled '{name}' on remote server: {result}")
    return result


def _schedule_local(
    notebook: Any, name: str, cron: str | None, interval_hours: int | None
) -> dict:
    """Schedule using FlowyML's local PipelineScheduler."""
    try:
        from flowyml import PipelineScheduler
    except ImportError:
        raise ImportError("FlowyML is required for local scheduling") from None

    # Export notebook as pipeline script
    script_path = _export_pipeline_script(notebook, name)

    # Create scheduler instance
    scheduler = PipelineScheduler()

    if cron:
        scheduler.schedule(name=name, script_path=script_path, cron=cron)
    elif interval_hours:
        scheduler.schedule(name=name, script_path=script_path, interval_hours=interval_hours)
    else:
        raise ValueError("Provide either 'cron' or 'interval_hours'")

    result = {
        "name": name,
        "script_path": script_path,
        "schedule": cron or f"every {interval_hours}h",
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }

    logger.info(f"Scheduled '{name}' locally: {result}")
    return result


def _export_pipeline_script(notebook: Any, name: str) -> str:
    """Export notebook code cells as a runnable pipeline script."""
    import tempfile
    from pathlib import Path

    lines = [
        '"""Auto-generated pipeline from FlowyML Notebook."""',
        f"# Generated from notebook: {notebook.name}",
        f"# Generated at: {datetime.now().isoformat()}",
        "",
    ]

    # Collect code cells
    for cell in notebook.notebook.cells:
        if cell.cell_type == CellType.CODE and cell.source.strip():
            lines.append(f"# Cell: {cell.name or cell.id}")
            lines.append(cell.source)
            lines.append("")

    content = "\n".join(lines) + "\n"

    # Save to a persistent location
    scripts_dir = Path.home() / ".flowyml" / "scheduled_scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / f"{name}.py"
    script_path.write_text(content, encoding="utf-8")

    return str(script_path)
