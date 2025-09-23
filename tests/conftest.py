"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import os
import tempfile
from typing import Iterator

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from src.config import Config
from src.models.user import db
from src.routes.crypto import crypto_bp
from src.routes.user import user_bp


@pytest.fixture(scope="session")
def app() -> Iterator[Flask]:
    """Provide a configured Flask application for the test session."""
    db_fd, db_path = tempfile.mkstemp()
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(crypto_bp, url_prefix="/api")

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="session")
def _db(app):  # noqa: PT004
    """Expose the SQLAlchemy database instance for tests."""
    return db


@pytest.fixture()
def client(app):
    """Return a Flask test client for HTTP endpoint validation."""
    return app.test_client()


@pytest.fixture()
def db_session(app) -> Iterator[Session]:
    """Provide a clean database session for each test case."""
    with app.app_context():
        yield db.session
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        db.session.remove()


@pytest.fixture(autouse=True)
def _clear_simulated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure tests run without leaked simulation environment overrides."""
    monkeypatch.delenv("ENABLE_SIMULATED_HEATMAP", raising=False)
    yield
