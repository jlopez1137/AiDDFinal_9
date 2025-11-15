"""Authentication blueprint handling registration, login, and logout."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

import bcrypt
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from ..data_access import users_dao

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../views")

ALLOWED_ROLES = ("student", "staff", "admin")


class RegistrationForm(FlaskForm):
    """Registration form for new campus users."""

    name = StringField("Full Name", validators=[InputRequired(), Length(max=120)])
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[InputRequired(), EqualTo("password", message="Passwords must match.")],
    )
    role = SelectField(
        "Role",
        choices=[(role, role.title()) for role in ALLOWED_ROLES if role != "admin"],
        validators=[InputRequired()],
        default="student",
    )
    department = StringField("Department", validators=[Length(max=120)])
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    """Basic credential form."""

    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Sign in")


def role_required(*roles: str) -> Callable:
    """Decorator enforcing role-based access control."""

    allowed_roles = tuple(role for role in roles if role in ALLOWED_ROLES)

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if allowed_roles and current_user.role not in allowed_roles and not current_user.is_admin:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def role_in(roles: Iterable[str]) -> Callable:
    """Decorator that accepts an iterable of roles for clarity."""

    return role_required(*tuple(role for role in roles if role in ALLOWED_ROLES))


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration."""

    if current_user.is_authenticated:
        flash("You are already signed in.", "info")
        return redirect(url_for("resources.list_resources"))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing = users_dao.get_user_by_email(form.email.data)
        if existing:
            form.email.errors.append("An account with that email already exists.")
        else:
            password_hash = bcrypt.hashpw(form.password.data.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = users_dao.create_user(
                name=form.name.data,
                email=form.email.data,
                password_hash=password_hash,
                role=form.role.data,
                department=form.department.data or None,
            )
            login_user(user)
            flash("Welcome to the Campus Resource Hub!", "success")
            return redirect(url_for("resources.list_resources"))
    return render_template("auth_register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user."""

    if current_user.is_authenticated:
        flash("You are already signed in.", "info")
        return redirect(url_for("resources.list_resources"))

    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email.data)
        if not user or not users_dao.verify_password(user.password_hash, form.password.data):
            form.email.errors.append("Invalid credentials. Please try again.")
        elif not user.is_active:
            form.email.errors.append("This account has been deactivated. Contact support.")
        else:
            login_user(user)
            flash("Signed in successfully.", "success")
            next_url = request.args.get("next")
            # Redirect admins to admin dashboard, others to resources list
            if user.is_admin and not next_url:
                return redirect(url_for("admin.dashboard"))
            return redirect(next_url or url_for("resources.list_resources"))
    return render_template("auth_login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""

    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))

