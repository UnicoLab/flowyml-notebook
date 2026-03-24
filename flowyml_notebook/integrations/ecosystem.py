"""UnicoLab ecosystem detection and status reporting.

Provides a registry that detects which UnicoLab packages are installed
and exposes version info, install commands, and documentation links.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Package Registry ──────────────────────────────────────────────────────────

_ECOSYSTEM_PACKAGES: dict[str, dict[str, str]] = {
    "kdp": {
        "display_name": "Keras Data Processor (KDP)",
        "description": "Keras-based data preprocessing layers — auto-configure feature processing",
        "install": "pip install kdp",
        "docs": "https://unicolab.github.io/keras-data-processor/",
        "repo": "https://github.com/UnicoLab/keras-data-processor",
        "import_name": "kdp",
    },
    "kerasfactory": {
        "display_name": "KerasFactory",
        "description": "38+ reusable Keras layers and production-ready model architectures",
        "install": "pip install kerasfactory",
        "docs": "https://unicolab.github.io/KerasFactory/latest/",
        "repo": "https://github.com/UnicoLab/KerasFactory",
        "import_name": "kerasfactory",
    },
    "mlpotion": {
        "display_name": "MLPotion",
        "description": "Modular ML pipeline building blocks for Keras, TensorFlow & PyTorch",
        "install": "pip install mlpotion",
        "docs": "https://unicolab.github.io/MLPotion/latest/",
        "repo": "https://github.com/UnicoLab/MLPotion",
        "import_name": "mlpotion",
    },
}


class UnicoLabEcosystem:
    """Detect and expose UnicoLab ecosystem packages."""

    @staticmethod
    def available_packages() -> dict[str, bool]:
        """Return ``{pkg_name: installed?}`` for each ecosystem package."""
        result: dict[str, bool] = {}
        for key, info in _ECOSYSTEM_PACKAGES.items():
            try:
                importlib.import_module(info["import_name"])
                result[key] = True
            except ImportError:
                result[key] = False
        return result

    @staticmethod
    def get_package_version(package_key: str) -> str | None:
        """Return installed version of an ecosystem package, or None."""
        info = _ECOSYSTEM_PACKAGES.get(package_key)
        if not info:
            return None
        try:
            mod = importlib.import_module(info["import_name"])
            return getattr(mod, "__version__", "unknown")
        except ImportError:
            return None

    @staticmethod
    def get_ecosystem_status() -> dict[str, Any]:
        """Full status report — versions, install instructions, links.

        Used by ``GET /api/ecosystem/status``.
        """
        packages: list[dict[str, Any]] = []
        installed_count = 0

        for key, info in _ECOSYSTEM_PACKAGES.items():
            version = UnicoLabEcosystem.get_package_version(key)
            is_installed = version is not None
            if is_installed:
                installed_count += 1

            packages.append({
                "key": key,
                "name": info["display_name"],
                "description": info["description"],
                "installed": is_installed,
                "version": version,
                "install_command": info["install"],
                "docs_url": info["docs"],
                "repo_url": info["repo"],
            })

        return {
            "packages": packages,
            "installed_count": installed_count,
            "total_count": len(_ECOSYSTEM_PACKAGES),
            "fully_integrated": installed_count == len(_ECOSYSTEM_PACKAGES),
            "install_all": "pip install 'flowyml-notebook[keras]'",
        }

    @staticmethod
    def is_available(package_key: str) -> bool:
        """Check if a specific package is installed."""
        info = _ECOSYSTEM_PACKAGES.get(package_key)
        if not info:
            return False
        try:
            importlib.import_module(info["import_name"])
            return True
        except ImportError:
            return False
