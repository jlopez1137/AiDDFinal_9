"""Booking conflict detection tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.data_access import bookings_dao, resources_dao, users_dao


def test_conflict_blocks_pending_and_approved(app, restricted_resource, student_user):
    """Pending and approved bookings should block new overlapping requests."""

    with app.app_context():
        base_start = datetime.now(timezone.utc) + timedelta(days=2, hours=9)
        base_end = base_start + timedelta(hours=2)

        bookings_dao.create_booking(
            restricted_resource.resource_id,
            student_user.user_id,
            base_start,
            base_end,
            requires_approval=True,
        )

        overlap_start = base_start + timedelta(minutes=15)
        overlap_end = overlap_start + timedelta(hours=1)
        assert bookings_dao.has_conflict(
            restricted_resource.resource_id,
            overlap_start,
            overlap_end,
        )

        touching_start = base_end
        touching_end = touching_start + timedelta(hours=1)
        assert not bookings_dao.has_conflict(
            restricted_resource.resource_id,
            touching_start,
            touching_end,
        )


def test_auto_approve_when_not_restricted(app):
    """Resources that do not require approval should auto-approve bookings."""

    with app.app_context():
        resources = resources_dao.list_published_resources()
        auto_resource = next(resource for resource in resources if not resource.requires_approval)
        requester = users_dao.get_user_by_email("ben@student.edu")
        start = datetime.now(timezone.utc) + timedelta(days=10)
        end = start + timedelta(hours=1)

        booking = bookings_dao.create_booking(
            auto_resource.resource_id,
            requester.user_id,
            start,
            end,
            requires_approval=False,
        )
        assert booking.status == "approved"

