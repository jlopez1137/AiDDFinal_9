"""Data access helpers for bookings."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from ..models.entities import Booking
from .db import execute, get_db, query_all, query_one


def _row_to_booking(row) -> Booking:
    def _parse(dt: str) -> datetime:
        return datetime.fromisoformat(dt.replace(" ", "T"))

    row_keys = row.keys() if hasattr(row, "keys") else ()
    approval_notes = row["approval_notes"] if "approval_notes" in row_keys else None

    return Booking(
        booking_id=row["booking_id"],
        resource_id=row["resource_id"],
        requester_id=row["requester_id"],
        start_datetime=_parse(row["start_datetime"]),
        end_datetime=_parse(row["end_datetime"]),
        status=row["status"],
        approval_notes=approval_notes,
        created_at=_parse(row["created_at"]),
        updated_at=_parse(row["updated_at"]),
    )


def create_booking(
    resource_id: int,
    requester_id: int,
    start_datetime: Union[str, datetime],
    end_datetime: Union[str, datetime],
    requires_approval: bool = True,
    approval_notes: Optional[str] = None,
) -> Booking:
    """Insert a new booking after validating conflicts."""

    db = get_db()
    start_value = start_datetime.isoformat() if isinstance(start_datetime, datetime) else start_datetime
    end_value = end_datetime.isoformat() if isinstance(end_datetime, datetime) else end_datetime
    if has_conflict(resource_id, start_value, end_value):
        raise ValueError("Booking conflicts with an existing reservation.")
    status = "pending" if requires_approval else "approved"
    cursor = execute(
        db,
        """
        INSERT INTO bookings (
            resource_id, requester_id, start_datetime, end_datetime, status, approval_notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            resource_id,
            requester_id,
            start_value,
            end_value,
            status,
            approval_notes,
        ),
    )
    return get_booking_by_id(cursor.lastrowid, connection=db)


def get_booking_by_id(booking_id: int, connection=None) -> Booking | None:
    """Fetch a specific booking."""

    db = connection or get_db()
    row = query_one(
        db,
        "SELECT * FROM bookings WHERE booking_id = ?",
        (booking_id,),
    )
    return _row_to_booking(row) if row else None


def update_booking_status(booking_id: int, status: str) -> None:
    """Update booking status and timestamp."""

    db = get_db()
    execute(
        db,
        """
        UPDATE bookings
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE booking_id = ?
        """,
        (status, booking_id),
    )


def approve_booking(booking_id: int, approver_id: int, notes: Optional[str] = None) -> None:
    """Approve a pending booking request."""

    db = get_db()
    execute(
        db,
        """
        UPDATE bookings
        SET status = 'approved',
            approval_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE booking_id = ? AND status = 'pending'
        """,
        (notes, booking_id),
    )
    _log_admin_action(db, approver_id, "bookings", f"Approved booking {booking_id}")


def reject_booking(booking_id: int, approver_id: int, notes: Optional[str] = None) -> None:
    """Reject a pending booking request."""

    db = get_db()
    execute(
        db,
        """
        UPDATE bookings
        SET status = 'rejected',
            approval_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE booking_id = ? AND status = 'pending'
        """,
        (notes, booking_id),
    )
    _log_admin_action(db, approver_id, "bookings", f"Rejected booking {booking_id}")


def cancel_booking(booking_id: int) -> None:
    """Cancel a booking request."""

    db = get_db()
    execute(
        db,
        """
        UPDATE bookings
        SET status = 'cancelled',
            updated_at = CURRENT_TIMESTAMP
        WHERE booking_id = ?
        """,
        (booking_id,),
    )


def complete_booking(booking_id: int) -> None:
    """Mark a booking as completed."""

    db = get_db()
    execute(
        db,
        """
        UPDATE bookings
        SET status = 'completed',
            updated_at = CURRENT_TIMESTAMP
        WHERE booking_id = ?
        """,
        (booking_id,),
    )


def list_bookings_for_user(user_id: int) -> list[Booking]:
    """Return bookings initiated by a requester."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT * FROM bookings
        WHERE requester_id = ?
        ORDER BY start_datetime DESC
        """,
        (user_id,),
    )
    return [_row_to_booking(row) for row in rows]


def list_bookings_for_resource(resource_id: int) -> list[Booking]:
    """Return bookings for a specific resource."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT * FROM bookings
        WHERE resource_id = ?
        ORDER BY start_datetime DESC
        """,
        (resource_id,),
    )
    return [_row_to_booking(row) for row in rows]


def has_conflict(
    resource_id: int,
    start_datetime: Union[str, datetime],
    end_datetime: Union[str, datetime],
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """Return True when a booking overlaps existing pending/approved slots."""

    db = get_db()
    query = """
        SELECT 1 FROM bookings
        WHERE resource_id = ?
          AND status IN ('pending', 'approved')
          AND NOT (end_datetime <= ? OR start_datetime >= ?)
    """
    start_value = start_datetime.isoformat() if isinstance(start_datetime, datetime) else start_datetime
    end_value = end_datetime.isoformat() if isinstance(end_datetime, datetime) else end_datetime
    params: list = [resource_id, start_value, end_value]
    if exclude_booking_id:
        query += " AND booking_id != ?"
        params.append(exclude_booking_id)
    row = query_one(db, query, params)
    return row is not None


def list_pending_approvals() -> list[Booking]:
    """Retrieve pending bookings for moderation workflows."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT * FROM bookings
        WHERE status = 'pending'
        ORDER BY created_at ASC
        """,
    )
    return [_row_to_booking(row) for row in rows]


def list_pending_for_owner(owner_id: int) -> list[Booking]:
    """Pending bookings scoped to resources owned by the specified user."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT b.*
        FROM bookings b
        JOIN resources r ON r.resource_id = b.resource_id
        WHERE b.status = 'pending' AND r.owner_id = ?
        ORDER BY b.created_at ASC
        """,
        (owner_id,),
    )
    return [_row_to_booking(row) for row in rows]


def _log_admin_action(db, admin_id: int, target_table: str, action: str) -> None:
    """Insert a row into admin_logs when available."""

    execute(
        db,
        """
        INSERT INTO admin_logs (admin_id, action, target_table, details)
        VALUES (?, ?, ?, ?)
        """,
        (admin_id, action, target_table, None),
    )

