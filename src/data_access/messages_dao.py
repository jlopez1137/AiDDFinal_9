"""Data access helpers for threaded messaging."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import sqlite3

from ..models.entities import Message, Thread
from .db import execute, get_db, query_all, query_one

_SCHEMA_INSTRUCTIONS = (
    "Messaging tables are missing. Re-initialize the database with "
    "`flask --app src.app init-db` followed by `python -m src.data_access.seed`."
)


class MessagingSchemaError(RuntimeError):
    """Raised when threaded messaging tables are unavailable."""


def _raise_schema_error() -> None:
    raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS)


def _row_to_message(row) -> Message:
    row_keys = row.keys() if hasattr(row, "keys") else ()
    raw_thread_id = row["thread_id"] if "thread_id" in row_keys else None
    thread_id = raw_thread_id if raw_thread_id is not None else row["message_id"]
    return Message(
        message_id=row["message_id"],
        thread_id=thread_id,
        sender_id=row["sender_id"],
        receiver_id=row["receiver_id"],
        content=row["content"],
        timestamp=datetime.fromisoformat(row["timestamp"].replace(" ", "T")),
    )


def _row_to_thread(row) -> Thread:
    return Thread(
        thread_id=row["thread_id"],
        context_type=row["context_type"],
        context_id=row["context_id"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"].replace(" ", "T")),
    )


def create_thread(context_type: str, context_id: Optional[int], created_by: int) -> Thread:
    """Create a new conversation thread."""

    db = get_db()
    try:
        cursor = execute(
            db,
            """
            INSERT INTO threads (context_type, context_id, created_by)
            VALUES (?, ?, ?)
            """,
            (context_type, context_id, created_by),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return get_thread(cursor.lastrowid, connection=db)


def post_message(
    thread_id: int,
    sender_id: int,
    receiver_id: int,
    content: str,
) -> Message:
    """Add a message to an existing thread."""

    db = get_db()
    try:
        cursor = execute(
            db,
            """
            INSERT INTO messages (thread_id, sender_id, receiver_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, sender_id, receiver_id, content),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return get_message_by_id(cursor.lastrowid, connection=db)


def get_thread(thread_id: int, connection=None) -> Thread | None:
    """Fetch a single thread record."""

    db = connection or get_db()
    try:
        row = query_one(
            db,
            "SELECT * FROM threads WHERE thread_id = ?",
            (thread_id,),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return _row_to_thread(row) if row else None


def get_message_by_id(message_id: int, connection=None) -> Message | None:
    """Fetch a single message."""

    db = connection or get_db()
    try:
        row = query_one(
            db,
            "SELECT * FROM messages WHERE message_id = ?",
            (message_id,),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return _row_to_message(row) if row else None


def get_messages(thread_id: int) -> list[Message]:
    """Return all messages for a thread ordered ascending."""

    db = get_db()
    try:
        rows = query_all(
            db,
            """
            SELECT * FROM messages
            WHERE thread_id = ?
            ORDER BY timestamp ASC
            """,
            (thread_id,),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return [_row_to_message(row) for row in rows]


def get_messages_since(thread_id: int, timestamp: str) -> list[Message]:
    """Return messages posted after the provided timestamp."""

    db = get_db()
    try:
        rows = query_all(
            db,
            """
            SELECT * FROM messages
            WHERE thread_id = ? AND timestamp > ?
            ORDER BY timestamp ASC
            """,
            (thread_id, timestamp),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return [_row_to_message(row) for row in rows]


def get_last_message(thread_id: int) -> Message | None:
    """Return the most recent message in a thread."""

    db = get_db()
    try:
        row = query_one(
            db,
            """
            SELECT * FROM messages
            WHERE thread_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (thread_id,),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return _row_to_message(row) if row else None


def list_threads_for_admin() -> list[dict]:
    """Return thread metadata ordered by recent activity."""

    db = get_db()
    try:
        rows = query_all(
            db,
            """
            SELECT
                t.*,
                MAX(m.timestamp) AS last_activity,
                COUNT(m.message_id) AS message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.thread_id
            GROUP BY t.thread_id
            ORDER BY (last_activity IS NULL), last_activity DESC
            """,
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return rows


def list_threads_for_user(user_id: int) -> list[dict]:
    """Return threads the user participates in ordered by last activity."""

    db = get_db()
    try:
        rows = query_all(
            db,
            """
            SELECT
                t.*,
                MAX(m.timestamp) AS last_activity,
                COUNT(m.message_id) AS message_count
            FROM threads t
            JOIN messages m ON m.thread_id = t.thread_id
            WHERE m.sender_id = ? OR m.receiver_id = ?
            GROUP BY t.thread_id
            ORDER BY (last_activity IS NULL), last_activity DESC
            """,
            (user_id, user_id),
        )
    except sqlite3.OperationalError as exc:
        raise MessagingSchemaError(_SCHEMA_INSTRUCTIONS) from exc
    return rows

