"""Production deployment from notebook.

Provides tools to promote notebooks to production pipelines,
deploy trained models to serving, and generate deployment artifacts.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from flowyml_notebook.cells import CellType, NotebookFile

logger = logging.getLogger(__name__)


def promote_to_pipeline(
    notebook: NotebookFile,
    output_path: str | None = None,
    include_markdown: bool = True,
) -> str:
    """Export notebook as a clean, production-ready pipeline .py file.

    Extracts code cells, adds proper imports, formats as a structured
    pipeline script with docstrings from markdown cells.

    Args:
        notebook: The NotebookFile to export.
        output_path: Output file path. Default: {name}_pipeline.py.
        include_markdown: Include markdown cells as docstrings/comments.

    Returns:
        Path to the exported pipeline file.
    """
    name = notebook.metadata.name
    save_path = output_path or f"{name}_pipeline.py"

    lines = [
        f'"""Production pipeline: {name}',
        f"",
        f"Auto-generated from FlowyML Notebook.",
        f"Generated at: {datetime.now().isoformat()}",
        f'"""',
        "",
    ]

    # Collect all imports from code cells (move to top)
    imports = []
    code_lines = []

    for cell in notebook.cells:
        if cell.cell_type == CellType.CODE and cell.source.strip():
            for line in cell.source.split("\n"):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    if line not in imports:
                        imports.append(line)
                else:
                    code_lines.append(line)
            code_lines.append("")  # Separator between cells

        elif cell.cell_type == CellType.MARKDOWN and include_markdown:
            # Convert markdown to Python comments
            for md_line in cell.source.split("\n"):
                lines.append(f"# {md_line}" if md_line else "#")
            lines.append("")

    # Write imports first
    if imports:
        lines.extend(sorted(set(imports)))
        lines.append("")
        lines.append("")

    # Write code
    lines.extend(code_lines)

    # Add main guard
    lines.extend([
        "",
        'if __name__ == "__main__":',
        f'    print("Running pipeline: {name}")',
        '    # Pipeline auto-executes when this module is run',
    ])

    content = "\n".join(lines) + "\n"
    Path(save_path).write_text(content, encoding="utf-8")
    logger.info(f"Promoted notebook to pipeline: {save_path}")
    return save_path


def deploy_model(
    model: Any,
    endpoint: str | None = None,
    connection: Any = None,
) -> dict:
    """Deploy a model from the notebook to FlowyML serving.

    Args:
        model: The model object from notebook namespace.
        endpoint: Endpoint name for serving.
        connection: FlowyMLConnection for remote deployment.

    Returns:
        Deployment info dict.
    """
    model_name = getattr(model, "name", None) or "notebook_model"
    endpoint_name = endpoint or model_name

    if connection:
        # Remote deployment via API
        deployment_data = {
            "model_name": model_name,
            "endpoint": endpoint_name,
            "source": "notebook",
        }
        result = connection.create_deployment(deployment_data)
        logger.info(f"Deployed model '{model_name}' to remote server: {result}")
        return result
    else:
        # Local deployment
        try:
            from flowyml.serving.model_server import ModelServer
            server = ModelServer()
            server.register_model(model_name, model)
            result = {
                "model_name": model_name,
                "endpoint": endpoint_name,
                "status": "deployed_locally",
                "created_at": datetime.now().isoformat(),
            }
            logger.info(f"Deployed model '{model_name}' locally")
            return result
        except ImportError:
            raise ImportError("FlowyML serving module required for deployment") from None


def generate_dockerfile(
    notebook: NotebookFile,
    output_path: str = "Dockerfile",
    base_image: str = "python:3.11-slim",
) -> str:
    """Generate a Dockerfile for containerized notebook execution.

    Args:
        notebook: The NotebookFile to containerize.
        output_path: Output path for Dockerfile.
        base_image: Base Docker image.

    Returns:
        Path to generated Dockerfile.
    """
    name = notebook.metadata.name

    # First promote to pipeline
    pipeline_path = promote_to_pipeline(notebook, f"{name}_pipeline.py")

    dockerfile = f"""# FlowyML Notebook — Containerized Pipeline
# Generated from notebook: {name}
FROM {base_image}

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline
COPY {Path(pipeline_path).name} .

# Run pipeline
CMD ["python", "{Path(pipeline_path).name}"]
"""

    Path(output_path).write_text(dockerfile, encoding="utf-8")

    # Generate requirements.txt
    reqs = [
        "flowyml>=1.8.0",
        "pandas>=2.0",
        "numpy>=1.24",
    ]
    Path("requirements.txt").write_text("\n".join(reqs) + "\n", encoding="utf-8")

    logger.info(f"Generated Dockerfile at {output_path}")
    return output_path
