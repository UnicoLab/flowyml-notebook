"""Remote FlowyML server connection manager.

Connects to a centralized FlowyML instance via HTTP/WebSocket
for remote execution, asset management, scheduling, and deployment.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class FlowyMLConnection:
    """Connection to a centralized FlowyML server.

    Provides HTTP methods for all FlowyML API endpoints
    with automatic authentication and error handling.
    """

    def __init__(
        self,
        server_url: str,
        token: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        self.server_url = server_url.rstrip("/")
        self.token = token or os.getenv("FLOWYML_API_TOKEN", "")
        self.timeout = timeout
        self._client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._connected = False
        self._server_version: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def connect(self) -> dict:
        """Establish connection to the FlowyML server.

        Returns:
            Server health info dict.

        Raises:
            ConnectionError: If server is unreachable or auth fails.
        """
        self._client = httpx.Client(
            base_url=self.server_url,
            headers=self.headers,
            timeout=self.timeout,
        )

        try:
            response = self._client.get("/api/health")
            response.raise_for_status()
            health = response.json()
            self._connected = True
            self._server_version = health.get("version")
            logger.info(
                f"Connected to FlowyML server at {self.server_url} "
                f"(version: {self._server_version})"
            )
            return health
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to FlowyML server at {self.server_url}. "
                "Is the server running? Start it with: flowyml ui"
            ) from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ConnectionError(
                    "Authentication failed. Set FLOWYML_API_TOKEN environment variable "
                    "or pass token= to FlowyMLConnection."
                ) from None
            raise

    def disconnect(self) -> None:
        """Close the connection."""
        if self._client:
            self._client.close()
            self._client = None
        self._connected = False

    def _ensure_connected(self) -> None:
        if not self._connected or not self._client:
            raise ConnectionError("Not connected. Call connect() first.")

    # --- Pipeline Operations ---

    def list_pipelines(self) -> list[dict]:
        """List all pipelines on the server."""
        self._ensure_connected()
        response = self._client.get("/api/pipelines")
        response.raise_for_status()
        return response.json()

    def get_pipeline(self, pipeline_id: str) -> dict:
        """Get pipeline details."""
        self._ensure_connected()
        response = self._client.get(f"/api/pipelines/{pipeline_id}")
        response.raise_for_status()
        return response.json()

    # --- Run Operations ---

    def list_runs(self, pipeline_name: str | None = None, limit: int = 50) -> list[dict]:
        """List pipeline runs."""
        self._ensure_connected()
        params = {"limit": limit}
        if pipeline_name:
            params["pipeline_name"] = pipeline_name
        response = self._client.get("/api/runs", params=params)
        response.raise_for_status()
        return response.json()

    def get_run(self, run_id: str) -> dict:
        """Get run details."""
        self._ensure_connected()
        response = self._client.get(f"/api/runs/{run_id}")
        response.raise_for_status()
        return response.json()

    # --- Asset Operations ---

    def list_assets(self, asset_type: str | None = None) -> list[dict]:
        """List assets in the catalog."""
        self._ensure_connected()
        params = {}
        if asset_type:
            params["type"] = asset_type
        response = self._client.get("/api/assets", params=params)
        response.raise_for_status()
        return response.json()

    def get_asset(self, asset_id: str) -> dict:
        """Get asset details including lineage."""
        self._ensure_connected()
        response = self._client.get(f"/api/assets/{asset_id}")
        response.raise_for_status()
        return response.json()

    # --- Experiment Operations ---

    def list_experiments(self) -> list[dict]:
        """List all experiments."""
        self._ensure_connected()
        response = self._client.get("/api/experiments")
        response.raise_for_status()
        return response.json()

    def get_experiment(self, experiment_id: str) -> dict:
        """Get experiment details."""
        self._ensure_connected()
        response = self._client.get(f"/api/experiments/{experiment_id}")
        response.raise_for_status()
        return response.json()

    # --- Schedule Operations ---

    def list_schedules(self) -> list[dict]:
        """List all schedules."""
        self._ensure_connected()
        response = self._client.get("/api/schedules")
        response.raise_for_status()
        return response.json()

    def create_schedule(self, schedule_data: dict) -> dict:
        """Create a new schedule."""
        self._ensure_connected()
        response = self._client.post("/api/schedules", json=schedule_data)
        response.raise_for_status()
        return response.json()

    def delete_schedule(self, name: str) -> None:
        """Delete a schedule."""
        self._ensure_connected()
        response = self._client.delete(f"/api/schedules/{name}")
        response.raise_for_status()

    # --- Deployment Operations ---

    def list_deployments(self) -> list[dict]:
        """List active deployments."""
        self._ensure_connected()
        response = self._client.get("/api/deployments")
        response.raise_for_status()
        return response.json()

    def create_deployment(self, deployment_data: dict) -> dict:
        """Create a new model deployment."""
        self._ensure_connected()
        response = self._client.post("/api/deployments", json=deployment_data)
        response.raise_for_status()
        return response.json()

    # --- Execution Operations ---

    def submit_pipeline(self, pipeline_data: dict) -> dict:
        """Submit a pipeline for remote execution."""
        self._ensure_connected()
        response = self._client.post("/api/execution/submit", json=pipeline_data)
        response.raise_for_status()
        return response.json()

    def get_execution_status(self, execution_id: str) -> dict:
        """Get execution status."""
        self._ensure_connected()
        response = self._client.get(f"/api/execution/{execution_id}")
        response.raise_for_status()
        return response.json()

    # --- Metrics & Stats ---

    def get_metrics(self) -> dict:
        """Get server metrics."""
        self._ensure_connected()
        response = self._client.get("/api/metrics")
        response.raise_for_status()
        return response.json()

    # --- Config ---

    def get_config(self) -> dict:
        """Get server configuration."""
        self._ensure_connected()
        response = self._client.get("/api/config")
        response.raise_for_status()
        return response.json()

    # --- Generic Request ---

    def request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Make a generic API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path (e.g., "/api/custom/endpoint").
            json: Request body.
            params: Query parameters.

        Returns:
            Response JSON.
        """
        self._ensure_connected()
        response = self._client.request(method, path, json=json, params=params)
        response.raise_for_status()
        return response.json()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"FlowyMLConnection({self.server_url}, {status})"
