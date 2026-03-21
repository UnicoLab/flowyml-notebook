"""Dev server orchestrator for FlowyML Notebook.

Provides a single-command dev experience that:
- Auto-installs frontend dependencies
- Starts Vite dev server (HMR) as a managed subprocess
- Starts the FastAPI backend with live reload
- Rich terminal output with live status dashboard
- Auto-opens the browser
"""

from __future__ import annotations

import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


console = Console()

FRONTEND_DIR = Path(__file__).parent / "frontend"
PACKAGE_ROOT = Path(__file__).parent.parent

# ── Brand Colors ──────────────────────────────────────────────────
WAVE = "🌊"
GRADIENT_COLORS = ["#3b82f6", "#6366f1", "#8b5cf6"]


def _styled_header() -> Panel:
    """Render the premium startup banner."""
    title = Text()
    title.append(f"\n  {WAVE}  ", style="bold")
    title.append("FlowyML Notebook", style="bold #3b82f6")
    title.append("  v0.1.0\n", style="dim #94a3b8")

    return Panel(
        title,
        border_style="#3b82f6",
        box=box.DOUBLE_EDGE,
        expand=False,
        padding=(0, 2),
    )


def _info_table(
    frontend_port: int,
    backend_port: int,
    notebook_name: str,
    mode: str,
    file_path: str | None,
) -> Table:
    """Render the server info table."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2, 0, 4),
        expand=False,
    )
    table.add_column("label", style="dim #94a3b8", min_width=14)
    table.add_column("value", style="bold")

    table.add_row("⚡ Mode", Text(mode, style="bold #22c55e"))
    table.add_row("", "")
    table.add_row(
        "🎨 Frontend",
        Text(f"http://localhost:{frontend_port}", style="bold underline #60a5fa link http://localhost:{frontend_port}"),
    )
    table.add_row(
        "🔧 Backend",
        Text(f"http://localhost:{backend_port}", style="bold underline #a78bfa link http://localhost:{backend_port}"),
    )
    table.add_row("", "")
    table.add_row("📂 Notebook", Text(notebook_name, style="#f0abfc"))

    if file_path:
        table.add_row("📄 File", Text(str(file_path), style="#94a3b8"))

    table.add_row("", "")
    table.add_row(
        "⌨️  Shortcuts",
        Text("Ctrl+C → Stop  |  Cmd+S → Save  |  Cmd+Shift+Enter → Run All", style="dim #64748b"),
    )

    return table


def _check_node() -> bool:
    """Check if Node.js is available."""
    return shutil.which("node") is not None


def _check_npm() -> bool:
    """Check if npm is available."""
    return shutil.which("npm") is not None


def _ensure_frontend_deps() -> bool:
    """Install frontend dependencies if node_modules doesn't exist."""
    node_modules = FRONTEND_DIR / "node_modules"

    if not FRONTEND_DIR.exists():
        console.print("[red]✗[/] Frontend directory not found at:", FRONTEND_DIR)
        return False

    if not _check_node() or not _check_npm():
        console.print("[red]✗[/] Node.js or npm not found. Please install Node.js >= 18")
        return False

    if node_modules.exists():
        console.print("[green]✓[/] Frontend dependencies ready")
        return True

    console.print("[yellow]⏳[/] Installing frontend dependencies...")
    result = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]✗[/] npm install failed:\n{result.stderr}")
        return False

    console.print("[green]✓[/] Frontend dependencies installed")
    return True


class _StreamLogger(threading.Thread):
    """Thread that reads a process stdout/stderr and logs lines with a prefix."""

    def __init__(self, stream: TextIO, prefix: str, style: str, console: Console):
        super().__init__(daemon=True)
        self.stream = stream
        self.prefix = prefix
        self.style = style
        self.console = console

    def run(self):
        try:
            for line in iter(self.stream.readline, ""):
                stripped = line.rstrip()
                if stripped:
                    self.console.print(f"  [{self.style}]{self.prefix}[/] {stripped}")
        except (ValueError, OSError):
            pass  # Stream closed


