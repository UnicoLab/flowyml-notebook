"""Environment snapshot and reproducibility utilities for FlowyML notebooks.

This module provides tools for capturing the current runtime environment
(Python version, OS, installed packages, GPU availability) and for
extracting dependency information from notebooks so that reproducible
``requirements.txt`` or ``environment.yml`` files can be generated
automatically.
"""

from __future__ import annotations

import ast
import importlib.metadata
import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from flowyml_notebook.cells import CellType, NotebookFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment snapshot
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentSnapshot:
    """Immutable snapshot of the current runtime environment.

    Attributes:
        python_version: Full Python version string (e.g. ``"3.11.4 …"``).
        platform_info: Detailed platform identifier from :func:`platform.platform`.
        os_name: Operating-system name (``"Linux"``, ``"Darwin"``, ``"Windows"``).
        architecture: CPU architecture string (e.g. ``"x86_64"``, ``"arm64"``).
        packages: Mapping of installed package names to their versions.
        gpu_info: List of dictionaries describing each detected GPU.
        timestamp: ISO-8601 timestamp of when the snapshot was taken.
        cpu_count: Number of logical CPUs available.
    """

    python_version: str
    platform_info: str
    os_name: str
    architecture: str
    packages: Dict[str, str]
    gpu_info: List[Dict[str, str]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cpu_count: int = field(default_factory=lambda: os.cpu_count() or 0)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "python_version": self.python_version,
            "platform_info": self.platform_info,
            "os_name": self.os_name,
            "architecture": self.architecture,
            "packages": self.packages,
            "gpu_info": self.gpu_info,
            "timestamp": self.timestamp,
            "cpu_count": self.cpu_count,
        }


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------


def capture_environment() -> EnvironmentSnapshot:
    """Capture a complete snapshot of the current runtime environment.

    The function collects Python version information, operating-system
    details, all installed packages (via :mod:`importlib.metadata`), GPU
    information (NVIDIA via ``nvidia-smi`` and Apple Silicon MPS), and
    basic CPU metadata.

    Returns:
        An :class:`EnvironmentSnapshot` populated with the current state.
    """

    # -- Python / OS -----------------------------------------------------------
    python_version = sys.version
    platform_info = platform.platform()
    os_name = platform.system()
    architecture = platform.machine()

    # -- Installed packages ----------------------------------------------------
    packages: Dict[str, str] = {}
    try:
        for dist in importlib.metadata.distributions():
            name = dist.metadata["Name"]
            version = dist.metadata["Version"]
            if name and version:
                packages[name] = version
    except Exception:  # pragma: no cover
        logger.warning("Failed to enumerate installed packages", exc_info=True)

    # -- GPU detection ---------------------------------------------------------
    gpu_info: List[Dict[str, str]] = []

    # NVIDIA GPUs via nvidia-smi
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    gpu_info.append(
                        {
                            "name": parts[0],
                            "memory_total_mb": parts[1],
                            "driver_version": parts[2],
                            "type": "nvidia",
                        }
                    )
    except FileNotFoundError:
        logger.debug("nvidia-smi not found – skipping NVIDIA GPU detection")
    except Exception:  # pragma: no cover
        logger.debug("nvidia-smi query failed", exc_info=True)

    # Apple Silicon MPS
    if os_name == "Darwin" and architecture == "arm64":
        gpu_info.append(
            {
                "name": "Apple Silicon (MPS)",
                "type": "mps",
            }
        )

    # -- CPU -------------------------------------------------------------------
    cpu_count = os.cpu_count() or 0

    return EnvironmentSnapshot(
        python_version=python_version,
        platform_info=platform_info,
        os_name=os_name,
        architecture=architecture,
        packages=packages,
        gpu_info=gpu_info,
        cpu_count=cpu_count,
    )


# ---------------------------------------------------------------------------
# Standard-library module list
# ---------------------------------------------------------------------------


