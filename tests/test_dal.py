"""Data access layer tests."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.data_access import bookings_dao, resources_dao, users_dao


def test_resource_crud_flow(app):
    """Ensure resources can be created and updated."""

    with app.app_context():
        owner = users_dao.get_user_by_email("sam.staff@campus.edu")
        resource = resources_dao.create_resource(
            owner_id=owner.user_id,
            title="Test Lab",
            description="Testing description",
            category="Innovation",
            location="Room 101",
            capacity=12,
            requires_approval=True,
            status="draft",
        )
        assert resource.title == "Test Lab"

        resources_dao.update_resource(
            resource.resource_id,
            title="Updated Test Lab",
            status="published",
            requires_approval=False,
        )
        fetched = resources_dao.get_resource_by_id(resource.resource_id, include_unpublished=True)
        assert fetched.title == "Updated Test Lab"
        assert fetched.status == "published"
        assert fetched.requires_approval is False


def test_booking_crud_and_status(app):
    """Bookings should be stored and status transitions persist."""

    with app.app_context():
        restricted = next(res for res in resources_dao.list_published_resources() if res.requires_approval)
        requester = users_dao.get_user_by_email("alice@student.edu")
        start = datetime.now(timezone.utc) + timedelta(days=10)
        end = start + timedelta(hours=1)
        booking = bookings_dao.create_booking(
            restricted.resource_id,
            requester.user_id,
            start,
            end,
            requires_approval=True,
        )
        assert booking.status == "pending"

        bookings_dao.approve_booking(booking.booking_id, requester.user_id, "See you soon")
        updated = bookings_dao.get_booking_by_id(booking.booking_id)
        assert updated.status == "approved"
        assert updated.approval_notes == "See you soon"

        # Second booking for rejection path
        second_start = start + timedelta(days=1)
        second_end = second_start + timedelta(hours=1)
        second_booking = bookings_dao.create_booking(
            restricted.resource_id,
            requester.user_id,
            second_start,
            second_end,
            requires_approval=True,
        )
        bookings_dao.reject_booking(second_booking.booking_id, requester.user_id, "Space not available")
        rejected = bookings_dao.get_booking_by_id(second_booking.booking_id)
        assert rejected.status == "rejected"
        assert rejected.approval_notes == "Space not available"


def test_invalid_resource_insert_raises(app):
    """Capacity validation should reject negative values."""

    with app.app_context():
        owner = users_dao.get_user_by_email("sam.staff@campus.edu")
        with pytest.raises(sqlite3.IntegrityError):
            resources_dao.create_resource(
                owner_id=owner.user_id,
                title="Broken Resource",
                description="Should fail",
                category="Innovation",
                location="Nowhere",
                capacity=-1,
            )

