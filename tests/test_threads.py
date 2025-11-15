"""Threaded messaging tests."""

from __future__ import annotations

from src.data_access import messages_dao, users_dao


def _login(client, email: str, password: str = "Password123!") -> None:
    client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_create_thread_and_post_message(app):
    """DAO helpers should create threads and return ordered messages."""

    with app.app_context():
        admin = users_dao.get_user_by_email("ada.admin@campus.edu")
        staff = users_dao.get_user_by_email("sam.staff@campus.edu")

        thread = messages_dao.create_thread("general", None, admin.user_id)
        first_message = messages_dao.post_message(thread.thread_id, admin.user_id, staff.user_id, "Welcome to the platform!")
        second_message = messages_dao.post_message(thread.thread_id, staff.user_id, admin.user_id, "Thanks for the reminder.")

        assert first_message.thread_id == thread.thread_id
        assert second_message.timestamp >= first_message.timestamp

        admin_threads = messages_dao.list_threads_for_admin()
        assert any(row["thread_id"] == thread.thread_id for row in admin_threads)

        staff_threads = messages_dao.list_threads_for_user(staff.user_id)
        assert any(row["thread_id"] == thread.thread_id for row in staff_threads)


def test_admin_inbox_lists_booking_threads(client, app, booking_thread):
    """Admin inbox should display booking-context threads."""

    _login(client, "ada.admin@campus.edu")
    response = client.get("/admin/threads")
    assert response.status_code == 200
    assert str(booking_thread.thread_id).encode() in response.data


def test_thread_access_permissions(client, app, booking_thread):
    """Only participants or admins can view a thread."""

    # Participant can view
    _login(client, "alice@student.edu")
    ok_resp = client.get(f"/messages/{booking_thread.thread_id}")
    assert ok_resp.status_code == 200
    client.get("/auth/logout", follow_redirects=True)

    # Non-participant denied
    _login(client, "ben@student.edu")
    forbidden_resp = client.get(f"/messages/{booking_thread.thread_id}")
    assert forbidden_resp.status_code == 403

