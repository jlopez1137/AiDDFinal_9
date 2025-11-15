"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Generator

import pytest
from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app import create_app
from src.config import TestingConfig
from src.data_access import bookings_dao, messages_dao, resources_dao, seed, users_dao
from src.data_access.db import get_db, init_db


class _TestConfig(TestingConfig):
    DATABASE_URL: str = ""


@pytest.fixture()
def app(tmp_path: Path) -> Generator[Flask, None, None]:
    """Configure a Flask application for testing with a temp SQLite database."""

    db_path = tmp_path / "test.db"
    _TestConfig.DATABASE_URL = f"sqlite:///{db_path}"
    application = create_app(_TestConfig)
    with application.app_context():
        init_db(application)
        seed.seed()
    yield application


@pytest.fixture()
def client(app: Flask):
    """Flask test client."""

    return app.test_client()


@pytest.fixture()
def runner(app: Flask):
    """Flask CLI runner."""

    return app.test_cli_runner()


@pytest.fixture()
def db(app: Flask):
    """Provide a database connection for direct queries."""

    with app.app_context():
        yield get_db()


@pytest.fixture()
def admin_user(app: Flask):
    with app.app_context():
        return users_dao.get_user_by_email("ada.admin@campus.edu")


@pytest.fixture()
def staff_user(app: Flask):
    with app.app_context():
        return users_dao.get_user_by_email("sam.staff@campus.edu")


@pytest.fixture()
def student_user(app: Flask):
    with app.app_context():
        return users_dao.get_user_by_email("alice@student.edu")


@pytest.fixture()
def restricted_resource(app: Flask):
    with app.app_context():
        staff = users_dao.get_user_by_email("sam.staff@campus.edu")
        resources = resources_dao.list_resources_for_owner(staff.user_id)
        for resource in resources:
            if resource.requires_approval:
                return resource
        raise AssertionError("Expected restricted resource in seed data.")


@pytest.fixture()
def pending_booking(app: Flask):
    with app.app_context():
        bookings = bookings_dao.list_pending_approvals()
        return bookings[0]


@pytest.fixture()
def booking_thread(app: Flask, pending_booking):
    with app.app_context():
        rows = messages_dao.list_threads_for_admin()
        for row in rows:
            if row["context_type"] == "booking" and row["context_id"] == pending_booking.booking_id:
                return messages_dao.get_thread(row["thread_id"])
        raise AssertionError("Expected booking thread not found in seed data.")

