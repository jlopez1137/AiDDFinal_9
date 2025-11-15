"""Data access helpers for the users table."""

from __future__ import annotations

from typing import Optional

import bcrypt

from datetime import datetime

from ..models.entities import User
from .db import execute, get_db, query_all, query_one

ALLOWED_ROLES = {"student", "staff", "admin"}


def _row_to_user(row) -> User:
    return User(
        user_id=row["user_id"],
        name=row["name"],
        email=row["email"],
        password_hash=row["password_hash"],
        role=row["role"],
        profile_image=row["profile_image"],
        department=row["department"],
        created_at=datetime.fromisoformat(row["created_at"].replace(" ", "T")),
        is_active=bool(row["is_active"]),
    )


def create_user(
    name: str,
    email: str,
    password_hash: str,
    role: str = "student",
    profile_image: Optional[str] = None,
    department: Optional[str] = None,
) -> User:
    """Insert a new user and return the persisted entity."""

    if role not in ALLOWED_ROLES:
        raise ValueError(f"Unsupported role '{role}'")

    db = get_db()
    cursor = execute(
        db,
        """
        INSERT INTO users (name, email, password_hash, role, profile_image, department)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, email, password_hash, role, profile_image, department),
    )
    return get_user_by_id(cursor.lastrowid, connection=db)


def get_user_by_id(user_id: int, connection=None) -> User | None:
    """Fetch a user by primary key."""

    db = connection or get_db()
    row = query_one(
        db,
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
    )
    return _row_to_user(row) if row else None


def get_user_by_email(email: str) -> User | None:
    """Fetch a user by unique email address."""

    db = get_db()
    row = query_one(
        db,
        "SELECT * FROM users WHERE email = ?",
        (email,),
    )
    return _row_to_user(row) if row else None


def list_users(include_inactive: bool = True) -> list[User]:
    """Return all users, optionally filtering out inactive entries."""

    db = get_db()
    query = "SELECT * FROM users"
    params: tuple = ()
    if not include_inactive:
        query += " WHERE is_active = 1"
    rows = query_all(db, query, params)
    return [_row_to_user(row) for row in rows]


def set_role(user_id: int, role: str) -> None:
    """Update the role for a user."""

    if role not in ALLOWED_ROLES:
        raise ValueError(f"Unsupported role '{role}'")

    db = get_db()
    execute(
        db,
        "UPDATE users SET role = ? WHERE user_id = ?",
        (role, user_id),
    )


def deactivate_user(user_id: int) -> None:
    """Soft delete a user record."""

    db = get_db()
    execute(
        db,
        "UPDATE users SET is_active = 0 WHERE user_id = ?",
        (user_id,),
    )


def activate_user(user_id: int) -> None:
    """Reactivate a previously deactivated user."""

    db = get_db()
    execute(
        db,
        "UPDATE users SET is_active = 1 WHERE user_id = ?",
        (user_id,),
    )


def verify_password(stored_hash: str, candidate: str) -> bool:
    """Compare a stored hash against a candidate password."""

    if not stored_hash:
        return False
    return bcrypt.checkpw(candidate.encode("utf-8"), stored_hash.encode("utf-8"))

