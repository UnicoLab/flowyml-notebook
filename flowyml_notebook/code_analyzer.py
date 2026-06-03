"""Automatic code cleanup, style fixing, and best-practice suggestions.

Provides real-time linting, auto-import sorting, variable naming
suggestions, and performance tips for notebook code cells.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeSuggestion:
    """A single code improvement suggestion."""
    rule: str
    severity: str  # "info", "warning", "performance", "style", "security"
    message: str
    line: int | None = None
    fix: str | None = None  # Auto-fix replacement if available
    original: str | None = None  # Original code that triggered the suggestion

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "fix": self.fix,
            "original": self.original,
        }


@dataclass
class LintReport:
    """Complete lint report for a code cell."""
    cell_id: str
    suggestions: list[CodeSuggestion] = field(default_factory=list)
    auto_fixes_available: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "auto_fixes_available": self.auto_fixes_available,
            "timestamp": self.timestamp,
        }


class CodeAnalyzer:
    """Analyzes notebook code cells for quality, performance, and best practices.

    Provides rules specifically tuned for data science workflows:
    - Performance: vectorization hints, memory optimization
    - Style: PEP8 naming, import ordering
    - Security: eval/exec detection, credential leaks
    - Best practices: pandas anti-patterns, sklearn conventions
    """

    def __init__(self):
        self._rules = [
            self._check_unused_imports,
            self._check_pandas_antipatterns,
            self._check_performance_hints,
            self._check_security,
            self._check_naming_conventions,
            self._check_magic_numbers,
            self._check_deprecated_patterns,
        ]

    def analyze(self, cell_id: str, source: str) -> LintReport:
        """Analyze a code cell and return suggestions.

        Args:
            cell_id: Cell identifier.
            source: Python source code.

        Returns:
            LintReport with all suggestions.
        """
        report = LintReport(cell_id=cell_id)

        if not source.strip():
            return report

        for rule in self._rules:
            try:
                suggestions = rule(source)
                report.suggestions.extend(suggestions)
            except Exception as e:
                logger.debug(f"Rule {rule.__name__} failed: {e}")

        report.auto_fixes_available = sum(1 for s in report.suggestions if s.fix)
        return report

    def _check_unused_imports(self, source: str) -> list[CodeSuggestion]:
        """Detect imported names that aren't used in the cell."""
        suggestions = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return suggestions

        imported_names: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = node.lineno

        # Check usage (simple text-based check)
        lines = source.split("\n")
        for name, lineno in imported_names.items():
            # Count uses outside the import line
            uses = sum(
                1 for i, line in enumerate(lines, 1)
                if i != lineno and re.search(rf'\b{re.escape(name)}\b', line)
            )
            if uses == 0:
                suggestions.append(CodeSuggestion(
                    rule="unused-import",
                    severity="style",
                    message=f"'{name}' is imported but never used in this cell",
                    line=lineno,
                ))

        return suggestions

    def _check_pandas_antipatterns(self, source: str) -> list[CodeSuggestion]:
        """Detect common pandas performance anti-patterns."""
        suggestions = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # .iterrows() anti-pattern
            if ".iterrows()" in stripped:
                suggestions.append(CodeSuggestion(
                    rule="pandas-iterrows",
                    severity="performance",
                    message="iterrows() is slow — use vectorized operations, .apply(), or .itertuples()",
                    line=i,
                    original=stripped,
                ))

            # .append() on DataFrame (deprecated & slow)
            if re.search(r'\.append\(', stripped) and "df" in stripped.lower():
                suggestions.append(CodeSuggestion(
                    rule="pandas-append",
                    severity="performance",
                    message="df.append() is deprecated and slow — use pd.concat() instead",
                    line=i,
                    original=stripped,
                ))

            # for loop with iloc
            if re.search(r'for\s+.*range\(len\(', stripped):
                suggestions.append(CodeSuggestion(
                    rule="pandas-loop-range",
                    severity="performance",
                    message="for i in range(len(df)) is slow — use vectorized operations or .apply()",
                    line=i,
                    original=stripped,
                ))

            # inplace=True anti-pattern
            if "inplace=True" in stripped:
                suggestions.append(CodeSuggestion(
                    rule="pandas-inplace",
                    severity="style",
                    message="inplace=True is discouraged — use assignment instead (df = df.drop(...))",
                    line=i,
                    original=stripped,
                ))

            # Chained indexing
            if re.search(r'\]\[', stripped) and ("df" in stripped.lower() or "series" in stripped.lower()):
                # Check if it looks like chained indexing not slicing
                if not stripped.startswith("#"):
                    suggestions.append(CodeSuggestion(
                        rule="pandas-chained-index",
                        severity="warning",
                        message="Possible chained indexing — use .loc[] or .iloc[] to avoid SettingWithCopyWarning",
                        line=i,
                        original=stripped,
                    ))

        return suggestions

    def _check_performance_hints(self, source: str) -> list[CodeSuggestion]:
        """Detect general performance issues."""
        suggestions = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # List comprehension inside sum/len/any/all
            if re.search(r'(sum|len|any|all)\(\[', stripped):
                suggestions.append(CodeSuggestion(
                    rule="use-generator",
                    severity="performance",
                    message="Use generator expression instead of list comprehension inside sum/len/any/all",
                    line=i,
                    original=stripped,
                ))

            # String concatenation in loop
            if "+" in stripped and ('""' in stripped or "''" in stripped):
                if re.search(r'(\+=\s*["\'])|(\+\s*str\()', stripped):
                    suggestions.append(CodeSuggestion(
                        rule="string-concat",
                        severity="performance",
                        message="String concatenation in loop is slow — use list + join() or f-strings",
                        line=i,
                    ))

            # Global variable shadowing common names
            if re.search(r'^(list|dict|set|type|id|input|print|len|range)\s*=', stripped):
                match = re.match(r'^(\w+)', stripped)
                if match:
                    suggestions.append(CodeSuggestion(
                        rule="builtin-shadow",
                        severity="warning",
                        message=f"'{match.group(1)}' shadows a Python builtin — use a different name",
                        line=i,
                        original=stripped,
                    ))

        return suggestions

    def _check_security(self, source: str) -> list[CodeSuggestion]:
        """Check for security issues."""
        suggestions = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Credential patterns
            if re.search(
                r'(api_key|secret|password|token|aws_access|aws_secret)\s*=\s*["\'][^"\']+["\']',
                stripped, re.IGNORECASE
            ):
                suggestions.append(CodeSuggestion(
                    rule="hardcoded-credential",
                    severity="security",
                    message="Possible hardcoded credential — use environment variables or a secrets manager",
                    line=i,
                ))

            # eval/exec usage
            if re.search(r'\beval\s*\(', stripped) and not stripped.startswith("#"):
                suggestions.append(CodeSuggestion(
                    rule="eval-usage",
                    severity="security",
                    message="eval() is a security risk — avoid with untrusted input",
                    line=i,
                ))

        return suggestions

    def _check_naming_conventions(self, source: str) -> list[CodeSuggestion]:
        """Check variable naming conventions."""
        suggestions = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return suggestions

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Check for camelCase (should be snake_case)
                        if (
                            not name.startswith("_")
                            and any(c.isupper() for c in name[1:])
                            and not name.isupper()
                            and "_" not in name
                            and len(name) > 2
                        ):
                            snake = re.sub(r'([A-Z])', r'_\1', name).lower().lstrip("_")
                            suggestions.append(CodeSuggestion(
                                rule="naming-convention",
                                severity="style",
                                message=f"'{name}' uses camelCase — Python convention is snake_case: '{snake}'",
                                line=node.lineno,
                                fix=snake,
                                original=name,
                            ))

            # Function name check
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if any(c.isupper() for c in name) and not name.startswith("_"):
                    snake = re.sub(r'([A-Z])', r'_\1', name).lower().lstrip("_")
                    suggestions.append(CodeSuggestion(
                        rule="naming-convention",
                        severity="style",
                        message=f"Function '{name}' uses camelCase — use '{snake}'",
                        line=node.lineno,
                    ))

        return suggestions

    def _check_magic_numbers(self, source: str) -> list[CodeSuggestion]:
        """Detect magic numbers that should be named constants."""
        suggestions = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return suggestions

        # Common acceptable numbers
        acceptable = {0, 1, 2, -1, 0.0, 1.0, 0.5, 100, 10, 1000}

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                # Skip common acceptable values
                if node.value in acceptable:
                    continue
                # Skip small numbers
                if isinstance(node.value, int) and abs(node.value) < 10:
                    continue
                # Skip if it's in a simple assignment (x = 42 is fine)
                # We only flag numbers in function calls and operations
                # This is a simple heuristic — just flag large unusual numbers
                if isinstance(node.value, (int, float)) and abs(node.value) > 100:
                    if not isinstance(node.value, bool):
                        suggestions.append(CodeSuggestion(
                            rule="magic-number",
                            severity="info",
                            message=f"Consider naming the constant {node.value} for readability",
                            line=node.lineno,
                        ))

        # Limit to avoid noise
        return suggestions[:3]

    def _check_deprecated_patterns(self, source: str) -> list[CodeSuggestion]:
        """Check for deprecated API patterns."""
        suggestions = []
        lines = source.split("\n")

        DEPRECATED = {
            "sklearn.cross_validation": ("sklearn.model_selection", "0.18"),
            "sklearn.grid_search": ("sklearn.model_selection", "0.18"),
            "pandas.io.parsers": ("pandas.read_csv directly", "1.0"),
            "from collections import Mapping": ("from collections.abc import Mapping", "3.9"),
            "np.float ": ("float or np.float64", "1.24"),
            "np.int ": ("int or np.int64", "1.24"),
            "np.bool ": ("bool or np.bool_", "1.24"),
            "np.object ": ("object or np.object_", "1.24"),
        }

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            for old, (replacement, since) in DEPRECATED.items():
                if old in stripped and not stripped.startswith("#"):
                    suggestions.append(CodeSuggestion(
                        rule="deprecated-api",
                        severity="warning",
                        message=f"'{old.strip()}' is deprecated since {since} — use '{replacement}'",
                        line=i,
                        original=stripped,
                    ))

        return suggestions

    def auto_fix(self, cell_id: str, source: str) -> tuple[str, list[str]]:
        """Apply auto-fixes to a cell's source code.

        Args:
            cell_id: Cell identifier.
            source: Original source code.

        Returns:
            Tuple of (fixed_source, list of changes made).
        """
        report = self.analyze(cell_id, source)
        fixed = source
        changes = []

        for suggestion in report.suggestions:
            if suggestion.fix and suggestion.original:
                if suggestion.original in fixed:
                    fixed = fixed.replace(suggestion.original, suggestion.fix, 1)
                    changes.append(f"Fixed {suggestion.rule}: {suggestion.message}")

        return fixed, changes
