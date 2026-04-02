# xservice Architecture

This document outlines the architecture for the `xservice` application.

## Guiding Principles

- **Simplicity**: We prefer simple, well-understood technologies.
- **Standards-Based**: Adhering to open standards for interoperability.
- **Production-Ready**: Capable of running in a production environment.

## Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) on Python 3.12.
- **Database**: [PostgreSQL](https://www.postgresql.org/) for production, with [SQLite](https://www.sqlite.org/index.html) as a fallback for local development only.
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/) with [Alembic](https://alembic.sqlalchemy.org/) for database migrations.
- **Containerization**: [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) for consistent development and production environments.

## Application Structure

The application follows a `src-layout` and is organized into layers to separate concerns. The high-level module structure is as follows:

```
/
├── src/
│   └── xservice/
│       ├── main.py             # FastAPI app factory and router configuration
│       ├── cli.py              # Entry point for the command-line interface
│       │
│       ├── api/                # FastAPI routers, request handling, and dependencies
│       │   └── routes/
│       ├── providers/          # Clients for external services (e.g., X/Twitter)
│       ├── parsers/            # Data parsing and transformation logic
│       ├── services/           # Higher-level business logic and orchestration
│       │
│       ├── db.py               # Database session management
│       ├── models.py           # SQLAlchemy database models
│       ├── schemas.py          # Pydantic data transfer objects (DTOs)
│       │
│       ├── auth.py             # Authentication and authorization schemes
│       ├── settings.py         # Application configuration
│       └── logging.py          # Logging configuration
│
├── tests/                      # Automated tests
├── alembic/                    # Database migration scripts
├── pyproject.toml              # Project metadata and dependencies
└── docker-compose.yml          # Local development environment definition
```

### Architectural Layers

-   **`api`**: The entry point for all HTTP requests. This layer is responsible for request validation (using Pydantic `schemas`), calling into the `services` layer, and formatting the response. It should contain no business logic.
-   **`services`**: This layer orchestrates the application's business logic. It calls `providers` to fetch external data, uses `parsers` to clean it, and interacts with the `db` layer to persist data using `models`.
-   **`providers`**: Handles all communication with external APIs. It is responsible for making requests and handling external API-specific errors or data formats.
-   **`parsers`**: Contains the logic for transforming raw data from `providers` into the structured `schemas` used throughout the application.
-   **`db` / `models`**: The data persistence layer, managed by SQLAlchemy. `models.py` defines the database table structures.