class DevServer:
    """Orchestrates Vite (frontend HMR) + FastAPI (backend) from a single process."""

    def __init__(
        self,
        notebook_name: str = "untitled",
        server: str | None = None,
        file_path: str | None = None,
        frontend_port: int = 3000,
        backend_port: int = 8888,
        no_browser: bool = False,
    ):
        self.notebook_name = notebook_name
        self.server = server
        self.file_path = file_path
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.no_browser = no_browser
        self._vite_proc: subprocess.Popen | None = None
        self._backend_proc: subprocess.Popen | None = None
        self._stopping = False

    def start(self) -> int:
        """Start both servers and display the dashboard."""
        console.clear()
        console.print(_styled_header())

        # ── Preflight checks ──
        console.print("  [dim]Preflight checks...[/]\n")

        if not _ensure_frontend_deps():
            return 1

        console.print("[green]✓[/] Backend ready (FastAPI + Uvicorn)")
        console.print()

        # ── Start Vite dev server ──
        self._start_vite()

        # ── Start Backend ──
        self._start_backend()

        # Give servers a moment to start
        time.sleep(1.5)

        # ── Dashboard ──
        console.print()
        console.print(
            Panel(
                _info_table(
                    frontend_port=self.frontend_port,
                    backend_port=self.backend_port,
                    notebook_name=self.notebook_name,
                    mode="Development (Hot Reload)",
                    file_path=self.file_path,
                ),
                title="[bold #3b82f6]Server Dashboard[/]",
                border_style="#1e3a5f",
                box=box.ROUNDED,
                padding=(1, 0),
            )
        )
        console.print()

        # ── Auto-open browser ──
        if not self.no_browser:
            self._open_browser()

        # ── Wait for shutdown ──
        self._register_cleanup()

        try:
            # Monitor child processes
            while not self._stopping:
                # Check if Vite died
                if self._vite_proc and self._vite_proc.poll() is not None:
                    console.print("\n[yellow]⚠[/]  Vite dev server exited. Restarting...")
                    self._start_vite()

                # Check if backend died
                if self._backend_proc and self._backend_proc.poll() is not None:
                    console.print("\n[yellow]⚠[/]  Backend server exited. Restarting...")
                    self._start_backend()

                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self._shutdown()
        return 0

    def _start_vite(self) -> None:
        """Start the Vite dev server subprocess."""
        env = os.environ.copy()
        env["BROWSER"] = "none"  # Don't let Vite open browser itself
        env["FORCE_COLOR"] = "1"

        self._vite_proc = subprocess.Popen(
            ["npx", "vite", "--port", str(self.frontend_port), "--host", "0.0.0.0"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Stream logs with prefix
        _StreamLogger(self._vite_proc.stdout, "vite", "#60a5fa", console).start()
        _StreamLogger(self._vite_proc.stderr, "vite", "#fbbf24", console).start()

        console.print("[green]✓[/] Vite dev server starting on port", self.frontend_port)

    def _start_backend(self) -> None:
        """Start the FastAPI backend with uvicorn reload."""
        env = os.environ.copy()
        env["FLOWYML_NB_NAME"] = self.notebook_name
        env["FLOWYML_NB_FILE"] = self.file_path or ""
        env["FLOWYML_NB_SERVER"] = self.server or ""
        env["FLOWYML_NB_DEV_MODE"] = "1"

        self._backend_proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "flowyml_notebook.server:dev_app_factory",
                "--factory",
                "--host", "0.0.0.0",
                "--port", str(self.backend_port),
                "--reload",
                "--reload-dir", str(Path(__file__).parent),
                "--log-level", "info",
                "--no-access-log",
            ],
            cwd=PACKAGE_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        _StreamLogger(self._backend_proc.stdout, "api ", "#a78bfa", console).start()
        _StreamLogger(self._backend_proc.stderr, "api ", "#fbbf24", console).start()

        console.print("[green]✓[/] Backend starting on port", self.backend_port)

    def _open_browser(self) -> None:
        """Open the frontend URL in the default browser after a short delay."""
        def _open():
            time.sleep(2.0)  # Let servers fully start
            import webbrowser
            url = f"http://localhost:{self.frontend_port}"
            console.print(f"\n  [dim]Opening browser →[/] [bold underline #60a5fa]{url}[/]\n")
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    def _register_cleanup(self) -> None:
        """Register cleanup for all exit scenarios."""
        atexit.register(self._shutdown)

        def _signal_handler(signum, frame):
            self._shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    def _shutdown(self) -> None:
        """Gracefully stop all child processes."""
        if self._stopping:
            return
        self._stopping = True

        console.print("\n")
        console.print(
            Panel(
                "[dim]Shutting down...[/]",
                border_style="#ef4444",
                box=box.ROUNDED,
                expand=False,
                padding=(0, 2),
            )
        )

        for name, proc in [("Vite", self._vite_proc), ("Backend", self._backend_proc)]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    console.print(f"  [green]✓[/] {name} stopped")
                except Exception:
                    console.print(f"  [yellow]![/] {name} force-stopped")

        console.print("\n  [bold #3b82f6]👋 Goodbye![/]\n")


class ProdServer:
    """Production-like server: builds frontend, then serves everything from one process."""

    def __init__(
        self,
        notebook_name: str = "untitled",
        server: str | None = None,
        file_path: str | None = None,
        port: int = 8888,
        no_browser: bool = False,
    ):
        self.notebook_name = notebook_name
        self.server = server
        self.file_path = file_path
        self.port = port
        self.no_browser = no_browser

    def start(self) -> int:
        """Build frontend and start unified server."""
        console.clear()
        console.print(_styled_header())

        # Build frontend
        if not self._build_frontend():
            console.print("[yellow]⚠[/]  Frontend not built — serving API only")

        console.print()
        console.print(
            Panel(
                _info_table(
                    frontend_port=self.port,
                    backend_port=self.port,
                    notebook_name=self.notebook_name,
                    mode="Production Preview",
                    file_path=self.file_path,
                ),
                title="[bold #3b82f6]Server Dashboard[/]",
                border_style="#1e3a5f",
                box=box.ROUNDED,
                padding=(1, 0),
            )
        )
        console.print()

        # Open browser
        if not self.no_browser:
            import webbrowser
            url = f"http://localhost:{self.port}"
            console.print(f"  [dim]Opening browser →[/] [bold underline #60a5fa]{url}[/]\n")
            webbrowser.open(url)

        # Start unified backend
        from flowyml_notebook.core import Notebook
        from flowyml_notebook.server import NotebookServer

        nb = Notebook(name=self.notebook_name, server=self.server, file_path=self.file_path)

        if self.server:
            try:
                nb.connect(self.server)
            except Exception:
                console.print("[yellow]⚠[/]  Could not connect to server, continuing locally")

        server = NotebookServer(nb, port=self.port)
        try:
            server.run()
        except KeyboardInterrupt:
            console.print("\n  [bold #3b82f6]👋 Goodbye![/]\n")

        return 0

    def _build_frontend(self) -> bool:
        """Build the frontend if sources exist and dist is stale."""
        dist_dir = FRONTEND_DIR / "dist"
        src_dir = FRONTEND_DIR / "src"

        if not src_dir.exists():
            return False

        # Check if build is needed
        if dist_dir.exists() and not self._is_stale(src_dir, dist_dir):
            console.print("[green]✓[/] Frontend build is up-to-date")
            return True

        if not _ensure_frontend_deps():
            return False

        console.print("[yellow]⏳[/] Building frontend...")
        result = subprocess.run(
            ["npx", "vite", "build"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]✗[/] Frontend build failed:\n{result.stderr}")
            return False

        console.print("[green]✓[/] Frontend built successfully")
        return True

    @staticmethod
    def _is_stale(src_dir: Path, dist_dir: Path) -> bool:
        """Check if dist is older than any source file."""
        try:
            dist_mtime = max(f.stat().st_mtime for f in dist_dir.rglob("*") if f.is_file())
            src_mtime = max(f.stat().st_mtime for f in src_dir.rglob("*") if f.is_file())
            return src_mtime > dist_mtime
        except (ValueError, OSError):
            return True
