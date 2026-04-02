# Gemini Worker Guidance for xservice

This document provides specific instructions for Gemini workers to maintain the integrity of the `xservice` project.

## Agent Operating Model

This project is a collaboration between a **Codex-supervisor** (a human or lead AI) and **Gemini-workers** (AIs focused on specific tasks).

-   The **Codex-supervisor** is responsible for the overall architecture, project setup, and defining the scopes of work.
-   **Gemini-workers** are responsible for implementing features and fixes within their assigned scope.

This model allows for parallel development. It is crucial that workers respect their assigned scopes to avoid conflicts.

## Secret Management

**DO NOT COMMIT SECRENTS TO THE REPOSITORY.**

This project uses a `.env` file for local development and environment variables in production for managing secrets and configuration.

-   The `.env` file is listed in `.gitignore` and should never be committed.
-   For production, secrets will be injected as environment variables.
-   When working locally, developers are expected to create their own `.env` file. The `scripts/bootstrap_local.sh` script can be used to create a default file.

When you need to add a new secret or configuration variable:
1.  Update `scripts/bootstrap_local.sh` to include the new variable with a sensible default.
2.  Document the new variable in `docs/development.md`.
3.  Use the variable in the application via `os.getenv('MY_NEW_VARIABLE')`.

## Architecture

The project architecture is documented in `docs/architecture.md`. All code changes must align with this architecture.

Key points:
- FastAPI for the web framework.
- PostgreSQL for the production database.
- Docker for containerization.

Before implementing new features, review the architecture document to ensure your changes are consistent with the project's design.
