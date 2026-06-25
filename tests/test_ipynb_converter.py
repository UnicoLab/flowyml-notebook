"""Tests for the .ipynb ↔ FlowyML notebook converter."""

import json

import pytest

from flowyml_notebook.cells import (
    CellOutput,
    CellType,
    NotebookFile,
    NotebookMetadata,
    serialize_notebook,
)
from flowyml_notebook.ipynb_converter import convert_file, from_ipynb, to_ipynb

# --- Sample .ipynb data for testing ---

MINIMAL_IPYNB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "cells": [],
}


def _make_ipynb_cell(cell_type="code", source="", outputs=None, execution_count=None, cell_id=None):
    """Helper to create a single .ipynb cell dict."""
    cell = {
        "cell_type": cell_type,
        "source": source,
        "metadata": {},
    }
    if cell_id:
        cell["id"] = cell_id
    if cell_type == "code":
        cell["outputs"] = outputs or []
        cell["execution_count"] = execution_count
    return cell


SAMPLE_IPYNB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11.5"},
    },
    "cells": [
        _make_ipynb_cell("markdown", "# My Analysis\n\nThis is a test notebook."),
        _make_ipynb_cell(
            "code",
            "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3]})",
            execution_count=1,
        ),
        _make_ipynb_cell(
            "code",
            "print(df.head())",
            outputs=[
                {"output_type": "stream", "name": "stdout", "text": "   a\n0  1\n1  2\n2  3\n"},
            ],
            execution_count=2,
        ),
        _make_ipynb_cell("markdown", "## Results\n\nLooks good!"),
        _make_ipynb_cell(
            "code",
            "df.describe()",
            outputs=[
                {
                    "output_type": "execute_result",
                    "data": {"text/plain": "         a\ncount  3.0\nmean   2.0"},
                    "metadata": {},
                    "execution_count": 3,
                },
            ],
            execution_count=3,
        ),
    ],
}


class TestFromIpynb:
    """Test importing .ipynb into FlowyML."""

    def test_import_empty_notebook(self):
        nb = from_ipynb(MINIMAL_IPYNB)
        assert isinstance(nb, NotebookFile)
        assert len(nb.cells) == 0
        assert nb.metadata.name == "Python 3"

    def test_import_sample_notebook(self):
        nb = from_ipynb(SAMPLE_IPYNB)
        assert len(nb.cells) == 5
        assert nb.cells[0].cell_type == CellType.MARKDOWN
        assert "My Analysis" in nb.cells[0].source
        assert nb.cells[1].cell_type == CellType.CODE
        assert "import pandas" in nb.cells[1].source
        assert nb.cells[1].execution_count == 1

    def test_import_preserves_outputs(self):
        nb = from_ipynb(SAMPLE_IPYNB)
        # Cell 2 (index 2) has stdout output
        cell = nb.cells[2]
        assert len(cell.outputs) > 0
        text_out = [o for o in cell.outputs if o.output_type == "text"]
        assert len(text_out) == 1
        assert "a" in text_out[0].data

    def test_import_execute_result(self):
        nb = from_ipynb(SAMPLE_IPYNB)
        # Cell 4 (index 4) has execute_result
        cell = nb.cells[4]
        assert len(cell.outputs) > 0

    def test_import_source_as_list(self):
        """ipynb stores source as list of lines sometimes."""
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell("code", ["x = 1\n", "y = 2\n"]),
            ],
        }
        nb = from_ipynb(ipynb)
        assert nb.cells[0].source == "x = 1\ny = 2"

    def test_import_sql_magic_cell(self):
        """%%sql magic cells should become SQL cell type."""
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell("code", "%%sql\nSELECT * FROM users WHERE age > 21"),
            ],
        }
        nb = from_ipynb(ipynb)
        assert nb.cells[0].cell_type == CellType.SQL
        assert "SELECT * FROM users" in nb.cells[0].source
        assert "%%sql" not in nb.cells[0].source

    def test_import_raw_cell(self):
        """Raw cells should become commented code cells."""
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell("raw", "This is raw text\nSecond line"),
            ],
        }
        nb = from_ipynb(ipynb)
        assert nb.cells[0].cell_type == CellType.CODE
        assert nb.cells[0].source.startswith("# This is raw text")

    def test_import_error_output(self):
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell(
                    "code",
                    "1/0",
                    outputs=[
                        {
                            "output_type": "error",
                            "ename": "ZeroDivisionError",
                            "evalue": "division by zero",
                            "traceback": ["ZeroDivisionError: division by zero"],
                        },
                    ],
                ),
            ],
        }
        nb = from_ipynb(ipynb)
        assert len(nb.cells[0].outputs) == 1
        assert nb.cells[0].outputs[0].output_type == "error"
        assert "ZeroDivisionError" in nb.cells[0].outputs[0].data

    def test_import_html_output(self):
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell(
                    "code",
                    "display(HTML('<b>Hello</b>'))",
                    outputs=[
                        {
                            "output_type": "display_data",
                            "data": {"text/html": "<b>Hello</b>", "text/plain": "Hello"},
                            "metadata": {},
                        },
                    ],
                ),
            ],
        }
        nb = from_ipynb(ipynb)
        assert nb.cells[0].outputs[0].output_type == "html"
        assert "<b>Hello</b>" in nb.cells[0].outputs[0].data

    def test_import_image_output(self):
        ipynb = {
            **MINIMAL_IPYNB,
            "cells": [
                _make_ipynb_cell(
                    "code",
                    "plt.plot([1,2,3])",
                    outputs=[
                        {
                            "output_type": "display_data",
                            "data": {"image/png": "iVBOR==", "text/plain": "<Figure>"},
                            "metadata": {},
                        },
                    ],
                ),
            ],
        }
        nb = from_ipynb(ipynb)
        assert nb.cells[0].outputs[0].output_type == "image"
        assert "base64" in nb.cells[0].outputs[0].data

    def test_reject_old_format(self):
        with pytest.raises(ValueError, match="Unsupported nbformat"):
            from_ipynb({"nbformat": 3, "cells": []})

    def test_import_from_dict(self):
        nb = from_ipynb(MINIMAL_IPYNB)
        assert isinstance(nb, NotebookFile)


