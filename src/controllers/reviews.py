"""Reviews blueprint for feedback on resources."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField
from wtforms.validators import InputRequired, NumberRange, Length

from ..data_access import bookings_dao, reviews_dao, resources_dao

bp = Blueprint("reviews", __name__, url_prefix="/reviews", template_folder="../views")


class ReviewForm(FlaskForm):
    """Form capturing a rating and narrative feedback."""

    rating = SelectField(
        "Rating",
        choices=[(str(i), f"{i} Stars") for i in range(1, 6)],
        validators=[InputRequired()],
    )
    comment = TextAreaField("Comment", validators=[InputRequired(), Length(max=1000)])
    submit = SubmitField("Submit review")


def _user_completed_booking(resource_id: int, user_id: int) -> bool:
    bookings = bookings_dao.list_bookings_for_user(user_id)
    return any(booking.resource_id == resource_id and booking.status == "completed" for booking in bookings)


@bp.route("/<int:resource_id>", methods=["POST"])
@login_required
def submit(resource_id: int):
    """Accept a review if the user completed a booking."""

    resource = resources_dao.get_resource_by_id(resource_id, include_unpublished=False)
    if not resource:
        abort(404)
    form = ReviewForm()
    if not form.validate_on_submit():
        flash("Review submission failed. Please fix highlighted issues.", "danger")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    if not _user_completed_booking(resource_id, current_user.user_id):
        flash("You can only review resources after completing a booking.", "warning")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    if reviews_dao.user_review_exists(resource_id, current_user.user_id):
        flash("You have already reviewed this resource.", "info")
        return redirect(url_for("resources.detail", resource_id=resource_id))

    reviews_dao.create_review(
        resource_id=resource_id,
        reviewer_id=current_user.user_id,
        rating=int(form.rating.data),
        comment=form.comment.data,
    )
    flash("Thank you for your review!", "success")
    return redirect(url_for("resources.detail", resource_id=resource_id))

