"""IPython magic commands for FlowyML Notebook.

Provides convenient magic commands for common FlowyML operations
when using the notebook in interactive/CLI mode.
"""

import logging

logger = logging.getLogger(__name__)

# Lazy flag to track registration
_MAGICS_REGISTERED = False


def register_magics(notebook) -> None:
    """Register FlowyML magic commands with the IPython kernel.

    Args:
        notebook: The Notebook instance to bind magics to.
    """
    global _MAGICS_REGISTERED

    try:
        from IPython.core.magic import register_line_magic, register_cell_magic
        from IPython import get_ipython
    except ImportError:
        logger.info("IPython not available, skipping magic registration")
        return

    ip = get_ipython()
    if ip is None:
        return

    if _MAGICS_REGISTERED:
        return

    @register_line_magic
    def connect(line):
        """Connect to a FlowyML server. Usage: %connect https://flowyml.company.com"""
        url = line.strip()
        if not url:
            print("Usage: %connect <server_url>")
            return
        notebook.connect(url)
        print(f"✅ Connected to {url}")

    @register_line_magic
    def run(line):
        """Run the notebook pipeline. Usage: %run [--remote]"""
        remote = "--remote" in line
        if remote and notebook._connection:
            print("🚀 Executing on remote server...")
        else:
            print("🚀 Executing locally...")
        results = notebook.run()
        success_count = sum(1 for r in results if r.success)
        total = len(results)
        print(f"{'✅' if success_count == total else '⚠️'} {success_count}/{total} cells succeeded")

    @register_line_magic
    def schedule(line):
        """Schedule the notebook. Usage: %schedule cron "0 2 * * *" """
        parts = line.strip().split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: %schedule cron \"0 2 * * *\"")
            print("       %schedule interval 4  (hours)")
            return
        sched_type, value = parts
        value = value.strip('"').strip("'")
        if sched_type == "cron":
            result = notebook.schedule(cron=value)
        elif sched_type == "interval":
            result = notebook.schedule(interval_hours=int(value))
        else:
            print(f"Unknown schedule type: {sched_type}. Use 'cron' or 'interval'.")
            return
        print(f"⏰ Scheduled: {result}")

    @register_line_magic
    def deploy(line):
        """Deploy a model. Usage: %deploy model_variable_name"""
        model_name = line.strip()
        if not model_name:
            print("Usage: %deploy <model_variable_name>")
            return
        result = notebook.deploy(model_name)
        print(f"🚀 Deployed: {result}")

    @register_line_magic
    def assets(line):
        """List assets. Usage: %assets [type]"""
        asset_type = line.strip() or None
        if notebook._connection:
            items = notebook._connection.list_assets(asset_type)
            if items:
                for item in items:
                    print(f"  📦 {item.get('name', 'unnamed')} ({item.get('type', 'unknown')})")
            else:
                print("No assets found.")
        else:
            print("⚠️ Not connected to server. Use %connect first.")

    @register_line_magic
    def viz(line):
        """Open visualization. Usage: %viz dag|metrics|drift|leaderboard"""
        viz_type = line.strip() or "dag"
        print(f"📊 Opening {viz_type} visualization...")
        # Note: actual visualization opening handled by the GUI frontend;
        # in CLI mode this would open a browser tab

    @register_line_magic
    def promote(line):
        """Export as production pipeline. Usage: %promote [output_path.py]"""
        output_path = line.strip() or None
        path = notebook.promote(output_path)
        print(f"📄 Exported pipeline to: {path}")

    @register_line_magic
    def save(line):
        """Save notebook. Usage: %save [path.py]"""
        path = line.strip() or None
        saved = notebook.save(path)
        print(f"💾 Saved to: {saved}")

    @register_line_magic
    def variables(line):
        """Show all variables. Usage: %variables"""
        vars_dict = notebook.session.get_variables()
        if vars_dict:
            for name, info in sorted(vars_dict.items()):
                shape = f" shape={info['shape']}" if 'shape' in info else ""
                length = f" len={info['length']}" if 'length' in info else ""
                print(f"  {name}: {info['type']}{shape}{length}")
        else:
            print("No user variables defined.")

    @register_cell_magic
    def sql(line, cell):
        """Execute SQL cell. Usage: %%sql [result_var=df]"""
        result_var = line.strip() or "df"
        try:
            from flowyml_notebook.sql.engine import execute_sql
            df, info = execute_sql(cell, notebook.session._namespace)
            notebook.session.set_variable(result_var, df)
            print(f"✅ Query returned {len(df)} rows → stored in '{result_var}'")
            return df
        except ImportError:
            print("❌ SQL engine not available. Install with: pip install 'flowyml-notebook[sql]'")
        except Exception as e:
            print(f"❌ SQL error: {e}")

    _MAGICS_REGISTERED = True
    logger.info("FlowyML magic commands registered")
