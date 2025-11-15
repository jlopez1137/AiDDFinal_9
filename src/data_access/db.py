"""SQLite connection management utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

import click
from flask import Flask, current_app, g


def _create_connection(database_url: str) -> sqlite3.Connection:
    """Instantiate a SQLite connection for the provided URL."""

    if database_url == "sqlite:///:memory:":
        db_path = ":memory:"
    elif database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "", 1)
    elif database_url.startswith("sqlite://"):
        db_path = database_url.replace("sqlite://", "", 1)
    else:
        raise ValueError("Only sqlite database URLs are supported in this implementation.")

    connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def get_db() -> sqlite3.Connection:
    """Return a cached connection for the request context."""

    if "db_conn" not in g:
        database_url = current_app.config["DATABASE_URL"]
        g.db_conn = _create_connection(database_url)
    return g.db_conn  # type: ignore[return-value]


def close_db(exception: Exception | None = None) -> None:
    """Close the stored connection at the end of the request."""

    connection = g.pop("db_conn", None)
    if connection is not None:
        connection.close()


def execute(db: sqlite3.Connection, query: str, params: Sequence[Any] | None = None) -> sqlite3.Cursor:
    """Execute a write query and commit immediately."""

    cursor = db.execute(query, params or [])
    db.commit()
    return cursor


def query_all(db: sqlite3.Connection, query: str, params: Sequence[Any] | None = None) -> list[sqlite3.Row]:
    """Execute a read query returning multiple rows."""

    cursor = db.execute(query, params or [])
    return cursor.fetchall()


def query_one(db: sqlite3.Connection, query: str, params: Sequence[Any] | None = None) -> sqlite3.Row | None:
    """Execute a read query returning a single row."""

    cursor = db.execute(query, params or [])
    return cursor.fetchone()


def init_db(app: Flask | None = None) -> None:
    """Initialize the database schema by executing the SQL script."""

    app = app or current_app
    with app.app_context():
        db = get_db()
        schema_path = Path(app.root_path).parent / "campus_resource_hub_schema.sql"
        with schema_path.open("r", encoding="utf-8") as sql_file:
            db.executescript(sql_file.read())
        db.commit()


def init_app(app: Flask) -> None:
    """Wire database helpers into the Flask app."""

    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Clear existing data and create new tables."""

        init_db(app)
        click.echo("Initialized the database.")

