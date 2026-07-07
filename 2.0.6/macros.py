"""MkDocs macros hook — exposes {{ version }} from pyproject.toml."""

from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback


def define_env(env):
    """Define mkdocs-macros variables available in all docs pages."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text())
        version = data.get("project", {}).get("version", "dev")
    else:
        version = "dev"

    env.variables["version"] = version
    env.variables["major_version"] = ".".join(version.split(".")[:2])
