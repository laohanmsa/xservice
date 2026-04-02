# syntax=docker/dockerfile:1

# --- Builder Stage ---
# Installs dependencies using Poetry
FROM python:3.12-slim-bullseye AS builder

WORKDIR /app

# Install poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN pip install poetry

# Copy dependency definition files
COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN poetry install --no-root --no-dev

# --- Final Stage ---
# Creates the final production image
FROM python:3.12-slim-bullseye AS final

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app/src

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY ./src ./src

# Set the command to run the application
CMD ["uvicorn", "xservice.main:app", "--host", "0.0.0.0", "--port", "8000"]
