"""Deterministic seed data for the Campus Resource Hub."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt

from .db import execute, get_db, query_one


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed() -> None:
    """Populate the database with representative demo records."""

    db = get_db()

    users = [
        ("Ada Admin", "ada.admin@campus.edu", "admin", "IT Services"),
        ("Sam Staff", "sam.staff@campus.edu", "staff", "Innovation Hub"),
        ("Sky Staff", "sky.staff@campus.edu", "staff", "Student Experience"),
        ("Alice Student", "alice@student.edu", "student", "Student Affairs"),
        ("Ben Student", "ben@student.edu", "student", "First-Year Programs"),
        ("Casey Student", "casey@student.edu", "student", "Graduate Studies"),
    ]

    for name, email, role, department in users:
        execute(
            db,
            """
            INSERT OR IGNORE INTO users (name, email, password_hash, role, department, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, email, _hash_password("Password123!"), role, department),
        )

    def _user_id(email: str) -> int:
        row = query_one(db, "SELECT user_id FROM users WHERE email = ?", (email,))
        if not row:
            raise ValueError(f"Expected seed user {email} to exist.")
        return row["user_id"]

    resources = [
        {
            "owner_email": "sam.staff@campus.edu",
            "title": "Innovation Lab",
            "description": "Collaborative space with prototyping tools and mentorship availability.",
            "category": "Innovation",
            "location": "Building A - Room 210",
            "capacity": 20,
            "images": None,
            "rules": "Available weekdays 9am-6pm",
            "requires_approval": True,
            "status": "published",
        },
        {
            "owner_email": "sam.staff@campus.edu",
            "title": "Mobile AV Cart",
            "description": "Portable audiovisual kit for events with projector and microphones.",
            "category": "Equipment",
            "location": "Media Center",
            "capacity": 1,
            "images": None,
            "rules": "Requires 24-hour advance booking",
            "requires_approval": False,
            "status": "published",
        },
        {
            "owner_email": "sky.staff@campus.edu",
            "title": "Wellness Reflection Room",
            "description": "Quiet space with soft lighting, mats, and mindfulness resources.",
            "category": "Wellness",
            "location": "Student Center - 2nd floor",
            "capacity": 6,
            "images": None,
            "rules": "Reserve for 30-minute intervals",
            "requires_approval": True,
            "status": "published",
        },
    ]

    for resource in resources:
        owner_id = _user_id(resource["owner_email"])
        execute(
            db,
            """
            INSERT OR IGNORE INTO resources (
                owner_id, title, description, category, location,
                capacity, images, availability_rules, requires_approval, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                resource["title"],
                resource["description"],
                resource["category"],
                resource["location"],
                resource["capacity"],
                resource["images"],
                resource["rules"],
                int(resource["requires_approval"]),
                resource["status"],
            ),
        )

    def _resource_id(title: str) -> int:
        row = query_one(db, "SELECT resource_id FROM resources WHERE title = ?", (title,))
        if not row:
            raise ValueError(f"Expected seed resource {title} to exist.")
        return row["resource_id"]

    now = datetime.now(timezone.utc)
    completed_start = now - timedelta(days=7)
    booking_rows = [
        {
            "resource": "Innovation Lab",
            "requester": "alice@student.edu",
            "start": now + timedelta(days=2),
            "end": now + timedelta(days=2, hours=2),
            "status": "pending",
            "notes": None,
        },
        {
            "resource": "Mobile AV Cart",
            "requester": "ben@student.edu",
            "start": now + timedelta(days=1),
            "end": now + timedelta(days=1, hours=3),
            "status": "approved",
            "notes": "Auto-approved via seed data.",
        },
        {
            "resource": "Innovation Lab",
            "requester": "casey@student.edu",
            "start": completed_start,
            "end": completed_start + timedelta(hours=2),
            "status": "completed",
            "notes": "Session completed successfully.",
        },
    ]

    for row in booking_rows:
        execute(
            db,
            """
            INSERT OR IGNORE INTO bookings (
                resource_id, requester_id, start_datetime, end_datetime, status, approval_notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _resource_id(row["resource"]),
                _user_id(row["requester"]),
                row["start"].isoformat(),
                row["end"].isoformat(),
                row["status"],
                row["notes"],
            ),
        )

    approved_booking = query_one(
        db,
        """
        SELECT booking_id, resource_id, requester_id
        FROM bookings
        WHERE status = 'approved'
        ORDER BY created_at ASC
        LIMIT 1
        """,
    )

    if approved_booking:
        execute(
            db,
            """
            INSERT OR IGNORE INTO reviews (resource_id, reviewer_id, rating, comment)
            VALUES (?, ?, ?, ?)
            """,
            (
                approved_booking["resource_id"],
                approved_booking["requester_id"],
                5,
                "Excellent support from staff and well-equipped space.",
            ),
        )

    # Threads and messages
    admin_id = _user_id("ada.admin@campus.edu")
    pending_booking_id = query_one(
        db,
        "SELECT booking_id FROM bookings WHERE status = 'pending' ORDER BY created_at DESC LIMIT 1",
    )
    if pending_booking_id:
        thread_row = query_one(
            db,
            "SELECT thread_id FROM threads WHERE context_type = 'booking' AND context_id = ?",
            (pending_booking_id["booking_id"],),
        )
        if thread_row:
            thread_id = thread_row["thread_id"]
        else:
            thread_id = execute(
                db,
                """
                INSERT INTO threads (context_type, context_id, created_by)
                VALUES ('booking', ?, ?)
                """,
                (pending_booking_id["booking_id"], admin_id),
            ).lastrowid
        execute(
            db,
            """
            INSERT OR IGNORE INTO messages (thread_id, sender_id, receiver_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                thread_id,
                _user_id("alice@student.edu"),
                _user_id("sam.staff@campus.edu"),
                "Hello! Could you confirm if the lab will support a 3D printing demo?",
            ),
        )
        execute(
            db,
            """
            INSERT OR IGNORE INTO messages (thread_id, sender_id, receiver_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                thread_id,
                _user_id("sam.staff@campus.edu"),
                _user_id("alice@student.edu"),
                "Thanks for the request! I will review and confirm shortly.",
            ),
        )

    g_row = query_one(
        db,
        "SELECT thread_id FROM threads WHERE context_type = 'general' ORDER BY created_at LIMIT 1",
    )
    if g_row:
        general_thread = g_row["thread_id"]
    else:
        general_thread = execute(
            db,
            """
            INSERT INTO threads (context_type, context_id, created_by)
            VALUES ('general', NULL, ?)
            """,
            (admin_id,),
        ).lastrowid
    execute(
        db,
        """
        INSERT OR IGNORE INTO messages (thread_id, sender_id, receiver_id, content)
        VALUES (?, ?, ?, ?)
        """,
        (
            general_thread,
            admin_id,
            _user_id("sam.staff@campus.edu"),
            "Reminder: please keep resource listings updated with availability changes.",
        ),
    )

    # AI Contribution: Seed helper drafted to ensure deterministic demo content across environments.


if __name__ == "__main__":
    from flask import Flask

    app = Flask(__name__)
    app.config.from_mapping(DATABASE_URL="sqlite:///campus_resource_hub.db")
    with app.app_context():
        seed()
    print("Seed data applied.")

