"""CLI entry point for FlowyML Notebook.

Provides the `fml-notebook` command for launching, running,
and managing notebooks from the terminal.
"""

from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="fml-notebook",
        description="🌊 FlowyML Notebook — Production-grade reactive notebook",
    )
    parser.add_argument("--version", action="version", version="flowyml-notebook 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- dev (★ primary dev workflow) ---
    dev_parser = subparsers.add_parser("dev", help="🔥 Launch in dev mode (hot reload)")
    dev_parser.add_argument("--name", default="untitled", help="Notebook name")
    dev_parser.add_argument("--server", help="FlowyML server URL")
    dev_parser.add_argument("--file", help="Load notebook from .py file")
    dev_parser.add_argument("--frontend-port", type=int, default=3000, help="Vite dev server port")
    dev_parser.add_argument("--backend-port", type=int, default=8888, help="API server port")
    dev_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

    # --- start ---
    start_parser = subparsers.add_parser("start", help="Launch notebook (production build)")
    start_parser.add_argument("--name", default="untitled", help="Notebook name")
    start_parser.add_argument("--server", help="FlowyML server URL")
    start_parser.add_argument("--port", type=int, default=8888, help="Server port")
    start_parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    start_parser.add_argument("--file", help="Load notebook from .py file")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Execute a notebook file")
    run_parser.add_argument("file", help="Notebook .py file to execute")
    run_parser.add_argument("--server", help="FlowyML server URL for remote execution")

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Export notebook")
    export_parser.add_argument("file", help="Notebook .py file")
    export_parser.add_argument(
        "--format", choices=["pipeline", "html", "pdf", "docker"], default="pipeline",
        help="Export format"
    )
    export_parser.add_argument("--output", "-o", help="Output file path")

    # --- app ---
    app_parser = subparsers.add_parser("app", help="Deploy notebook as web app")
    app_parser.add_argument("file", help="Notebook .py file")
    app_parser.add_argument("--port", type=int, default=8501, help="App server port")
    app_parser.add_argument("--layout", choices=["linear", "grid", "tabs", "sidebar", "dashboard"],
                           default="linear", help="App layout")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List notebooks on server")
    list_parser.add_argument("--server", required=True, help="FlowyML server URL")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    try:
        if args.command == "dev":
            return _cmd_dev(args)
        elif args.command == "start":
            return _cmd_start(args)
        elif args.command == "run":
            return _cmd_run(args)
        elif args.command == "export":
            return _cmd_export(args)
        elif args.command == "app":
            return _cmd_app(args)
        elif args.command == "list":
            return _cmd_list(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        logger.debug("Full traceback:", exc_info=True)
        return 1


def _cmd_dev(args) -> int:
    """Launch in dev mode with hot reload (Vite + FastAPI)."""
    from flowyml_notebook.dev_server import DevServer

    dev = DevServer(
        notebook_name=args.name,
        server=args.server,
        file_path=args.file,
        frontend_port=args.frontend_port,
        backend_port=args.backend_port,
        no_browser=args.no_browser,
    )
    return dev.start()


def _cmd_start(args) -> int:
    """Launch the notebook with production frontend build."""
    from flowyml_notebook.dev_server import ProdServer

    prod = ProdServer(
        notebook_name=args.name,
        server=args.server,
        file_path=args.file,
        port=args.port,
        no_browser=args.no_browser,
    )
    return prod.start()


def _cmd_run(args) -> int:
    """Execute a notebook file."""
    from flowyml_notebook.core import Notebook

    print(f"🚀 Running notebook: {args.file}")
    nb = Notebook(file_path=args.file)

    if args.server:
        nb.connect(args.server)
        print(f"   Connected to {args.server}")

    results = nb.run()

    success_count = sum(1 for r in results if r.success)
    total = len(results)
    failed = total - success_count

    print(f"\n{'✅' if failed == 0 else '⚠️'} Results: {success_count}/{total} cells succeeded")

    if failed > 0:
        for r in results:
            if not r.success:
                print(f"   ❌ Cell {r.cell_id}: {r.error}")
        return 1

    return 0


def _cmd_export(args) -> int:
    """Export a notebook to various formats."""
    from flowyml_notebook.core import Notebook

    nb = Notebook(file_path=args.file)

    if args.format == "pipeline":
        from flowyml_notebook.deployer import promote_to_pipeline
        path = promote_to_pipeline(nb.notebook, args.output)
        print(f"📄 Pipeline exported: {path}")
    elif args.format in ("html", "pdf"):
        from flowyml_notebook.reporting import generate_report
        path = generate_report(nb.notebook, format=args.format, output_path=args.output)
        print(f"📊 Report exported: {path}")
    elif args.format == "docker":
        from flowyml_notebook.deployer import generate_dockerfile
        path = generate_dockerfile(nb.notebook, args.output or "Dockerfile")
        print(f"🐳 Dockerfile generated: {path}")

    return 0


def _cmd_app(args) -> int:
    """Deploy notebook as a web app."""
    from flowyml_notebook.core import Notebook
    from flowyml_notebook.ui.app_mode import AppMode, LayoutType

    nb = Notebook(file_path=args.file)

    # Execute all cells first
    print(f"🚀 Executing notebook: {args.file}")
    nb.run()

    # Configure app mode
    app = AppMode(nb)
    app.configure(layout=args.layout)

    print(f"\n🌊 FlowyML App")
    print(f"   Source: {args.file}")
    print(f"   Layout: {args.layout}")
    print(f"   URL:    http://localhost:{args.port}")
    print(f"\n   Press Ctrl+C to stop\n")

    # Start app server
    import uvicorn
    from flowyml_notebook.server import create_app_server

    app_server = create_app_server(nb, app)

    import webbrowser
    webbrowser.open(f"http://localhost:{args.port}")

    uvicorn.run(app_server, host="0.0.0.0", port=args.port, log_level="warning")
    return 0


def _cmd_list(args) -> int:
    """List notebooks on a remote server."""
    from flowyml_notebook.connection import FlowyMLConnection

    conn = FlowyMLConnection(args.server)
    conn.connect()
    print(f"📚 Notebooks on {args.server}:")
    # This would call the notebooks API endpoint
    print("   (notebook listing endpoint not yet implemented)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