def _get_stdlib_modules() -> Set[str]:
    """Return the set of standard-library module names.

    On Python ≥ 3.10 the authoritative :data:`sys.stdlib_module_names` is
    used.  On older interpreters a hard-coded set of the most common stdlib
    top-level names is returned as a best-effort fallback.

    Returns:
        A set of module name strings.
    """

    if sys.version_info >= (3, 10):
        return set(sys.stdlib_module_names)  # type: ignore[attr-defined]

    # Fallback for Python < 3.10
    return {
        "abc",
        "aifc",
        "argparse",
        "array",
        "ast",
        "asynchat",
        "asyncio",
        "asyncore",
        "atexit",
        "audioop",
        "base64",
        "bdb",
        "binascii",
        "binhex",
        "bisect",
        "builtins",
        "bz2",
        "calendar",
        "cgi",
        "cgitb",
        "chunk",
        "cmath",
        "cmd",
        "code",
        "codecs",
        "codeop",
        "collections",
        "colorsys",
        "compileall",
        "concurrent",
        "configparser",
        "contextlib",
        "contextvars",
        "copy",
        "copyreg",
        "cProfile",
        "crypt",
        "csv",
        "ctypes",
        "curses",
        "dataclasses",
        "datetime",
        "dbm",
        "decimal",
        "difflib",
        "dis",
        "distutils",
        "doctest",
        "email",
        "encodings",
        "enum",
        "errno",
        "faulthandler",
        "fcntl",
        "filecmp",
        "fileinput",
        "fnmatch",
        "formatter",
        "fractions",
        "ftplib",
        "functools",
        "gc",
        "getopt",
        "getpass",
        "gettext",
        "glob",
        "grp",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "idlelib",
        "imaplib",
        "imghdr",
        "imp",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "keyword",
        "lib2to3",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "mailcap",
        "marshal",
        "math",
        "mimetypes",
        "mmap",
        "modulefinder",
        "multiprocessing",
        "netrc",
        "nis",
        "nntplib",
        "numbers",
        "operator",
        "optparse",
        "os",
        "ossaudiodev",
        "parser",
        "pathlib",
        "pdb",
        "pickle",
        "pickletools",
        "pipes",
        "pkgutil",
        "platform",
        "plistlib",
        "poplib",
        "posix",
        "posixpath",
        "pprint",
        "profile",
        "pstats",
        "pty",
        "pwd",
        "py_compile",
        "pyclbr",
        "pydoc",
        "queue",
        "quopri",
        "random",
        "re",
        "readline",
        "reprlib",
        "resource",
        "rlcompleter",
        "runpy",
        "sched",
        "secrets",
        "select",
        "selectors",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "smtpd",
        "smtplib",
        "sndhdr",
        "socket",
        "socketserver",
        "sqlite3",
        "ssl",
        "stat",
        "statistics",
        "string",
        "stringprep",
        "struct",
        "subprocess",
        "sunau",
        "symtable",
        "sys",
        "sysconfig",
        "syslog",
        "tabnanny",
        "tarfile",
        "telnetlib",
        "tempfile",
        "termios",
        "test",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "tkinter",
        "token",
        "tokenize",
        "trace",
        "traceback",
        "tracemalloc",
        "tty",
        "turtle",
        "turtledemo",
        "types",
        "typing",
        "unicodedata",
        "unittest",
        "urllib",
        "uu",
        "uuid",
        "venv",
        "warnings",
        "wave",
        "weakref",
        "webbrowser",
        "winreg",
        "winsound",
        "wsgiref",
        "xdrlib",
        "xml",
        "xmlrpc",
        "zipapp",
        "zipfile",
        "zipimport",
        "zlib",
        "_thread",
    }


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------


def extract_imports(notebook: NotebookFile) -> Set[str]:
    """Extract third-party top-level import names from a notebook.

    Only code cells are inspected.  The source of each cell is parsed with
    :func:`ast.parse`; ``import`` and ``from … import`` statements are
    collected.  Standard-library modules and ``__future__`` imports are
    excluded from the returned set.

    Args:
        notebook: A :class:`NotebookFile` whose code cells will be analysed.

    Returns:
        A set of top-level package names (e.g. ``{"numpy", "pandas"}``).
    """

    stdlib = _get_stdlib_modules()
    imports: Set[str] = set()

    for cell in notebook.cells:
        if cell.cell_type != CellType.CODE:
            continue

        try:
            tree = ast.parse(cell.source)
        except SyntaxError:
            logger.debug("Skipping cell with syntax error during import extraction")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    imports.add(top_level)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_level = node.module.split(".")[0]
                    imports.add(top_level)

    # Filter out stdlib and __future__
    imports.discard("__future__")
    imports -= stdlib

    return imports


# ---------------------------------------------------------------------------
# Common import-name → PyPI package-name mapping
# ---------------------------------------------------------------------------

