"""Context-aware AI coding assistant for FlowyML Notebook.

Provides intelligent code generation, explanation, debugging, and
autocompletion that understands the FlowyML SDK, the current pipeline
structure, registered assets, and experiment history.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Response from the AI assistant."""

    content: str
    code: str = ""  # Extracted code block if any
    explanation: str = ""
    suggestions: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "code": self.code,
            "explanation": self.explanation,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
        }


class NotebookAIAssistant:
    """FlowyML-aware AI coding assistant.

    Understands:
    - FlowyML SDK (Pipeline, step, assets, schedulers, etc.)
    - Current notebook cells and their dependency graph
    - Available assets from the connected server
    - Experiment history and metrics
    """

    # FlowyML SDK context for the AI model
    FLOWYML_CONTEXT = """You are an AI assistant for FlowyML Notebook, a production-grade ML notebook.

FlowyML SDK Quick Reference:
- `@step(inputs=["x"], outputs=["y"])` — Define pipeline steps
- `Pipeline("name").add_step(fn)` — Build pipelines
- `Dataset.from_csv(path)`, `Dataset.from_dataframe(df)` — Create datasets
- `Model(obj, name="name")` — Wrap trained models
- `Metrics({"accuracy": 0.95})` — Record metrics
- `Experiment("name")` — Track experiments
- `evaluate(model, dataset, scorers=[...])` — Run evaluations
- `PipelineScheduler.schedule(pipeline, cron="...")` — Schedule pipelines
- `detect_drift(reference, current)` — Detect data drift
- `parallel_map(fn, items)` — Parallel execution

Widgets:
- `slider(min, max, value, label)` — Interactive slider
- `dropdown(options, label)` — Dropdown selector
- `table(data)`, `chart(data, x, y, kind)` — Data visualization
- `pipeline_dag(pipeline)` — Pipeline DAG viewer
- `metrics_dashboard(metrics)` — Metrics charts
- `leaderboard(experiments)` — Model comparison

Generate clean, idiomatic Python code. Use FlowyML abstractions when appropriate.
Provide brief explanations. Be concise and practical."""

    def __init__(self, notebook: Any = None, provider: str = "openai", model: str | None = None, base_url: str | None = None):
        self.notebook = notebook
        self._client = None
        self._provider = provider.lower()
        self._base_url = base_url
        # Set default model per provider
        if model:
            self._model = model
        elif self._provider == "ollama":
            self._model = "llama3.1"
        elif self._provider == "google":
            self._model = "gemini-pro"
        else:
            self._model = "gpt-4o-mini"

    def _get_client(self):
        """Lazily initialize AI client (OpenAI-compatible for all providers)."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "AI assistant requires the openai package. Install with: "
                    "pip install 'flowyml-notebook[ai]'"
                ) from None

            if self._provider == "ollama":
                base_url = self._base_url or "http://localhost:11434/v1"
                self._client = OpenAI(base_url=base_url, api_key="ollama")
            elif self._base_url:
                # Custom OpenAI-compatible endpoint
                self._client = OpenAI(base_url=self._base_url)
            else:
                # Standard OpenAI / Google AI
                self._client = OpenAI()
        return self._client

    def _build_context(self) -> str:
        """Build context string from current notebook state."""
        context_parts = [self.FLOWYML_CONTEXT]

        if self.notebook:
            # Add current cells
            cells_summary = []
            for i, cell in enumerate(self.notebook.cells):
                if cell.cell_type.value == "code" and cell.source.strip():
                    cells_summary.append(f"Cell {i + 1} ({cell.id}):\n```python\n{cell.source}\n```")
            if cells_summary:
                context_parts.append(
                    "\nCurrent notebook cells:\n" + "\n".join(cells_summary)
                )

            # Add variable info
            try:
                variables = self.notebook.session.get_variables()
                if variables:
                    var_summary = ", ".join(
                        f"{name}: {info['type']}" for name, info in list(variables.items())[:20]
                    )
                    context_parts.append(f"\nCurrent variables: {var_summary}")
            except Exception:
                pass

        return "\n".join(context_parts)

    def generate(self, prompt: str) -> AIResponse:
        """Generate code from a natural language description.

        Args:
            prompt: Natural language description of what to create.
                e.g., "Create a pipeline that loads CSV, trains XGBoost, and evaluates"

        Returns:
            AIResponse with generated code and explanation.
        """
        client = self._get_client()
        context = self._build_context()

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": f"Generate Python code for: {prompt}\n\nReturn ONLY the code in a ```python block, followed by a brief explanation."},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content or ""
        code = _extract_code_block(content)
        explanation = content.replace(f"```python\n{code}\n```", "").strip()

        return AIResponse(
            content=content,
            code=code,
            explanation=explanation,
            confidence=0.85,
        )

    def explain(self, code: str) -> AIResponse:
        """Explain what a piece of code does.

        Args:
            code: Python code to explain.

        Returns:
            AIResponse with explanation.
        """
        client = self._get_client()
        context = self._build_context()

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": f"Explain this code concisely:\n```python\n{code}\n```"},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        content = response.choices[0].message.content or ""
        return AIResponse(content=content, explanation=content, confidence=0.9)

    def debug(self, code: str, error: str) -> AIResponse:
        """Debug an error in code.

        Args:
            code: The code that produced the error.
            error: The error message/traceback.

        Returns:
            AIResponse with fix and explanation.
        """
        client = self._get_client()
        context = self._build_context()

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": (
                    f"Debug this code:\n```python\n{code}\n```\n\n"
                    f"Error:\n```\n{error}\n```\n\n"
                    "Provide the fixed code in a ```python block and explain the fix."
                )},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        content = response.choices[0].message.content or ""
        code_fix = _extract_code_block(content)
        explanation = content.replace(f"```python\n{code_fix}\n```", "").strip()

        return AIResponse(
            content=content,
            code=code_fix,
            explanation=explanation,
            suggestions=["Review the fix before running"],
            confidence=0.75,
        )

    def complete(self, code: str, cursor_pos: int | None = None) -> list[str]:
        """Get code completions for the current cursor position.

        Uses a combination of IPython completions and AI-powered suggestions.

        Args:
            code: Current code in the cell.
            cursor_pos: Cursor position in the code.

        Returns:
            List of completion suggestions.
        """
        completions = []

        # Try IPython completions first (fast)
        if self.notebook and self.notebook.session._ip:
            try:
                text = code[:cursor_pos] if cursor_pos else code
                _, matches = self.notebook.session._ip.complete(text)
                completions.extend(matches[:20])
            except Exception:
                pass

        # Add FlowyML-specific completions
        completions.extend(_flowyml_completions(code, cursor_pos))

        return list(dict.fromkeys(completions))[:30]  # Deduplicate, limit

    def chat(self, message: str) -> AIResponse:
        """Have a freeform conversation about the notebook.

        Args:
            message: User message.

        Returns:
            AIResponse.
        """
        client = self._get_client()
        context = self._build_context()

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": message},
            ],
            temperature=0.5,
            max_tokens=2000,
        )

        content = response.choices[0].message.content or ""
        code = _extract_code_block(content)
        return AIResponse(content=content, code=code, confidence=0.8)


def _extract_code_block(text: str) -> str:
    """Extract the first Python code block from markdown text."""
    import re
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic code block
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _flowyml_completions(code: str, cursor_pos: int | None) -> list[str]:
    """Get FlowyML-specific completion suggestions."""
    text = code[:cursor_pos] if cursor_pos else code
    last_word = text.split()[-1] if text.split() else ""

    completions = []

    # After 'from flowyml import '
    if "from flowyml import" in text:
        completions.extend([
            "Pipeline", "step", "context", "Context",
            "Dataset", "Model", "Metrics", "Prompt", "Checkpoint",
            "Experiment", "evaluate", "detect_drift",
            "parallel_map", "PipelineScheduler",
        ])

    # After 'nb.' or 'notebook.'
    elif last_word.endswith("nb.") or last_word.endswith("notebook."):
        completions.extend([
            "cell(", "run()", "save(", "load(", "connect(",
            "schedule(", "deploy(", "promote(", "report(",
            "viz.dag()", "viz.metrics()", "viz.drift()",
        ])

    # After '@'
    elif last_word == "@" or last_word.endswith("@"):
        completions.extend(["step(", "step(inputs=", "step(outputs="])

    # After 'Dataset.'
    elif "Dataset." in last_word:
        completions.extend([
            "from_csv(", "from_dataframe(", "from_dict(",
            "from_parquet(", "from_json(",
        ])

    return completions
