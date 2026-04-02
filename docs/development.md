# Local Development Setup

This guide explains how to set up the `xservice` for local development.

There are two primary ways to develop locally:
1.  **Using Docker Compose (Recommended)**: For a consistent environment that mirrors production.
2.  **Using a local Python environment**: For running the application directly on your machine.

## Prerequisites

- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Python 3.12](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (if using the Docker-based setup)

## Initial Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd xservice
    ```

2.  **Create your `.env` file**:
    The application requires an `.env` file for configuration. The provided bootstrap script automates this for local development.

    ```bash
    sh scripts/bootstrap_local.sh
    ```

    This will create a new `.env` file with secure, random credentials for a local PostgreSQL database, ready to be used with Docker Compose. It will not overwrite an existing `.env` file. By default, the application is configured to use the PostgreSQL database via Docker Compose.

    The app also supports a built-in API playground at `/playground`. By default,
    it uses `PLAYGROUND_DEFAULT_API_KEY`, which is intended for local/demo use and
    is prefilled in the Web UI. Override that value in your `.env` file if you do
    not want the default shared key.

## Development with Docker Compose

This is the recommended approach for a consistent environment that mirrors production.

1.  **Generate your environment file**:
    If you haven't already, run the bootstrap script:
    ```bash
    sh scripts/bootstrap_local.sh
    ```

2.  **Build and run the services**:
    ```bash
    docker compose up --build
    ```

    The application will be running at `http://localhost:8000`. The `app` service has a volume mount, so changes to your local code will automatically be reflected in the running container.

## Development with a Local Python Environment (Alternative)

If you prefer to run the application directly on your machine, you can use a local Python environment.

1.  **Install dependencies**:
    This project uses [Poetry](https://python-poetry.org/) for dependency management. After installing poetry, run:
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all necessary packages from `pyproject.toml`.

2.  **Activate the virtual environment**:
    ```bash
    poetry shell
    ```

3.  **Configure your environment**:
    The default setup uses PostgreSQL via Docker. To run the Python app locally against the Dockerized database, simply run `sh scripts/bootstrap_local.sh` and then `docker compose up -d postgres`. The `DATABASE_URL` in the generated `.env` file will connect to it correctly.

    If you prefer to use a local SQLite database, first create an `.env` file by running `sh scripts/bootstrap_local.sh`, then edit the `.env` file. Comment out the `DATABASE_URL` for PostgreSQL and uncomment the one for SQLite.

4.  **Start the application**:
    With the virtual environment activated, run:
    ```bash
    uvicorn xservice.main:app --reload
    ```
    The application will be running at `http://localhost:8000`.

## Running Tests

To run the test suite:
```bash
poetry run pytest
```
(Further details on testing to be added in a future phase).
