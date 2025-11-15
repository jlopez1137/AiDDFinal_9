"""Data access helpers for campus resources."""

from __future__ import annotations

from typing import Optional

from datetime import datetime
from pathlib import Path

from ..models.entities import Resource
from .db import execute, get_db, query_all, query_one


def _row_to_resource(row) -> Resource:
    requires_approval_value = False
    if row is not None:
        keys = row.keys() if hasattr(row, "keys") else []
        if "requires_approval" in keys:
            requires_approval_value = bool(row["requires_approval"])
    image_value = row["images"]
    if image_value:
        static_dir = Path(__file__).resolve().parents[1] / "static" / "uploads"
        if not (static_dir / image_value).exists():
            image_value = None

    return Resource(
        resource_id=row["resource_id"],
        owner_id=row["owner_id"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        location=row["location"],
        capacity=row["capacity"],
        images=image_value,
        availability_rules=row["availability_rules"],
        requires_approval=requires_approval_value,
        status=row["status"],
        created_at=datetime.fromisoformat(str(row["created_at"]).replace(" ", "T")),
        average_rating=row["average_rating"],
    )


def create_resource(
    owner_id: int,
    title: str,
    description: str,
    category: str,
    location: str,
    capacity: int,
    images: Optional[str] = None,
    availability_rules: Optional[str] = None,
    requires_approval: bool = False,
    status: str = "draft",
) -> Resource:
    """Insert a new resource."""

    db = get_db()
    cursor = execute(
        db,
        """
        INSERT INTO resources (
            owner_id, title, description, category, location,
            capacity, images, availability_rules, requires_approval, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            title,
            description,
            category,
            location,
            capacity,
            images,
            availability_rules,
            int(requires_approval),
            status,
        ),
    )
    return get_resource_by_id(cursor.lastrowid, include_unpublished=True, connection=db)


def update_resource(resource_id: int, **fields) -> None:
    """Update mutable fields for a resource."""

    allowed = {
        "title",
        "description",
        "category",
        "location",
        "capacity",
        "images",
        "availability_rules",
        "requires_approval",
        "status",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return

    columns = ", ".join(f"{key} = ?" for key in updates.keys())
    params = list(updates.values()) + [resource_id]
    db = get_db()
    execute(db, f"UPDATE resources SET {columns} WHERE resource_id = ?", params)


def set_status(resource_id: int, status: str) -> None:
    """Update a resource status lifecycle value."""

    update_resource(resource_id, status=status)


def get_resource_by_id(
    resource_id: int,
    include_unpublished: bool = False,
    connection=None,
) -> Resource | None:
    """Fetch a single resource, optionally including drafts."""

    db = connection or get_db()
    query = """
        SELECT
            r.*,
            ROUND(AVG(rv.rating), 2) AS average_rating
        FROM resources r
        LEFT JOIN reviews rv ON rv.resource_id = r.resource_id
        WHERE r.resource_id = ?
    """
    params = [resource_id]
    if not include_unpublished:
        query += " AND r.status = 'published'"
    query += " GROUP BY r.resource_id"
    row = query_one(db, query, params)
    return _row_to_resource(row) if row else None


def list_published_resources(db=None, limit: Optional[int] = None) -> list[Resource]:
    """Return recently created published resources."""

    db = db or get_db()
    query = """
        SELECT
            r.*,
            ROUND(AVG(rv.rating), 2) AS average_rating
        FROM resources r
        LEFT JOIN reviews rv ON rv.resource_id = r.resource_id
        WHERE r.status = 'published'
        GROUP BY r.resource_id
        ORDER BY r.created_at DESC
    """
    if limit:
        query += " LIMIT ?"
        rows = query_all(db, query, (limit,))
    else:
        rows = query_all(db, query)
    return [_row_to_resource(row) for row in rows]


def list_resources_for_owner(owner_id: int) -> list[Resource]:
    """Return all resources created by a specific owner."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT
            r.*,
            ROUND(AVG(rv.rating), 2) AS average_rating
        FROM resources r
        LEFT JOIN reviews rv ON rv.resource_id = r.resource_id
        WHERE r.owner_id = ?
        GROUP BY r.resource_id
        ORDER BY r.created_at DESC
        """,
        (owner_id,),
    )
    return [_row_to_resource(row) for row in rows]


def search_resources(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort: str = "recent",
) -> list[Resource]:
    """Perform filtered search across published resources."""

    db = get_db()
    query = """
        SELECT
            r.*,
            ROUND(AVG(rv.rating), 2) AS average_rating
        FROM resources r
        LEFT JOIN reviews rv ON rv.resource_id = r.resource_id
        WHERE r.status = 'published'
    """
    params: list = []
    if keyword:
        query += " AND (r.title LIKE ? OR r.description LIKE ?)"
        like_term = f"%{keyword}%"
        params.extend([like_term, like_term])
    if category:
        query += " AND r.category = ?"
        params.append(category)
    if location:
        query += " AND r.location LIKE ?"
        params.append(f"%{location}%")
    if start_date and end_date:
        query += """
            AND r.resource_id NOT IN (
                SELECT b.resource_id
                FROM bookings b
                WHERE b.status IN ('pending', 'approved')
                AND NOT (b.end_datetime <= ? OR b.start_datetime >= ?)
            )
        """
        params.extend([start_date, end_date])
    query += " GROUP BY r.resource_id"
    if sort == "top-rated":
        query += " ORDER BY (average_rating IS NULL), average_rating DESC, r.created_at DESC"
    else:
        query += " ORDER BY r.created_at DESC"
    rows = query_all(db, query, params)
    return [_row_to_resource(row) for row in rows]


def list_distinct_categories(db=None) -> list[str]:
    """Return available categories to power filter chips."""

    db = db or get_db()
    rows = query_all(
        db,
        "SELECT DISTINCT category FROM resources WHERE status = 'published' ORDER BY category ASC",
    )
    return [row["category"] for row in rows if row["category"]]

