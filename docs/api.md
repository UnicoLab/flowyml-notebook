# 📚 API Reference

FlowyML Notebook provides a programmatic API for advanced users and integrations.

## Core SDK

The `flowyml_notebook` package provides decorators and utilities for building reactive workflows.

### `@notebook`
Main decorator to define a reactive module.

### `@cell`
Defines a specific execution unit.

## CLI Reference

### `fml-notebook start`
Launches the GUI server.

**Options:**
- `--port`: Port to run the server on (default: 8880).
- `--host`: Host address (default: 127.0.0.1).

### `fml-notebook build`
Pre-compiles notebooks for production deployment.
