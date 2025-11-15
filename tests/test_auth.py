"""Authentication flow tests."""

from __future__ import annotations

from flask import url_for

from src.data_access import users_dao


def login(client, email: str, password: str = "Password123!") -> None:
    client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_register_login_and_access_protected(client):
    """Register a new staff user, login, and access a protected route."""

    response = client.post(
        "/auth/register",
        data={
            "name": "Test Staff",
            "email": "staff@example.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "staff",
            "department": "Testing",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome to the Campus Resource Hub" in response.data

    login_resp = client.post(
        "/auth/login",
        data={
            "email": "staff@example.edu",
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert login_resp.status_code == 200
    assert b"Resources" in login_resp.data

    protected_resp = client.get("/resources/new")
    assert protected_resp.status_code == 200


def test_invalid_credentials_fail(client):
    """Invalid sign-ins should prompt an error."""

    response = client.post(
        "/auth/login",
        data={
            "email": "nonexistent@example.edu",
            "password": "WrongPassword!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_admin_routes_require_admin_privileges(client, app, staff_user):
    """Ensure staff cannot access admin-only endpoints."""

    login(client, staff_user.email)

    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 403

    client.get("/auth/logout", follow_redirects=True)

    login(client, "ada.admin@campus.edu")
    admin_resp = client.get("/admin/", follow_redirects=False)
    assert admin_resp.status_code == 200


def test_deactivated_user_cannot_login(client, app, student_user):
    """Inactive accounts should be prevented from signing in."""

    with app.app_context():
        users_dao.deactivate_user(student_user.user_id)

    response = client.post(
        "/auth/login",
        data={
            "email": student_user.email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"has been deactivated" in response.data

