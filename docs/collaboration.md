# 🤝 Team Collaboration

FlowyML Notebook is designed for teams. It leverages **GitHub** as a backend to provide seamless collaboration, versioning, and branching without requiring a centralized database.

## The `.flowyml-hub` Architecture

When you connect a GitHub repository, FlowyML Notebook creates a hidden `.flowyml-hub` directory structure that acts as a synchronized state manager:

```text
.flowyml-hub/
├── notebooks/          # Shared notebooks organized by project/experiment
├── recipes/            # Shared team recipe catalog
└── config.json         # Repository-level configuration
```

## GitHub-Based Sync

### 1. Connecting a Repository
You can connect to any GitHub repository via the **Collaboration** tab in the sidebar. You can use either HTTPS or SSH authentication.

### 2. Pushing & Pulling
- **Push**: Save your current notebook and experiment state to the hub.
- **Pull**: Get the latest updates from your teammates.
- **Conflict Resolution**: Since notebooks are stored as pure-Python files, resolving conflicts is handled natively by Git.

## Versioning & Branching

Leverage the full power of Git directly within the notebook interface:
- **Create Branches**: Experiment in isolation by creating a new branch (e.g., `feature/custom-loss-fn`).
- **Switching Contexts**: Seamlessly switch between branches to compare different experiment versions.
- **Commit History**: View the lineage of changes for every notebook and recipe.

## Collaborative Recipes

Share technical excellence by pushing your custom recipes to the team hub. This creates a shared "knowledge galaxy" where every researcher can benefit from optimized code snippets.
