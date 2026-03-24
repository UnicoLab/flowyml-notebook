"""UnicoLab Ecosystem Integrations for FlowyML Notebook.

Provides adapters for:
- KDP (keras-data-processor): Keras-based data preprocessing layers
- KerasFactory: Reusable Keras model architectures & layers
- MLPotion: Modular ML pipeline building blocks

All packages are optional — adapters gracefully degrade when not installed.
"""

from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem

__all__ = ["UnicoLabEcosystem"]
