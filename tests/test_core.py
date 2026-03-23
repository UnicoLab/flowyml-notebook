"""Tests for the core notebook engine."""

import pytest
from flowyml_notebook.cells import Cell, CellType, NotebookFile, NotebookMetadata
from flowyml_notebook.core import Notebook, NotebookSession, ExecutionResult


class TestNotebookSession:
    """Test the execution session."""

    def test_create_session(self):
        session = NotebookSession()
        assert session.session_id is not None
        assert not session._initialized

    def test_execute_code_cell(self):
        session = NotebookSession()
        cell = Cell(source="x = 42")
        result = session.execute_cell(cell)
        assert result.success
        assert result.cell_id == cell.id
        assert session.get_variable("x") == 42

    def test_execute_print_output(self):
        session = NotebookSession()
        cell = Cell(source="print('hello world')")
        result = session.execute_cell(cell)
        assert result.success
        # Check that output was captured
        text_outputs = [o for o in result.outputs if o.output_type == "text"]
        assert any("hello world" in str(o.data) for o in text_outputs)

    def test_execute_error(self):
        session = NotebookSession()
        cell = Cell(source="1/0")
        result = session.execute_cell(cell)
        assert not result.success
        assert result.error is not None
        assert "division by zero" in result.error

    def test_execute_syntax_error(self):
        session = NotebookSession()
        cell = Cell(source="def broken(")
        result = session.execute_cell(cell)
        assert not result.success

    def test_shared_namespace(self):
        session = NotebookSession()
        session.execute_cell(Cell(source="x = 10"))
        session.execute_cell(Cell(source="y = x * 2"))
        assert session.get_variable("y") == 20

    def test_get_variables(self):
        session = NotebookSession()
        session.execute_cell(Cell(source="name = 'alice'\nage = 30"))
        variables = session.get_variables()
        assert "name" in variables
        assert variables["name"]["type"] == "str"
        assert "age" in variables
        assert variables["age"]["type"] == "int"

    def test_set_variable(self):
        session = NotebookSession()
        session._ensure_kernel()
        session.set_variable("test_var", 123)
        assert session.get_variable("test_var") == 123

    def test_reset(self):
        session = NotebookSession()
        session.execute_cell(Cell(source="x = 42"))
        assert session.get_variable("x") == 42
        session.reset()
        assert session.get_variable("x") is None

    def test_execute_markdown_cell(self):
        session = NotebookSession()
        cell = Cell(cell_type=CellType.MARKDOWN, source="## Hello")
        result = session.execute_cell(cell)
        assert result.success
        assert any(o.output_type == "html" for o in result.outputs)

    def test_execute_dataframe_result(self):
        session = NotebookSession()
        cell = Cell(source="import pandas as pd\ndf = pd.DataFrame({'a': [1,2,3]})\ndf")
        result = session.execute_cell(cell)
        assert result.success

    def test_execution_count(self):
        session = NotebookSession()
        cell = Cell(source="x = 1")
        assert cell.execution_count == 0
        session.execute_cell(cell)
        assert cell.execution_count == 1
        session.execute_cell(cell)
        assert cell.execution_count == 2


class TestNotebook:
    """Test the main Notebook class."""

    def test_create_notebook(self):
        nb = Notebook(name="test_nb")
        assert nb.name == "test_nb"
        assert len(nb.cells) == 0

    def test_add_and_execute_cell(self):
        nb = Notebook()
        nb.cell("x = 42")
        result = nb.execute_cell(nb.cells[0].id)
        assert result.success
        assert nb.session.get_variable("x") == 42

    def test_reactive_execution(self):
        nb = Notebook()
        c1 = nb.cell("x = 10")
        c2 = nb.cell("y = x * 2")

        # Execute c1 reactively — should also execute c2
        results = nb.execute_cell_reactive(c1.id)
        # First result is c1, remaining are downstream
        assert results[0].success
        assert nb.session.get_variable("x") == 10
        assert nb.session.get_variable("y") == 20

    def test_run_all(self):
        nb = Notebook()
        nb.cell("a = 1")
        nb.cell("b = a + 1")
        nb.cell("c = b + 1")
        results = nb.run()
        assert all(r.success for r in results)
        assert nb.session.get_variable("c") == 3

    def test_update_cell(self):
        nb = Notebook()
        c1 = nb.cell("x = 1")
        c2 = nb.cell("y = x + 1")

        stale = nb.update_cell(c1.id, "x = 100")
        assert c2.id in stale

    def test_save_and_load(self, tmp_path):
        nb = Notebook(name="save_test")
        nb.cell("x = 42")
        nb.cell("## Analysis", CellType.MARKDOWN)
        nb.cell("y = x + 1")

        path = str(tmp_path / "test.py")
        nb.save(path)

        # Load into new notebook
        nb2 = Notebook(file_path=path)
        assert nb2.name == "save_test"
        assert len(nb2.cells) == 3
        assert nb2.cells[0].source == "x = 42"
        assert nb2.cells[1].cell_type == CellType.MARKDOWN

    def test_get_state(self):
        nb = Notebook(name="state_test")
        nb.cell("x = 1")
        state = nb.get_state()
        assert "notebook" in state
        assert "graph" in state
        assert "variables" in state
        assert "session_id" in state
        assert state["notebook"]["metadata"]["name"] == "state_test"

    def test_execution_result_to_dict(self):
        result = ExecutionResult(
            cell_id="test",
            success=True,
            duration_seconds=0.1,
        )
        d = result.to_dict()
        assert d["cell_id"] == "test"
        assert d["success"] is True
        assert d["duration_seconds"] == 0.1
