# Reva API

FastAPI backend for the Reva E-commerce AI Support Agent.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for PostgreSQL and Redis)

### Quick Start

1. Start the database and Redis:
   ```bash
   docker-compose up -d
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Copy environment file:
   ```bash
   cp .env.example .env
   ```

4. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```

5. Start the development server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

6. Open API docs at http://localhost:8000/api/v1/docs

### Running Celery Worker

```bash
uv run celery -A app.workers.celery_app worker --loglevel=info
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy app
```

## Project Structure

```
app/
├── main.py           # FastAPI application entry point
├── core/             # Configuration, security, dependencies
├── api/v1/           # API route handlers
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── workers/          # Celery background tasks
```