IMPORT_TO_PKG: Dict[str, str] = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "attr": "attrs",
    "dateutil": "python-dateutil",
    "git": "GitPython",
    "dotenv": "python-dotenv",
    "serial": "pyserial",
    "usb": "pyusb",
    "wx": "wxPython",
    "gi": "PyGObject",
    "Crypto": "pycryptodome",
    "jose": "python-jose",
    "jwt": "PyJWT",
    "magic": "python-magic",
    "Bio": "biopython",
    "skimage": "scikit-image",
}


# ---------------------------------------------------------------------------
# Requirements export
# ---------------------------------------------------------------------------


def export_requirements(
    notebook: NotebookFile,
    output_path: str | Path,
    pinned: bool = True,
) -> Path:
    """Generate a ``requirements.txt`` from a notebook's imports.

    Each import is mapped to a PyPI package name (using
    :data:`IMPORT_TO_PKG` when necessary), and the currently installed
    version is looked up from the environment snapshot.

    Args:
        notebook: The notebook to analyse.
        output_path: Destination file path for the generated
            ``requirements.txt``.
        pinned: If ``True`` (default), pin each package to its currently
            installed version (``pkg==x.y.z``).  Otherwise only the bare
            package name is written.

    Returns:
        The resolved :class:`~pathlib.Path` of the written file.
    """

    imports = extract_imports(notebook)
    env = capture_environment()

    # Build a case-insensitive lookup of installed packages
    installed: Dict[str, str] = {name.lower(): version for name, version in env.packages.items()}

    lines: List[str] = []
    for imp in sorted(imports):
        pkg_name = IMPORT_TO_PKG.get(imp, imp)
        version = installed.get(pkg_name.lower())
        if pinned and version:
            lines.append(f"{pkg_name}=={version}")
        else:
            lines.append(pkg_name)

    output = Path(output_path)
    header = f"# Auto-generated by FlowyML Notebook\n# Timestamp: {datetime.now().isoformat()}\n#\n"
    output.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

    logger.info("Wrote requirements to %s (%d packages)", output, len(lines))
    return output


# ---------------------------------------------------------------------------
# Conda environment export
# ---------------------------------------------------------------------------


def export_conda_env(
    notebook: NotebookFile,
    output_path: str | Path,
    env_name: str | None = None,
) -> Path:
    """Generate a Conda ``environment.yml`` from a notebook's imports.

    The generated file includes the ``defaults`` and ``conda-forge``
    channels.  Packages that cannot be mapped to Conda channels are placed
    under a ``pip`` sub-list.

    If `PyYAML <https://pypi.org/project/PyYAML/>`_ is available it is used
    for serialisation; otherwise the YAML is written via simple string
    formatting.

    Args:
        notebook: The notebook to analyse.
        output_path: Destination file path for the generated
            ``environment.yml``.
        env_name: Optional environment name.  Defaults to ``"flowyml_env"``.

    Returns:
        The resolved :class:`~pathlib.Path` of the written file.
    """

    imports = extract_imports(notebook)
    env = capture_environment()

    installed: Dict[str, str] = {name.lower(): version for name, version in env.packages.items()}

    if env_name is None:
        env_name = "flowyml_env"

    pip_deps: List[str] = []
    for imp in sorted(imports):
        pkg_name = IMPORT_TO_PKG.get(imp, imp)
        version = installed.get(pkg_name.lower())
        if version:
            pip_deps.append(f"{pkg_name}=={version}")
        else:
            pip_deps.append(pkg_name)

    env_dict = {
        "name": env_name,
        "channels": ["defaults", "conda-forge"],
        "dependencies": [
            f"python={platform.python_version()}",
            "pip",
            {"pip": pip_deps},
        ],
    }

    output = Path(output_path)

    # Try PyYAML first, fall back to manual formatting
    try:
        import yaml  # type: ignore[import-untyped]

        yaml_content = yaml.dump(env_dict, default_flow_style=False, sort_keys=False)
        output.write_text(yaml_content, encoding="utf-8")
    except ImportError:
        logger.debug("PyYAML not available – writing YAML manually")
        lines: List[str] = [
            f"name: {env_name}",
            "channels:",
            "  - defaults",
            "  - conda-forge",
            "dependencies:",
            f"  - python={platform.python_version()}",
            "  - pip",
            "  - pip:",
        ]
        for dep in pip_deps:
            lines.append(f"      - {dep}")

        output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info("Wrote conda environment to %s (%d pip deps)", output, len(pip_deps))
    return output
