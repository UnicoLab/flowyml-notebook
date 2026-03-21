#!/usr/bin/env python3
"""Standalone test script — imports submodules directly to avoid heavy deps."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def test(name, fn):
    global passed, failed
    try:
        fn(); passed += 1; print(f"  ✅ {name}")
    except Exception as e:
        failed += 1; print(f"  ❌ {name}: {e}")

# ===== reactive.py (no external deps) =====
print("\n📦 reactive.py")
from flowyml_notebook.reactive import ReactiveGraph, CellState, analyze_cell_dependencies

test("simple assignment", lambda: (
    (r := analyze_cell_dependencies("x = 42")[0]),
    (w := analyze_cell_dependencies("x = 42")[1]),
    None if "x" in w else (_ for _ in ()).throw(AssertionError("x not in writes"))
))

def t_reads():
    r, w = analyze_cell_dependencies("y = x + 1")
    assert "x" in r and "y" in w
test("read variable", t_reads)

def t_import():
    _, w = analyze_cell_dependencies("import pandas as pd")
    assert "pd" in w
test("import", t_import)

def t_funcdef():
    _, w = analyze_cell_dependencies("def train(d): return d*2")
    assert "train" in w
test("function def", t_funcdef)

def t_syntax():
    r, w = analyze_cell_dependencies("def broken(")
    assert r == set() and w == set()
test("syntax error graceful", t_syntax)

def t_deps():
    g = ReactiveGraph()
    g.update_cell("c1", "x = 42")
    g.update_cell("c2", "y = x + 1")
    assert "c1" in g.get_upstream("c2")
    assert "c2" in g.get_downstream("c1")
test("dependency detection", t_deps)

def t_order():
    g = ReactiveGraph()
    g.update_cell("c1", "x = 1")
    g.update_cell("c2", "y = x + 1")
    g.update_cell("c3", "z = y * 2")
    o = g.get_execution_order()
    assert o.index("c1") < o.index("c2") < o.index("c3")
test("topological order", t_order)

def t_stale():
    g = ReactiveGraph()
    g.update_cell("c1", "x = 1")
    g.update_cell("c2", "y = x + 1")
    g.set_cell_state("c2", CellState.SUCCESS)
    stale = g.update_cell("c1", "x = 99")
    assert "c2" in stale
test("stale detection", t_stale)

def t_diamond():
    g = ReactiveGraph()
    g.update_cell("a", "x = 1")
    g.update_cell("b", "y = x + 1")
    g.update_cell("c", "z = x + 2")
    g.update_cell("d", "w = y + z")
    o = g.get_execution_order()
    assert o.index("a") < o.index("d")
test("diamond dependency", t_diamond)

def t_remove():
    g = ReactiveGraph()
    g.update_cell("a", "x = 1")
    g.update_cell("b", "y = x + 1")
    stale = g.remove_cell("a")
    assert "a" not in g.cells and "b" in stale
test("cell removal", t_remove)

# ===== cells.py (no external deps) =====
print("\n📦 cells.py")
from flowyml_notebook.cells import Cell, CellType, NotebookFile, NotebookMetadata, serialize_notebook, parse_notebook

def t_cell():
    c = Cell(); assert c.cell_type == CellType.CODE and len(c.id) == 8
test("default cell", t_cell)

def t_serde():
    c = Cell(id="a", source="x=1"); d = c.to_dict(); r = Cell.from_dict(d)
    assert r.id == "a" and r.source == "x=1"
test("cell serde", t_serde)

def t_roundtrip():
    nb = NotebookFile(metadata=NotebookMetadata(name="t", version=2))
    nb.add_cell("x = 42", CellType.CODE, "setup", "c1")
    nb.add_cell("## Title\nText", CellType.MARKDOWN, "", "c2")
    nb.add_cell("SELECT 1", CellType.SQL, "", "c3")
    txt = serialize_notebook(nb)
    r = parse_notebook(txt)
    assert r.metadata.name == "t" and len(r.cells) == 3
    assert r.cells[0].id == "c1" and r.cells[1].cell_type == CellType.MARKDOWN
    assert "Title" in r.cells[1].source
test("full round-trip", t_roundtrip)

def t_python():
    nb = NotebookFile()
    nb.add_cell("x = 42\ny = x + 1", CellType.CODE)
    nb.add_cell("## Hi", CellType.MARKDOWN)
    compile(serialize_notebook(nb), "<nb>", "exec")
test("valid Python output", t_python)

def t_meta():
    nb = NotebookFile(metadata=NotebookMetadata(name="m", server="https://s.com", author="A", tags=["a","b"]))
    r = parse_notebook(serialize_notebook(nb))
    assert r.metadata.server == "https://s.com" and "a" in r.metadata.tags
test("metadata round-trip", t_meta)

def t_pct():
    nb = NotebookFile()
    nb.add_cell("x=1", CellType.CODE)
    nb.add_cell("## H", CellType.MARKDOWN)
    markers = [l for l in serialize_notebook(nb).split("\n") if l.startswith("# %%")]
    assert len(markers) == 2
test("VS Code percent markers", t_pct)

# ===== widgets (no external deps) =====
print("\n📦 widgets")
from flowyml_notebook.ui import slider, dropdown, checkbox, table

def t_slider():
    s = slider(0, 100, 50, label="A")
    assert s.value == 50 and s.config["min"] == 0
test("slider", t_slider)

def t_dropdown():
    d = dropdown(["a","b","c"])
    assert d.value == "a"
test("dropdown", t_dropdown)

def t_table():
    t = table([{"a": 1}, {"a": 2}])
    assert len(t.value["rows"]) == 2
test("table", t_table)

def t_onchange():
    w = slider(0,10,5); vals = []
    w.on_change(lambda v: vals.append(v))
    w.set_value(7)
    assert vals == [7]
test("on_change callback", t_onchange)

# ===== Summary =====
print(f"\n{'='*40}")
print(f"Results: {passed}/{passed+failed} passed, {failed} failed")
print("🎉 All tests passed!" if failed == 0 else "❌ Some tests failed")
sys.exit(0 if failed == 0 else 1)
