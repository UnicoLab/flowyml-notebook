"""Tests for the killer features: benchmark, data_validator, code_analyzer, execution_history."""

import pytest
from flowyml_notebook.cells import Cell, CellOutput, CellType, NotebookFile, NotebookMetadata


class TestCellBenchmark:
    """Test the cell benchmarking module."""

    def test_benchmark_basic(self):
        from flowyml_notebook.benchmark import CellBenchmark

        bm = CellBenchmark()
        result = bm.benchmark("c1", "x = sum(range(100))", {}, runs=3, warmup=0)

        assert result.cell_id == "c1"
        assert result.runs == 3
        assert result.mean_s > 0
        assert result.median_s > 0
        assert result.min_s <= result.mean_s <= result.max_s
        assert len(result.all_times) == 3

    def test_benchmark_history(self):
        from flowyml_notebook.benchmark import CellBenchmark

        bm = CellBenchmark()
        bm.benchmark("c1", "x = 1", {}, runs=3, warmup=0)
        bm.benchmark("c1", "x = 1", {}, runs=3, warmup=0)

        history = bm.get_history("c1")
        assert len(history) == 2

    def test_benchmark_regression_detection(self):
        from flowyml_notebook.benchmark import CellBenchmark, BenchmarkResult

        bm = CellBenchmark()
        # Simulate fast then slow
        bm._history["c1"] = [
            BenchmarkResult(cell_id="c1", runs=3, mean_s=0.001),
            BenchmarkResult(cell_id="c1", runs=3, mean_s=0.010),
        ]

        regressions = bm.detect_regressions("c1", threshold_pct=25.0)
        assert len(regressions) == 1
        assert regressions[0].severity in ("warning", "critical")
        assert regressions[0].change_pct > 25.0

    def test_benchmark_to_dict(self):
        from flowyml_notebook.benchmark import BenchmarkResult

        result = BenchmarkResult(cell_id="c1", runs=5, mean_s=0.123456)
        d = result.to_dict()
        assert d["cell_id"] == "c1"
        assert d["runs"] == 5
        assert isinstance(d["mean_s"], float)

    def test_format_benchmark_output(self):
        from flowyml_notebook.benchmark import BenchmarkResult, format_benchmark_output

        result = BenchmarkResult(
            cell_id="c1", runs=5, mean_s=0.05,
            median_s=0.04, std_s=0.01, min_s=0.03, max_s=0.08,
            all_times=[0.03, 0.04, 0.04, 0.05, 0.08],
        )
        output = format_benchmark_output(result)
        assert output.output_type == "html"
        assert "Benchmark" in output.data
        assert "ms" in output.data


