# Agent Guidelines for xservice

This document provides guidance for AI agents working on the `xservice` codebase.

## Core Principles

1.  **Adhere to the Agent Operating Model**: This project follows the **Codex-supervisor** / **Gemini-worker** model. Read `GEMINI.md` to understand your role and responsibilities.
2.  **Master Your Tools**: You are equipped with a powerful toolset. Use it to understand the codebase, make changes, and validate your work. Don't guess; `grep`, `read`, and `test`.
3.  **Respect Scopes**: Work only within your assigned file scope. Other agents are working in parallel. Modifying files outside your scope can lead to merge conflicts and rework.
4.  **Secrets Handling**: Never commit secrets to the repository. The project uses environment variables for configuration. See `GEMINI.md` for more details.
5.  **Incremental Changes**: Make small, atomic changes. This makes it easier to review your work and to recover from errors.
6.  **Run Validation**: Before finishing your work, run the validation steps defined in your instructions to ensure your changes have not broken anything.
