# xservice

An operator-facing backend service for accessing X/Twitter data.

## Overview

`xservice` provides a REST API and a command-line interface (CLI) for programmatic access to the X/Twitter platform. It is designed for operators to manage and utilize X accounts for data retrieval, parsing, and storage.

-   **API**: A RESTful API providing access to user information, tweets, search, and administrative functions.
-   **CLI**: A command-line tool for interacting with the API from the terminal.
-   **Authentication**: API key-based authentication (`X-API-KEY` header).
-   **Database**: PostgreSQL for production, with a SQLite fallback for local development.
-   **Deployment**: Containerized with Docker and ready for Docker Compose.

## Getting Started

### Local Development

1.  **Prerequisites**: Requires Python 3.12+ and [Poetry](https://python-poetry.org/).

2.  **Install dependencies**:
    ```bash
    poetry install
    ```

3.  **Bootstrap environment**: Create a local `.env` file for configuration.
    ```bash
    ./scripts/bootstrap_local.sh
    ```

4.  **Run database migrations**:
    ```bash
    # For local development with SQLite
    poetry run alembic upgrade head
    ```

5.  **Run the API server**:
    ```bash
    poetry run uvicorn xservice.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

The API is versioned under the `/api/v1` prefix. The major route groups are:

-   `/health`: Health checks for the service.
-   `/admin`: Administrative endpoints for managing service accounts.
-   `/search`: Endpoints for searching X/Twitter.
-   `/users`: Endpoints for retrieving user profiles, timelines, followers, and other user-related data.
-   `/tweets`: Endpoints for retrieving tweet details, retweeters, and favoriters.

## Command-Line Interface (CLI)

The project includes a CLI tool, `xservice-cli`, for interacting with the API. The entry point is defined in `pyproject.toml`.

### Usage

The CLI provides commands for accessing the various API endpoints.

```bash
# Check API health
poetry run xservice-cli health

# Search for tweets
poetry run xservice-cli search "my query"

# Get a user's profile
poetry run xservice-cli user profile "username"

# Get a tweet's details
poetry run xservice-cli tweet detail "123456789"
```

You can configure the API endpoint and key via environment variables (`XSERVICE_BASE_URL`, `XSERVICE_API_KEY`) or command-line arguments.