class TestDataValidator:
    """Test the automatic data quality validator."""

    def test_validate_clean_dataframe(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)

        assert report.var_name == "df"
        assert report.shape == (3, 2)
        assert report.overall_score > 50
        assert len(report.columns) == 2

    def test_validate_nulls_detected(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        df = pd.DataFrame({"a": [1, None, None, None, 5]})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)

        col = report.columns[0]
        assert col.null_count == 3
        assert col.null_pct == 60.0
        assert len(col.issues) > 0
        assert report.overall_score < 100

    def test_validate_duplicates_detected(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        df = pd.DataFrame({"a": [1, 1, 2, 2, 3]})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)

        assert report.duplicate_rows == 2
        assert len(report.warnings) > 0

    def test_validate_constant_column(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        df = pd.DataFrame({"a": [1, 1, 1, 1, 1]})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)

        col = report.columns[0]
        assert col.unique_count == 1
        assert any("Constant" in issue for issue in col.issues)

    def test_validate_empty_dataframe(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        df = pd.DataFrame({"a": []})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)

        assert report.shape == (0, 1)
        assert any("empty" in w for w in report.warnings)

    def test_validate_namespace(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        ns = {
            "df": pd.DataFrame({"a": [1, 2, 3]}),
            "x": 42,  # Not a DataFrame, should be ignored
            "_private": pd.DataFrame({"b": [1]}),  # Private, should be ignored
        }
        validator = DataValidator()
        reports = validator.validate_namespace("c1", ns)

        assert len(reports) == 1
        assert reports[0].var_name == "df"

    def test_format_quality_output(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator, format_quality_output

        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", "z"]})
        validator = DataValidator()
        report = validator.validate("df", "c1", df)
        output = format_quality_output(report)

        assert output.output_type == "html"
        assert "Data Quality" in output.data

    def test_get_reports(self):
        import pandas as pd
        from flowyml_notebook.data_validator import DataValidator

        validator = DataValidator()
        df = pd.DataFrame({"a": [1, 2, 3]})
        validator.validate("df", "c1", df)
        validator.validate("df", "c2", df)

        reports = validator.get_reports("df")
        assert len(reports) == 2

        latest = validator.get_latest_report("df")
        assert latest is not None
        assert latest["cell_id"] == "c2"


class TestCodeAnalyzer:
    """Test the smart code analyzer."""

    def test_unused_import_detection(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "import pandas as pd\nx = 42")

        rules = [s.rule for s in report.suggestions]
        assert "unused-import" in rules

    def test_pandas_iterrows_antipattern(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "for idx, row in df.iterrows():\n    print(row)")

        rules = [s.rule for s in report.suggestions]
        assert "pandas-iterrows" in rules

    def test_pandas_inplace_antipattern(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "df.drop('col', inplace=True)")

        rules = [s.rule for s in report.suggestions]
        assert "pandas-inplace" in rules

    def test_security_hardcoded_credential(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", 'api_key = "sk-abc123xyz"')

        rules = [s.rule for s in report.suggestions]
        assert "hardcoded-credential" in rules

    def test_builtin_shadow(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "list = [1, 2, 3]")

        rules = [s.rule for s in report.suggestions]
        assert "builtin-shadow" in rules

    def test_clean_code_no_issues(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "x = 42\ny = x + 1\nprint(y)")

        # Should have minimal/no issues
        critical = [s for s in report.suggestions if s.severity in ("security", "warning")]
        assert len(critical) == 0

    def test_naming_convention_detection(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "myVariableName = 42")

        rules = [s.rule for s in report.suggestions]
        assert "naming-convention" in rules
        # Check that fix is suggested
        naming = [s for s in report.suggestions if s.rule == "naming-convention"]
        assert naming[0].fix is not None

    def test_deprecated_api(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        report = analyzer.analyze("c1", "from collections import Mapping")

        rules = [s.rule for s in report.suggestions]
        assert "deprecated-api" in rules

    def test_auto_fix(self):
        from flowyml_notebook.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        fixed, changes = analyzer.auto_fix("c1", "myVarName = 42")

        # Should have applied naming fix
        assert "my_var_name" in fixed or len(changes) > 0


class TestExecutionHistory:
    """Test the execution history and time-travel debugging."""

    def test_record_and_retrieve(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 42", success=True, duration_s=0.05)

        timeline = history.get_timeline("c1")
        assert timeline is not None
        assert timeline["total_executions"] == 1

    def test_multiple_records(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True, duration_s=0.01)
        history.record("c1", "x = 2", success=True, duration_s=0.02)
        history.record("c1", "x = 3", success=False, duration_s=0.03)

        timeline = history.get_timeline("c1")
        assert timeline["total_executions"] == 3

    def test_compare_runs(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True, duration_s=0.01)
        history.record("c1", "x = 2", success=True, duration_s=0.05)

        comparison = history.compare_runs("c1")
        assert comparison is not None
        assert comparison["source_changed"] is True
        assert comparison["duration_delta_s"] > 0

    def test_get_snapshot(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 42", success=True)

        snap = history.get_snapshot("c1", -1)
        assert snap is not None
        assert snap["source"] == "x = 42"
        assert snap["success"] is True

    def test_global_log(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True, duration_s=0.01)
        history.record("c2", "y = 2", success=True, duration_s=0.02)

        log = history.get_global_log()
        assert len(log) == 2

    def test_execution_stats(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True, duration_s=0.01)
        history.record("c2", "y = 2", success=False, duration_s=0.02)

        stats = history.get_execution_stats()
        assert stats["total_executions"] == 2
        assert stats["total_cells_executed"] == 2
        assert stats["total_failures"] == 1
        assert stats["success_rate_pct"] == 50.0

    def test_clear_specific_cell(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True)
        history.record("c2", "y = 2", success=True)

        history.clear("c1")
        assert history.get_timeline("c1") is None
        assert history.get_timeline("c2") is not None

    def test_max_snapshots_limit(self):
        from flowyml_notebook.execution_history import ExecutionHistory

        history = ExecutionHistory(max_snapshots=5)
        for i in range(10):
            history.record("c1", f"x = {i}", success=True)

        timeline = history.get_timeline("c1")
        assert timeline["total_executions"] == 5  # Trimmed to limit

    def test_format_timeline_output(self):
        from flowyml_notebook.execution_history import ExecutionHistory, format_timeline_output

        history = ExecutionHistory()
        history.record("c1", "x = 1", success=True, duration_s=0.01, execution_count=1)
        history.record("c1", "x = 2", success=False, duration_s=0.02, execution_count=2)

        timeline = history.get_timeline("c1")
        output = format_timeline_output(timeline)
        assert output.output_type == "html"
        assert "History" in output.data
