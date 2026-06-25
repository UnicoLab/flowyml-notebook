"""Package installer module for FlowyML Notebook.

Provides utilities for detecting the current Python environment, installing
and uninstalling packages via pip, listing installed packages, and searching
PyPI for package metadata.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distributions, version
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EnvInfo:
    """Information about the current Python environment."""

    env_type: str  # 'conda', 'venv', or 'system'
    python_path: str
    env_name: str
    env_path: str
    pip_path: str

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "env_type": self.env_type,
            "python_path": self.python_path,
            "env_name": self.env_name,
            "env_path": self.env_path,
            "pip_path": self.pip_path,
        }


@dataclass
class InstallResult:
    """Result of a package install or uninstall operation."""

    package: str
    success: bool
    version: str = ""
    output: str = ""
    error: str = ""
    env_type: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "package": self.package,
            "success": self.success,
            "version": self.version,
            "output": self.output,
            "error": self.error,
            "env_type": self.env_type,
        }


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------


def detect_environment() -> EnvInfo:
    """Detect the current Python environment type and paths.

    Checks for Conda, virtualenv / venv, or falls back to the system
    interpreter.

    Returns:
        EnvInfo: Populated dataclass describing the active environment.
    """
    python_path = sys.executable
    env_type: str
    env_name: str
    env_path: str

    conda_prefix = os.environ.get("CONDA_PREFIX")

    if conda_prefix:
        env_type = "conda"
        env_path = conda_prefix
        env_name = os.path.basename(conda_prefix)
        logger.debug("Detected conda environment: %s at %s", env_name, env_path)

    elif sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV"):
        env_type = "venv"
        env_path = os.environ.get("VIRTUAL_ENV", sys.prefix)
        env_name = os.path.basename(env_path)
        logger.debug("Detected venv environment: %s at %s", env_name, env_path)

    else:
        env_type = "system"
        env_path = sys.prefix
        env_name = "system"
        logger.debug("Using system Python at %s", python_path)

    pip_path = _find_pip(env_path)

    return EnvInfo(
        env_type=env_type,
        python_path=python_path,
        env_name=env_name,
        env_path=env_path,
        pip_path=pip_path,
    )


def _find_pip(env_path: str) -> str:
    """Locate the pip executable within *env_path*.

    Falls back to ``sys.executable -m pip`` representation when an explicit
    pip binary cannot be found on disk.

    Args:
        env_path: Root path of the Python environment.

    Returns:
        Absolute path to the pip binary, or a descriptive fallback string.
    """
    # Try common locations
    candidates = [
        os.path.join(env_path, "bin", "pip"),
        os.path.join(env_path, "bin", "pip3"),
        os.path.join(env_path, "Scripts", "pip.exe"),
        os.path.join(env_path, "Scripts", "pip3.exe"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    # Fall back to shutil.which
    pip_on_path = shutil.which("pip") or shutil.which("pip3")
    if pip_on_path:
        return pip_on_path

    return f"{sys.executable} -m pip"


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------


def _get_package_version(name: str) -> str | None:
    """Return the installed version string for *name*, or ``None``.

    Args:
        name: The distribution / package name (e.g. ``"requests"``).

    Returns:
        Version string if installed, otherwise ``None``.
    """
    try:
        return version(name)
    except PackageNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------


def install_package(
    name: str,
    version: str | None = None,
    upgrade: bool = False,
    quiet: bool = True,
) -> InstallResult:
    """Install a Python package via pip.

    Args:
        name: Package name (e.g. ``"requests"``).
        version: Optional version constraint (e.g. ``"2.31.0"``).
        upgrade: If ``True``, pass ``--upgrade`` to pip.
        quiet: If ``True``, pass ``--quiet`` to pip.

    Returns:
        InstallResult: Outcome of the installation attempt.
    """
    env = detect_environment()
    package_spec = f"{name}=={version}" if version else name

    cmd: list[str] = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    if quiet:
        cmd.append("--quiet")
    cmd.append(package_spec)

    logger.info("Installing %s in %s environment (%s)", package_spec, env.env_type, env.env_name)
    logger.debug("Running command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            installed_version = _get_package_version(name) or ""
            logger.info("Successfully installed %s %s", name, installed_version)
            return InstallResult(
                package=name,
                success=True,
                version=installed_version,
                output=result.stdout,
                error=result.stderr,
                env_type=env.env_type,
            )
        else:
            logger.error("Failed to install %s: %s", name, result.stderr)
            return InstallResult(
                package=name,
                success=False,
                version="",
                output=result.stdout,
                error=result.stderr,
                env_type=env.env_type,
            )

    except subprocess.TimeoutExpired:
        error_msg = f"Installation of {package_spec} timed out after 300 seconds"
        logger.error(error_msg)
        return InstallResult(
            package=name,
            success=False,
            version="",
            output="",
            error=error_msg,
            env_type=env.env_type,
        )
    except Exception as exc:
        error_msg = f"Unexpected error installing {package_spec}: {exc}"
        logger.error(error_msg)
        return InstallResult(
            package=name,
            success=False,
            version="",
            output="",
            error=error_msg,
            env_type=env.env_type,
        )


def uninstall_package(name: str) -> InstallResult:
    """Uninstall a Python package via pip.

    Args:
        name: Package name to remove.

    Returns:
        InstallResult: Outcome of the uninstall attempt.
    """
    env = detect_environment()
    cmd: list[str] = [sys.executable, "-m", "pip", "uninstall", "-y", name]

    logger.info("Uninstalling %s from %s environment (%s)", name, env.env_type, env.env_name)
    logger.debug("Running command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            logger.info("Successfully uninstalled %s", name)
            return InstallResult(
                package=name,
                success=True,
                version="",
                output=result.stdout,
                error=result.stderr,
                env_type=env.env_type,
            )
        else:
            logger.error("Failed to uninstall %s: %s", name, result.stderr)
            return InstallResult(
                package=name,
                success=False,
                version="",
                output=result.stdout,
                error=result.stderr,
                env_type=env.env_type,
            )

    except subprocess.TimeoutExpired:
        error_msg = f"Uninstall of {name} timed out after 300 seconds"
        logger.error(error_msg)
        return InstallResult(
            package=name,
            success=False,
            version="",
            output="",
            error=error_msg,
            env_type=env.env_type,
        )
    except Exception as exc:
        error_msg = f"Unexpected error uninstalling {name}: {exc}"
        logger.error(error_msg)
        return InstallResult(
            package=name,
            success=False,
            version="",
            output="",
            error=error_msg,
            env_type=env.env_type,
        )


# ---------------------------------------------------------------------------
# Listing installed packages
# ---------------------------------------------------------------------------


def list_installed() -> dict[str, str]:
    """Return a mapping of all installed package names to their versions.

    Uses ``importlib.metadata.distributions()`` so no subprocess is needed.

    Returns:
        dict[str, str]: ``{package_name: version}`` for every installed
        distribution.
    """
    try:
        return {
            dist.metadata["Name"]: dist.metadata["Version"]
            for dist in distributions()
            if dist.metadata["Name"] is not None
        }
    except Exception as exc:
        logger.error("Error listing installed packages: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# PyPI search
# ---------------------------------------------------------------------------


def _fetch_json(url: str, timeout: int = 15) -> dict[str, Any] | None:
    """Fetch JSON from *url*, preferring httpx when available.

    Falls back to :mod:`urllib.request` if httpx is not installed.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON as a dict, or ``None`` on failure.
    """
    # Try httpx first
    try:
        import httpx  # type: ignore[import-untyped]

        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except ImportError:
        logger.debug("httpx not available, falling back to urllib")
    except Exception as exc:
        logger.debug("httpx request failed for %s: %s", url, exc)
        return None

    # Fallback: urllib
    try:
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "flowyml-notebook"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except URLError as exc:
        logger.debug("urllib request failed for %s: %s", url, exc)
    except Exception as exc:
        logger.debug("Unexpected error fetching %s: %s", url, exc)

    return None


def search_pypi(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search PyPI for packages matching *query*.

    First attempts an exact-match lookup via the PyPI JSON API.  If that
    fails, a rudimentary search against the Simple API index is attempted
    (substring match on package names).  Network errors are handled
    gracefully and logged.

    Args:
        query: Search term (package name or keyword).
        limit: Maximum number of results to return.

    Returns:
        A list of dicts, each containing ``name``, ``version``,
        ``summary``, ``author``, and ``home_page`` keys.
    """
    results: list[dict[str, Any]] = []

    # --- Exact match via JSON API ---
    url = f"https://pypi.org/pypi/{query}/json"
    logger.debug("Querying PyPI JSON API: %s", url)

    data = _fetch_json(url)
    if data and "info" in data:
        info = data["info"]
        results.append(
            {
                "name": info.get("name", query),
                "version": info.get("version", ""),
                "summary": info.get("summary", ""),
                "author": info.get("author", ""),
                "home_page": info.get("home_page", ""),
            }
        )
        return results[:limit]

    # --- Fallback: simple index substring search ---
    logger.debug("Exact match not found on PyPI for '%s', trying simple index.", query)

    try:
        simple_url = "https://pypi.org/simple/"
        try:
            import httpx  # type: ignore[import-untyped]

            resp = httpx.get(simple_url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            page_text = resp.text
        except ImportError:
            req = Request(simple_url, headers={"User-Agent": "flowyml-notebook"})
            with urlopen(req, timeout=30) as resp:
                page_text = resp.read().decode()

        # Very simple HTML parse – each anchor text is a package name
        query_lower = query.lower()
        matches: list[str] = []

        for line in page_text.splitlines():
            if "<a " not in line:
                continue
            # Extract text between > and </a>
            start = line.find(">")
            end = line.find("</a>")
            if start == -1 or end == -1:
                continue
            pkg_name = line[start + 1 : end].strip()
            if query_lower in pkg_name.lower():
                matches.append(pkg_name)
                if len(matches) >= limit:
                    break

        # Fetch metadata for each matched package
        for pkg_name in matches:
            pkg_data = _fetch_json(f"https://pypi.org/pypi/{pkg_name}/json")
            if pkg_data and "info" in pkg_data:
                info = pkg_data["info"]
                results.append(
                    {
                        "name": info.get("name", pkg_name),
                        "version": info.get("version", ""),
                        "summary": info.get("summary", ""),
                        "author": info.get("author", ""),
                        "home_page": info.get("home_page", ""),
                    }
                )
            else:
                results.append(
                    {
                        "name": pkg_name,
                        "version": "",
                        "summary": "",
                        "author": "",
                        "home_page": "",
                    }
                )

        if not results:
            logger.warning("No packages found on PyPI matching '%s'.", query)

    except Exception as exc:
        logger.error("Error searching PyPI simple index: %s", exc)

    return results[:limit]
