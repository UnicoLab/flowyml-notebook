"""SQL cell execution engine with DataFrame bridge.

Executes SQL queries in notebook cells and automatically converts
results to pandas DataFrames. Supports multiple data sources:
- DuckDB (in-process, default)
- SQLAlchemy connections (PostgreSQL, MySQL, SQLite, etc.)
- FlowyML's built-in SQL catalog
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SQLEngine:
    """SQL execution engine for notebook cells.

    Supports executing SQL against:
    1. DuckDB (default): Query DataFrames directly with SQL
    2. Named connections: External databases via SQLAlchemy
    3. FlowyML catalog: Query the artifact catalog
    """

    def __init__(self):
        self._connections: dict[str, Any] = {}
        self._duckdb_conn = None

    def _get_duckdb(self):
        """Lazily initialize DuckDB connection."""
        if self._duckdb_conn is None:
            try:
                import duckdb
                self._duckdb_conn = duckdb.connect()
            except ImportError:
                raise ImportError(
                    "DuckDB required for SQL cells. Install with: "
                    "pip install 'flowyml-notebook[sql]'"
                ) from None
        return self._duckdb_conn

    def add_connection(self, name: str, connection_string: str) -> None:
        """Register a named database connection.

        Args:
            name: Connection name (use in SQL with `FROM name.table`).
            connection_string: SQLAlchemy connection string.
        """
        try:
            from sqlalchemy import create_engine
            engine = create_engine(connection_string)
            self._connections[name] = engine
            logger.info(f"Registered SQL connection: {name}")
        except ImportError:
            raise ImportError("SQLAlchemy required for external connections") from None

    def execute(
        self,
        query: str,
        namespace: dict[str, Any] | None = None,
        connection: str | None = None,
    ) -> tuple[Any, dict]:
        """Execute a SQL query and return results as a DataFrame.

        Args:
            query: SQL query string.
            namespace: Notebook namespace (DataFrames are auto-registered as tables).
            connection: Named connection to use. None = use DuckDB with namespace tables.

        Returns:
            Tuple of (DataFrame, info_dict).
        """
        import pandas as pd

        query = query.strip()
        if not query:
            return pd.DataFrame(), {"rows": 0, "columns": []}

        # Strip leading comments
        lines = query.split("\n")
        clean_lines = [l for l in lines if not l.strip().startswith("--")]
        query = "\n".join(clean_lines).strip()

        if connection and connection in self._connections:
            return self._execute_sqlalchemy(query, connection)
        else:
            return self._execute_duckdb(query, namespace or {})

    def _execute_duckdb(
        self, query: str, namespace: dict[str, Any]
    ) -> tuple[Any, dict]:
        """Execute SQL via DuckDB with namespace DataFrames as tables."""
        import pandas as pd

        conn = self._get_duckdb()

        # Register DataFrames from namespace as temporary views
        for name, value in namespace.items():
            if isinstance(value, pd.DataFrame):
                try:
                    conn.register(name, value)
                except Exception:
                    pass  # Skip if name conflicts or invalid

        try:
            result = conn.execute(query)
            df = result.fetchdf()
            info = {
                "rows": len(df),
                "columns": list(df.columns),
                "engine": "duckdb",
            }
            return df, info
        except Exception as e:
            logger.error(f"DuckDB query error: {e}")
            raise

    def _execute_sqlalchemy(self, query: str, connection: str) -> tuple[Any, dict]:
        """Execute SQL via SQLAlchemy connection."""
        import pandas as pd

        engine = self._connections[connection]
        try:
            df = pd.read_sql(query, engine)
            info = {
                "rows": len(df),
                "columns": list(df.columns),
                "engine": "sqlalchemy",
                "connection": connection,
            }
            return df, info
        except Exception as e:
            logger.error(f"SQLAlchemy query error: {e}")
            raise


# Module-level singleton
_sql_engine = None


def get_sql_engine() -> SQLEngine:
    """Get the global SQL engine instance."""
    global _sql_engine
    if _sql_engine is None:
        _sql_engine = SQLEngine()
    return _sql_engine


def execute_sql(
    query: str,
    namespace: dict[str, Any] | None = None,
    connection: str | None = None,
) -> tuple[Any, dict]:
    """Execute a SQL query (module-level convenience function).

    Args:
        query: SQL query.
        namespace: Notebook namespace for DuckDB table registration.
        connection: Named connection.

    Returns:
        Tuple of (DataFrame, info_dict).
    """
    engine = get_sql_engine()
    return engine.execute(query, namespace, connection)
