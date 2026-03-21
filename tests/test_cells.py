"""Tests for the cell model and .py file format parser."""

import pytest
from flowyml_notebook.cells import (
    Cell,
    CellType,
    CellOutput,
    NotebookFile,
    NotebookMetadata,
    serialize_notebook,
    parse_notebook,
)


class TestCell:
    """Test the Cell dataclass."""

    def test_create_default(self):
        cell = Cell()
        assert cell.cell_type == CellType.CODE
        assert cell.source == ""
        assert cell.outputs == []
        assert cell.execution_count == 0
        assert len(cell.id) == 8

    def test_create_with_params(self):
        cell = Cell(id="abc", cell_type=CellType.MARKDOWN, source="# Hello", name="intro")
        assert cell.id == "abc"
        assert cell.cell_type == CellType.MARKDOWN
        assert cell.source == "# Hello"
        assert cell.name == "intro"

    def test_to_dict(self):
        cell = Cell(id="abc", source="x = 1")
        d = cell.to_dict()
        assert d["id"] == "abc"
        assert d["cell_type"] == "code"
        assert d["source"] == "x = 1"

    def test_from_dict(self):
        d = {"id": "xyz", "cell_type": "sql", "source": "SELECT *", "name": "query"}
        cell = Cell.from_dict(d)
        assert cell.id == "xyz"
        assert cell.cell_type == CellType.SQL
        assert cell.source == "SELECT *"
        assert cell.name == "query"


class TestNotebookFile:
    """Test the NotebookFile dataclass."""

    def test_create_empty(self):
        nb = NotebookFile()
        assert nb.cells == []
        assert nb.metadata.name == "untitled"

    def test_add_cell(self):
        nb = NotebookFile()
        cell = nb.add_cell("x = 1", CellType.CODE, "setup")
        assert len(nb.cells) == 1
        assert nb.cells[0].source == "x = 1"
        assert nb.cells[0].name == "setup"

    def test_remove_cell(self):
        nb = NotebookFile()
        cell = nb.add_cell("x = 1")
        assert nb.remove_cell(cell.id) is True
        assert len(nb.cells) == 0
        assert nb.remove_cell("nonexistent") is False

    def test_move_cell(self):
        nb = NotebookFile()
        c1 = nb.add_cell("x = 1")
        c2 = nb.add_cell("y = 2")
        c3 = nb.add_cell("z = 3")
        nb.move_cell(c3.id, 0)
        assert nb.cells[0].id == c3.id
        assert nb.cells[1].id == c1.id
        assert nb.cells[2].id == c2.id

    def test_get_cell(self):
        nb = NotebookFile()
        cell = nb.add_cell("x = 1")
        assert nb.get_cell(cell.id) is cell
        assert nb.get_cell("nonexistent") is None

    def test_to_dict_from_dict(self):
        nb = NotebookFile(metadata=NotebookMetadata(name="test", version=2))
        nb.add_cell("x = 1", CellType.CODE, "setup")
        nb.add_cell("# Hello", CellType.MARKDOWN)

        d = nb.to_dict()
        restored = NotebookFile.from_dict(d)
        assert restored.metadata.name == "test"
        assert restored.metadata.version == 2
        assert len(restored.cells) == 2
        assert restored.cells[0].cell_type == CellType.CODE
        assert restored.cells[1].cell_type == CellType.MARKDOWN


