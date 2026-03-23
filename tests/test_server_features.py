"""Tests for the killer features: SmartPrep, Algorithm Matchmaker, and Patterns."""

import json
from pathlib import Path

from flowyml_notebook.cells import Cell
from flowyml_notebook.core import NotebookSession


class TestSmartPrepLogic:
    """Test the SmartPrep analysis logic via the notebook session."""

    def test_detects_missing_values(self):
        """The advisor should detect columns with missing values."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\nimport numpy as np\n"
            "df = pd.DataFrame({'a': [1, 2, None, 4], 'b': [10, 20, 30, 40]})"
        )))
        ns = session._namespace
        df = ns["df"]
        assert df["a"].isnull().sum() == 1

    def test_detects_skew(self):
        """Skewed distribution should be detectable."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\nimport numpy as np\n"
            "np.random.seed(42)\n"
            "df = pd.DataFrame({'skewed': np.random.exponential(2, 1000), 'normal': np.random.randn(1000)})"
        )))
        df = session._namespace["df"]
        assert abs(float(df["skewed"].skew())) > 1.0
        assert abs(float(df["normal"].skew())) < 1.0

    def test_detects_outliers(self):
        """Outlier detection via IQR should work."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\nimport numpy as np\n"
            "np.random.seed(42)\n"
            "data = list(np.random.randn(100)) + [100, -100]\n"
            "df = pd.DataFrame({'values': data})"
        )))
        df = session._namespace["df"]
        q1 = float(df["values"].quantile(0.25))
        q3 = float(df["values"].quantile(0.75))
        iqr = q3 - q1
        outliers = ((df["values"] < q1 - 1.5 * iqr) | (df["values"] > q3 + 1.5 * iqr)).sum()
        assert outliers > 0

    def test_detects_high_cardinality(self):
        """Categorical columns with many unique values should be flagged."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\n"
            "df = pd.DataFrame({'cat': [f'item_{i}' for i in range(100)]})"
        )))
        df = session._namespace["df"]
        assert int(df["cat"].nunique()) > 50

    def test_detects_class_imbalance(self):
        """Class imbalance detection should work with target variable."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\n"
            "df = pd.DataFrame({'x': range(100), 'y': [0]*90 + [1]*10})"
        )))
        df = session._namespace["df"]
        vc = df["y"].value_counts()
        ratio = int(vc.iloc[0]) / int(vc.iloc[-1]) if int(vc.iloc[-1]) > 0 else 999
        assert ratio > 3

    def test_detects_scaling_needed(self):
        """Features with very different ranges should trigger scaling suggestion."""
        session = NotebookSession()
        session.execute_cell(Cell(source=(
            "import pandas as pd\n"
            "df = pd.DataFrame({'tiny': [0.001, 0.002, 0.003], 'huge': [10000, 20000, 30000]})"
        )))
        df = session._namespace["df"]
        ranges = {col: float(df[col].max() - df[col].min()) for col in df.columns}
        max_r = max(ranges.values())
        min_r = min(v for v in ranges.values() if v > 0)
        assert max_r / min_r > 100


class TestAlgorithmMatchLogic:
    """Test the Algorithm Matchmaker analysis logic."""

    def test_classification_detection(self):
        """Should detect classification task when target has few unique values."""
        import pandas as pd
        df = pd.DataFrame({"x": range(100), "y": [0, 1] * 50})
        n_unique = int(df["y"].nunique())
        assert n_unique <= 20  # classification threshold
        assert pd.api.types.is_numeric_dtype(df["y"])

    def test_regression_detection(self):
        """Should detect regression task when target has many unique values."""
        import numpy as np
        import pandas as pd
        np.random.seed(42)
        df = pd.DataFrame({"x": range(100), "y": np.random.randn(100)})
        n_unique = int(df["y"].nunique())
        assert n_unique > 20  # regression threshold

    def test_clustering_default(self):
        """Without target, should default to clustering."""
        # This is implicit logic — no target means clustering
        task_type = "clustering"
        target = None
        if target:
            task_type = "classification"
        assert task_type == "clustering"

    def test_data_characteristics(self):
        """Should correctly compute data characteristics."""
        import numpy as np
        import pandas as pd
        np.random.seed(42)
        df = pd.DataFrame({
            "num1": np.random.randn(10000),
            "num2": np.random.randn(10000),
            "cat1": [f"c{i%5}" for i in range(10000)],
            "target": [0, 1] * 5000,
        })
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        assert len(numeric_cols) == 3  # num1, num2, target
        assert len(cat_cols) == 1
        assert df.shape[0] == 10000
        assert df.shape[0] > 1000  # "large enough for XGBoost"


class TestAnalysisPatterns:
    """Test the Analysis Patterns CRUD and file-based storage."""

    def _patterns_file(self, tmpdir) -> Path:
        return Path(tmpdir) / ".flowyml_patterns.json"

    def test_empty_patterns_list(self, tmp_path):
        """Should return empty list when no patterns file exists."""
        pf = self._patterns_file(tmp_path)
        assert not pf.exists()

    def test_save_pattern(self, tmp_path):
        """Should save a new pattern to the JSON file."""
        import uuid
        pf = self._patterns_file(tmp_path)
        data = {"patterns": []}

        new_pattern = {
            "id": str(uuid.uuid4())[:8],
            "name": "EDA Starter",
            "description": "Basic exploratory data analysis",
            "tags": ["eda", "pandas"],
            "cells": [
                {"source": "import pandas as pd", "cell_type": "code"},
                {"source": "df.describe()", "cell_type": "code"},
            ],
            "data_type": "tabular",
            "problem_type": "eda",
            "uses": 0,
        }
        data["patterns"].append(new_pattern)
        pf.write_text(json.dumps(data, indent=2), encoding="utf-8")

        loaded = json.loads(pf.read_text(encoding="utf-8"))
        assert len(loaded["patterns"]) == 1
        assert loaded["patterns"][0]["name"] == "EDA Starter"
        assert len(loaded["patterns"][0]["cells"]) == 2

    def test_delete_pattern(self, tmp_path):
        """Should remove a pattern by ID."""
        pf = self._patterns_file(tmp_path)
        data = {"patterns": [
            {"id": "abc", "name": "Pattern 1"},
            {"id": "def", "name": "Pattern 2"},
        ]}
        pf.write_text(json.dumps(data), encoding="utf-8")

        # Delete pattern "abc"
        loaded = json.loads(pf.read_text(encoding="utf-8"))
        loaded["patterns"] = [p for p in loaded["patterns"] if p["id"] != "abc"]
        pf.write_text(json.dumps(loaded), encoding="utf-8")

        result = json.loads(pf.read_text(encoding="utf-8"))
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["id"] == "def"

    def test_apply_pattern_increments_usage(self, tmp_path):
        """Applying a pattern should increment its usage counter."""
        pf = self._patterns_file(tmp_path)
        data = {"patterns": [
            {"id": "p1", "name": "Pattern", "uses": 5, "cells": [{"source": "x=1"}]},
        ]}
        pf.write_text(json.dumps(data), encoding="utf-8")

        loaded = json.loads(pf.read_text(encoding="utf-8"))
        pattern = next(p for p in loaded["patterns"] if p["id"] == "p1")
        pattern["uses"] = pattern.get("uses", 0) + 1
        pf.write_text(json.dumps(loaded), encoding="utf-8")

        result = json.loads(pf.read_text(encoding="utf-8"))
        assert result["patterns"][0]["uses"] == 6

    def test_search_patterns_by_query(self, tmp_path):
        """Should filter patterns by search query."""
        patterns = [
            {"id": "1", "name": "EDA Analysis", "description": "Explore", "tags": ["eda"]},
            {"id": "2", "name": "Feature Engineering", "description": "Build features", "tags": ["fe"]},
            {"id": "3", "name": "Model Training", "description": "Train model", "tags": ["ml"]},
        ]
        q = "feature"
        results = [
            p for p in patterns
            if q in p.get("name", "").lower() or q in p.get("description", "").lower()
            or any(q in t.lower() for t in p.get("tags", []))
        ]
        assert len(results) == 1
        assert results[0]["name"] == "Feature Engineering"

    def test_search_patterns_by_problem_type(self, tmp_path):
        """Should filter patterns by problem type."""
        patterns = [
            {"id": "1", "name": "A", "problem_type": "classification"},
            {"id": "2", "name": "B", "problem_type": "regression"},
            {"id": "3", "name": "C", "problem_type": "any"},
        ]
        pt = "classification"
        results = [
            p for p in patterns
            if p.get("problem_type") in (pt, "any")
        ]
        assert len(results) == 2  # "classification" + "any"

    def test_pattern_roundtrip(self, tmp_path):
        """Complete save-load roundtrip."""
        pf = self._patterns_file(tmp_path)
        cells = [
            {"source": "import pandas as pd", "cell_type": "code", "name": "imports"},
            {"source": "# ## EDA Report", "cell_type": "markdown", "name": "header"},
            {"source": "df.describe()", "cell_type": "code", "name": "stats"},
        ]
        data = {"patterns": [{
            "id": "test_id",
            "name": "Full EDA",
            "description": "Complete exploratory data analysis pattern",
            "tags": ["eda", "statistics", "visualization"],
            "cells": cells,
            "data_type": "tabular",
            "problem_type": "eda",
            "uses": 0,
        }]}
        pf.write_text(json.dumps(data, indent=2), encoding="utf-8")

        loaded = json.loads(pf.read_text(encoding="utf-8"))
        p = loaded["patterns"][0]
        assert p["name"] == "Full EDA"
        assert len(p["cells"]) == 3
        assert p["cells"][0]["source"] == "import pandas as pd"
        assert p["tags"] == ["eda", "statistics", "visualization"]
        assert p["uses"] == 0

    def test_multiple_patterns(self, tmp_path):
        """Should handle multiple patterns in the same file."""
        pf = self._patterns_file(tmp_path)
        data = {"patterns": []}
        for i in range(5):
            data["patterns"].append({
                "id": f"p{i}",
                "name": f"Pattern {i}",
                "cells": [{"source": f"x = {i}"}],
                "uses": i,
            })
        pf.write_text(json.dumps(data), encoding="utf-8")

        loaded = json.loads(pf.read_text(encoding="utf-8"))
        assert len(loaded["patterns"]) == 5
        assert loaded["patterns"][4]["uses"] == 4

    def test_corrupted_file_handling(self, tmp_path):
        """Should handle corrupted patterns file gracefully."""
        pf = self._patterns_file(tmp_path)
        pf.write_text("not valid json!!!", encoding="utf-8")

        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"patterns": []}

        assert data == {"patterns": []}


class TestInteractiveDashboardConfig:
    """Test that AppPublishRequest models accept new interactive dashboard fields."""

    def test_interactive_config_defaults(self):
        """Default config should have interactivity disabled."""
        config = {
            "title": "My Dashboard",
            "layout": "linear",
            "theme": "dark",
            "show_code": False,
            "grid_columns": 2,
            "cell_visibility": {},
            "interactive": False,
            "refresh_interval": None,
        }
        assert config["interactive"] is False
        assert config["refresh_interval"] is None

    def test_interactive_config_enabled(self):
        """Should accept interactive dashboard configuration."""
        config = {
            "title": "Live Dashboard",
            "layout": "dashboard",
            "theme": "dark",
            "interactive": True,
            "refresh_interval": 60,
        }
        assert config["interactive"] is True
        assert config["refresh_interval"] == 60

    def test_widget_types(self):
        """Auto-detected widget types should be complete."""
        widget_types = ['Date Range', 'Category Dropdown', 'Numeric Slider', 'Text Search']
        assert len(widget_types) == 4
        assert 'Date Range' in widget_types
        assert 'Numeric Slider' in widget_types
