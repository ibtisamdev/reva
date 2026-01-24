"""Example Celery tasks for testing."""

from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.add")
def add(x: int, y: int) -> int:
    """Simple addition task for testing Celery setup."""
    return x + y


@celery_app.task(name="tasks.hello")
def hello(name: str = "World") -> str:
    """Simple hello task for testing Celery setup."""
    return f"Hello, {name}!"