class TestSerializeParseRoundTrip:
    """Test the .py file format serialization and parsing."""

    def test_empty_notebook(self):
        nb = NotebookFile(metadata=NotebookMetadata(name="test"))
        text = serialize_notebook(nb)
        assert "# /// flowyml-notebook" in text
        assert "# name: test" in text

        restored = parse_notebook(text)
        assert restored.metadata.name == "test"
        assert len(restored.cells) == 0

    def test_code_cell_roundtrip(self):
        nb = NotebookFile()
        nb.add_cell("x = 42\nprint(x)", CellType.CODE, "setup", "abc123")
        text = serialize_notebook(nb)

        assert "# %% [code] id=abc123" in text
        assert "x = 42" in text
        assert "print(x)" in text

        restored = parse_notebook(text)
        assert len(restored.cells) == 1
        assert restored.cells[0].id == "abc123"
        assert restored.cells[0].cell_type == CellType.CODE
        assert "x = 42" in restored.cells[0].source
        assert "print(x)" in restored.cells[0].source

    def test_markdown_cell_roundtrip(self):
        nb = NotebookFile()
        nb.add_cell("## Title\nSome text", CellType.MARKDOWN)
        text = serialize_notebook(nb)

        assert "# %% [markdown]" in text
        assert "# ## Title" in text
        assert "# Some text" in text

        restored = parse_notebook(text)
        assert len(restored.cells) == 1
        assert restored.cells[0].cell_type == CellType.MARKDOWN
        assert "## Title" in restored.cells[0].source
        assert "Some text" in restored.cells[0].source

    def test_sql_cell_roundtrip(self):
        nb = NotebookFile()
        nb.add_cell("SELECT * FROM users WHERE age > 21", CellType.SQL)
        text = serialize_notebook(nb)

        assert "# %% [sql]" in text
        assert "# %%sql" in text
        assert "# SELECT * FROM users" in text

        restored = parse_notebook(text)
        assert len(restored.cells) == 1
        assert restored.cells[0].cell_type == CellType.SQL
        assert "SELECT * FROM users" in restored.cells[0].source

    def test_multi_cell_roundtrip(self):
        nb = NotebookFile(metadata=NotebookMetadata(name="analysis", version=2))
        nb.add_cell("import pandas as pd", CellType.CODE, "imports", "c1")
        nb.add_cell("## Data Loading", CellType.MARKDOWN, "", "c2")
        nb.add_cell("df = pd.read_csv('data.csv')", CellType.CODE, "load", "c3")
        nb.add_cell("SELECT COUNT(*) FROM df", CellType.SQL, "", "c4")

        text = serialize_notebook(nb)
        restored = parse_notebook(text)

        assert restored.metadata.name == "analysis"
        assert restored.metadata.version == 2
        assert len(restored.cells) == 4
        assert restored.cells[0].id == "c1"
        assert restored.cells[0].cell_type == CellType.CODE
        assert restored.cells[1].cell_type == CellType.MARKDOWN
        assert restored.cells[2].cell_type == CellType.CODE
        assert restored.cells[3].cell_type == CellType.SQL

    def test_named_cell_roundtrip(self):
        nb = NotebookFile()
        nb.add_cell("x = 1", CellType.CODE, "My Setup Cell", "abc")
        text = serialize_notebook(nb)

        assert '"My Setup Cell"' in text

        restored = parse_notebook(text)
        assert restored.cells[0].name == "My Setup Cell"

    def test_empty_code_cell_roundtrip(self):
        nb = NotebookFile()
        nb.add_cell("", CellType.CODE)
        text = serialize_notebook(nb)
        assert "pass  # empty cell" in text

        restored = parse_notebook(text)
        assert restored.cells[0].source == ""

    def test_metadata_roundtrip(self):
        nb = NotebookFile(metadata=NotebookMetadata(
            name="ml_pipeline",
            version=3,
            server="https://flowyml.company.com",
            author="Alice",
            description="Training pipeline",
            tags=["ml", "production"],
        ))
        text = serialize_notebook(nb)

        assert "# server: https://flowyml.company.com" in text
        assert "# author: Alice" in text
        assert "# tags: ml, production" in text

        restored = parse_notebook(text)
        assert restored.metadata.name == "ml_pipeline"
        assert restored.metadata.version == 3
        assert restored.metadata.server == "https://flowyml.company.com"
        assert restored.metadata.author == "Alice"
        assert "ml" in restored.metadata.tags
        assert "production" in restored.metadata.tags

    def test_vscode_compatibility(self):
        """Verify the output is valid VS Code percent format."""
        nb = NotebookFile()
        nb.add_cell("x = 1", CellType.CODE)
        nb.add_cell("## Title", CellType.MARKDOWN)
        text = serialize_notebook(nb)

        # VS Code recognizes cells starting with # %%
        lines = text.split("\n")
        cell_markers = [l for l in lines if l.startswith("# %%")]
        assert len(cell_markers) == 2

    def test_file_is_valid_python(self):
        """The serialized file should be valid Python (compilable)."""
        nb = NotebookFile()
        nb.add_cell("x = 42\ny = x + 1", CellType.CODE)
        nb.add_cell("## Title\nSome description", CellType.MARKDOWN)
        nb.add_cell("z = y * 2", CellType.CODE)

        text = serialize_notebook(nb)
        # This should not raise SyntaxError
        compile(text, "<notebook>", "exec")


class TestCellOutput:
    """Test CellOutput serialization."""

    def test_to_dict(self):
        output = CellOutput(output_type="text", data="hello")
        d = output.to_dict()
        assert d["output_type"] == "text"
        assert d["data"] == "hello"
        assert "timestamp" in d

    def test_none_data(self):
        output = CellOutput(output_type="text", data=None)
        d = output.to_dict()
        assert d["data"] is None
