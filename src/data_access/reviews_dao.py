"Data access helpers for resource reviews."

from __future__ import annotations

from typing import Optional

from datetime import datetime

from ..models.entities import Review
from .db import execute, get_db, query_all, query_one


def _row_to_review(row) -> Review:
    return Review(
        review_id=row["review_id"],
        resource_id=row["resource_id"],
        reviewer_id=row["reviewer_id"],
        rating=row["rating"],
        comment=row["comment"],
        timestamp=datetime.fromisoformat(row["timestamp"].replace(" ", "T")),
    )


def create_review(resource_id: int, reviewer_id: int, rating: int, comment: str) -> Review:
    """Insert a new review for a completed booking."""

    db = get_db()
    cursor = execute(
        db,
        """
        INSERT INTO reviews (resource_id, reviewer_id, rating, comment)
        VALUES (?, ?, ?, ?)
        """,
        (resource_id, reviewer_id, rating, comment),
    )
    return get_review_by_id(cursor.lastrowid, connection=db)


def get_review_by_id(review_id: int, connection=None) -> Review | None:
    """Fetch a review by primary key."""

    db = connection or get_db()
    row = query_one(
        db,
        "SELECT * FROM reviews WHERE review_id = ?",
        (review_id,),
    )
    return _row_to_review(row) if row else None


def list_reviews_for_resource(resource_id: int) -> list[Review]:
    """Return reviews in reverse chronological order."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT * FROM reviews
        WHERE resource_id = ?
        ORDER BY timestamp DESC
        """,
        (resource_id,),
    )
    return [_row_to_review(row) for row in rows]


def user_review_exists(resource_id: int, reviewer_id: int) -> bool:
    """Return True when a user already reviewed the resource."""

    db = get_db()
    row = query_one(
        db,
        """
        SELECT 1 FROM reviews
        WHERE resource_id = ? AND reviewer_id = ?
        """,
        (resource_id, reviewer_id),
    )
    return row is not None


def average_rating(resource_id: int) -> Optional[float]:
    """Compute the average rating for display."""

    db = get_db()
    row = query_one(
        db,
        "SELECT ROUND(AVG(rating), 2) AS avg_rating FROM reviews WHERE resource_id = ?",
        (resource_id,),
    )
    return row["avg_rating"] if row and row["avg_rating"] is not None else None

