"""Search and filter functionality tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.data_access import bookings_dao, resources_dao, users_dao


def test_keyword_search(app):
    with app.app_context():
        results = resources_dao.search_resources(keyword="Collaborative")
        titles = [r.title for r in results]
        assert any("Innovation Lab" in title for title in titles)


def test_category_and_date_filter(app):
    with app.app_context():
        owner = users_dao.get_user_by_email("sam.staff@campus.edu")
        resource = resources_dao.create_resource(
            owner_id=owner.user_id,
            title="Weekend Retreat Space",
            description="Perfect for retreats and wellness events.",
            category="Wellness",
            location="Retreat Center",
            capacity=15,
            requires_approval=True,
            status="published",
        )
        requester = users_dao.get_user_by_email("alice@student.edu")
        start = datetime.now(timezone.utc) + timedelta(days=7)
        end = start + timedelta(hours=3)
        bookings_dao.create_booking(
            resource.resource_id,
            requester.user_id,
            start,
            end,
            requires_approval=True,
        )

        iso_start = (start + timedelta(minutes=30)).isoformat()
        iso_end = (end - timedelta(minutes=30)).isoformat()

        filtered = resources_dao.search_resources(
            category="Wellness",
            start_date=iso_start,
            end_date=iso_end,
        )
        assert all(r.resource_id != resource.resource_id for r in filtered)


def test_sort_top_rated(app):
    with app.app_context():
        results = resources_dao.search_resources(sort="top-rated")
        assert results
        ratings = [resource.average_rating or 0 for resource in results]
        assert ratings == sorted(ratings, reverse=True)
        assert any(resource.title == "Innovation Lab" for resource in results)


def test_search_excludes_draft_and_archived(app):
    with app.app_context():
        owner = users_dao.get_user_by_email("sam.staff@campus.edu")
        draft = resources_dao.create_resource(
            owner_id=owner.user_id,
            title="Hidden Draft Resource",
            description="Not visible to search.",
            category="Innovation",
            location="Bunker",
            capacity=5,
            requires_approval=False,
            status="draft",
        )
        archived = resources_dao.create_resource(
            owner_id=owner.user_id,
            title="Archived Resource",
            description="Should not show up.",
            category="Study",
            location="Archive",
            capacity=3,
            requires_approval=False,
            status="archived",
        )
        results = resources_dao.search_resources()
        titles = {resource.title for resource in results}
        assert draft.title not in titles
        assert archived.title not in titles


def test_requires_approval_badge_visible_in_listing(client):
    response = client.get("/resources/")
    assert response.status_code == 200
    assert b"Requires Approval" in response.data