class TestToIpynb:
    """Test exporting FlowyML to .ipynb."""

    def test_export_empty_notebook(self):
        nb = NotebookFile()
        ipynb = to_ipynb(nb)
        assert ipynb["nbformat"] == 4
        assert ipynb["nbformat_minor"] == 5
        assert ipynb["cells"] == []
        assert "kernelspec" in ipynb["metadata"]

    def test_export_code_cell(self):
        nb = NotebookFile()
        nb.add_cell("x = 42", CellType.CODE, "setup")
        ipynb = to_ipynb(nb)
        assert len(ipynb["cells"]) == 1
        assert ipynb["cells"][0]["cell_type"] == "code"
        assert ipynb["cells"][0]["source"] == "x = 42"

    def test_export_markdown_cell(self):
        nb = NotebookFile()
        nb.add_cell("## Title\nSome text", CellType.MARKDOWN)
        ipynb = to_ipynb(nb)
        assert ipynb["cells"][0]["cell_type"] == "markdown"
        assert "## Title" in ipynb["cells"][0]["source"]

    def test_export_sql_cell(self):
        """SQL cells should export as code cells with %%sql magic."""
        nb = NotebookFile()
        nb.add_cell("SELECT * FROM users", CellType.SQL)
        ipynb = to_ipynb(nb)
        cell = ipynb["cells"][0]
        assert cell["cell_type"] == "code"
        assert cell["source"].startswith("%%sql")
        assert "SELECT * FROM users" in cell["source"]

    def test_export_without_outputs(self):
        nb = NotebookFile()
        cell = nb.add_cell("x = 1", CellType.CODE)
        cell.outputs = [CellOutput(output_type="text", data="hello")]
        ipynb = to_ipynb(nb, include_outputs=False)
        assert ipynb["cells"][0]["outputs"] == []

    def test_export_with_outputs(self):
        nb = NotebookFile()
        cell = nb.add_cell("print('hi')", CellType.CODE)
        cell.outputs = [CellOutput(output_type="text", data="hi\n")]
        ipynb = to_ipynb(nb, include_outputs=True)
        assert len(ipynb["cells"][0]["outputs"]) == 1
        assert ipynb["cells"][0]["outputs"][0]["output_type"] == "stream"

    def test_export_preserves_metadata(self):
        nb = NotebookFile(
            metadata=NotebookMetadata(
                name="My Notebook",
                description="Test",
                author="Alice",
                tags=["ml", "test"],
            )
        )
        ipynb = to_ipynb(nb)
        flowyml_meta = ipynb["metadata"]["flowyml"]
        assert flowyml_meta["name"] == "My Notebook"
        assert flowyml_meta["author"] == "Alice"
        assert "ml" in flowyml_meta["tags"]


