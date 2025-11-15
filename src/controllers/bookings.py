"""Booking workflow blueprint."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SubmitField
from wtforms.validators import InputRequired

from ..data_access import bookings_dao, resources_dao
from .auth import role_in

bp = Blueprint("bookings", __name__, url_prefix="/bookings", template_folder="../views")


class BookingRequestForm(FlaskForm):
    """Form to request a reservation."""

    start_datetime = DateTimeLocalField(
        "Start",
        format="%Y-%m-%dT%H:%M",
        validators=[InputRequired(message="Please provide a start time.")],
    )
    end_datetime = DateTimeLocalField(
        "End",
        format="%Y-%m-%dT%H:%M",
        validators=[InputRequired(message="Please provide an end time.")],
    )
    submit = SubmitField("Request booking")


def _ensure_owner_or_admin(resource_owner_id: int) -> None:
    if current_user.user_id != resource_owner_id and not current_user.is_admin:
        abort(403)


@bp.route("/create/<int:resource_id>", methods=["POST"])
@login_required
def create(resource_id: int):
    """Create a booking for a resource."""

    resource = resources_dao.get_resource_by_id(resource_id, include_unpublished=True)
    if not resource or resource.status == "archived":
        abort(404)
    if resource.status == "draft" and resource.owner_id != current_user.user_id and not current_user.is_admin:
        abort(403)
    form = BookingRequestForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    start = form.start_datetime.data
    end = form.end_datetime.data
    if start >= end:
        flash("End time must be after start time.", "danger")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    try:
        booking = bookings_dao.create_booking(
            resource_id,
            current_user.user_id,
            start.isoformat(),
            end.isoformat(),
            requires_approval=resource.requires_approval,
            approval_notes="Auto-approved" if not resource.requires_approval else None,
        )
    except ValueError:
        flash("This time conflicts with an existing booking.", "warning")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    if resource.requires_approval:
        flash("Booking requested. Await approval from the resource owner.", "success")
    else:
        flash("Booking confirmed and auto-approved.", "success")
    return redirect(url_for("bookings.my_bookings"))


@bp.route("/my")
@login_required
def my_bookings():
    """Display bookings associated with the current user."""

    bookings = bookings_dao.list_bookings_for_user(current_user.user_id)
    return render_template("bookings_my.html", bookings=bookings)


@bp.route("/approvals")
@role_in(["staff", "admin"])
def pending_approvals():
    """Display pending approvals for staff owners or admins."""

    if current_user.is_admin:
        pending = bookings_dao.list_pending_approvals()
    else:
        pending = bookings_dao.list_pending_for_owner(current_user.user_id)
    enriched = []
    for booking in pending:
        resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
        enriched.append(
            {
                "booking": booking,
                "resource": resource,
            }
        )
    return render_template("bookings_pending.html", approvals=enriched)


@bp.route("/<int:booking_id>/approve", methods=["POST"])
@login_required
def approve(booking_id: int):
    """Approve a pending booking."""

    booking = bookings_dao.get_booking_by_id(booking_id)
    if not booking:
        abort(404)
    resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
    if not resource:
        abort(404)
    _ensure_owner_or_admin(resource.owner_id)
    notes = request.form.get("approval_notes") or None
    bookings_dao.approve_booking(booking_id, current_user.user_id, notes)
    flash("Booking approved.", "success")
    return redirect(request.referrer or url_for("bookings.my_bookings"))


@bp.route("/<int:booking_id>/reject", methods=["POST"])
@login_required
def reject(booking_id: int):
    """Reject a pending booking."""

    booking = bookings_dao.get_booking_by_id(booking_id)
    if not booking:
        abort(404)
    resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
    if not resource:
        abort(404)
    _ensure_owner_or_admin(resource.owner_id)
    notes = request.form.get("approval_notes") or None
    bookings_dao.reject_booking(booking_id, current_user.user_id, notes)
    flash("Booking rejected.", "info")
    return redirect(request.referrer or url_for("bookings.my_bookings"))


@bp.route("/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id: int):
    """Allow requester to cancel their booking."""

    booking = bookings_dao.get_booking_by_id(booking_id)
    if not booking:
        abort(404)
    if booking.requester_id != current_user.user_id and not current_user.is_admin:
        abort(403)
    bookings_dao.cancel_booking(booking_id)
    flash("Booking cancelled.", "info")
    return redirect(url_for("bookings.my_bookings"))


@bp.route("/<int:booking_id>/complete", methods=["POST"])
@login_required
def complete(booking_id: int):
    """Mark a booking as completed."""

    booking = bookings_dao.get_booking_by_id(booking_id)
    if not booking:
        abort(404)
    resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
    if not resource:
        abort(404)
    _ensure_owner_or_admin(resource.owner_id)
    bookings_dao.complete_booking(booking_id)
    flash("Booking marked as completed.", "success")
    return redirect(request.referrer or url_for("bookings.my_bookings"))