class TestRoundTrip:
    """Test .ipynb → FlowyML → .ipynb preserves essential data."""

    def test_roundtrip_basic(self):
        nb = from_ipynb(SAMPLE_IPYNB)
        exported = to_ipynb(nb)

        assert len(exported["cells"]) == len(SAMPLE_IPYNB["cells"])

        # Check cell types match
        for orig, exp in zip(SAMPLE_IPYNB["cells"], exported["cells"]):
            assert orig["cell_type"] == exp["cell_type"]

    def test_roundtrip_source_preserved(self):
        nb = from_ipynb(SAMPLE_IPYNB)
        exported = to_ipynb(nb)

        # Code cell sources should be identical
        for orig, exp in zip(SAMPLE_IPYNB["cells"], exported["cells"]):
            orig_source = orig["source"]
            exp_source = exp["source"]
            if isinstance(orig_source, list):
                orig_source = "".join(orig_source).rstrip("\n")
            else:
                orig_source = orig_source.rstrip("\n")
            exp_source = exp_source.rstrip("\n")
            assert orig_source == exp_source

    def test_roundtrip_flowyml_to_ipynb(self):
        """FlowyML .py → .ipynb → FlowyML .py preserves cells."""
        # Create a FlowyML notebook
        nb = NotebookFile(metadata=NotebookMetadata(name="test"))
        nb.add_cell("import pandas as pd", CellType.CODE, "imports")
        nb.add_cell("## Analysis", CellType.MARKDOWN)
        nb.add_cell("df = pd.read_csv('data.csv')", CellType.CODE, "load")

        # Export to ipynb
        ipynb = to_ipynb(nb)
        # Re-import
        nb2 = from_ipynb(ipynb)

        assert len(nb2.cells) == 3
        assert nb2.cells[0].cell_type == CellType.CODE
        assert nb2.cells[1].cell_type == CellType.MARKDOWN
        assert nb2.cells[2].cell_type == CellType.CODE
        assert "import pandas" in nb2.cells[0].source
        assert "## Analysis" in nb2.cells[1].source

    def test_roundtrip_sql_cell(self):
        """SQL cells survive FlowyML → .ipynb → FlowyML round-trip."""
        nb = NotebookFile()
        nb.add_cell("SELECT * FROM users", CellType.SQL)
        ipynb = to_ipynb(nb)
        nb2 = from_ipynb(ipynb)
        assert nb2.cells[0].cell_type == CellType.SQL
        assert "SELECT * FROM users" in nb2.cells[0].source


class TestConvertFile:
    """Test the file conversion helper."""

    def test_ipynb_to_py(self, tmp_path):
        # Create a .ipynb file
        ipynb_path = tmp_path / "test.ipynb"
        ipynb_path.write_text(json.dumps(SAMPLE_IPYNB), encoding="utf-8")

        # Convert
        output = convert_file(ipynb_path)
        assert output.endswith(".py")

        # Verify it's valid percent format
        content = (tmp_path / "test.py").read_text(encoding="utf-8")
        assert "# /// flowyml-notebook" in content
        assert "# %%" in content

    def test_py_to_ipynb(self, tmp_path):
        # Create a FlowyML .py file
        nb = NotebookFile(metadata=NotebookMetadata(name="test"))
        nb.add_cell("x = 42", CellType.CODE)
        nb.add_cell("## Title", CellType.MARKDOWN)

        py_path = tmp_path / "test.py"
        py_path.write_text(serialize_notebook(nb), encoding="utf-8")

        # Convert
        output = convert_file(py_path)
        assert output.endswith(".ipynb")

        # Verify it's valid JSON
        ipynb = json.loads((tmp_path / "test.ipynb").read_text(encoding="utf-8"))
        assert ipynb["nbformat"] == 4
        assert len(ipynb["cells"]) == 2

    def test_custom_output_path(self, tmp_path):
        ipynb_path = tmp_path / "input.ipynb"
        ipynb_path.write_text(json.dumps(MINIMAL_IPYNB), encoding="utf-8")
        output_path = tmp_path / "custom_output.py"

        result = convert_file(ipynb_path, output_path)
        assert result == str(output_path)
        assert output_path.exists()

    def test_unsupported_extension(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            convert_file(txt_path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            convert_file("/nonexistent/path/notebook.ipynb")
