"""Resource management routes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4
from types import SimpleNamespace

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, NumberRange

from ..data_access import bookings_dao, resources_dao, reviews_dao
from .bookings import BookingRequestForm
from .messaging import ThreadStartForm
from .reviews import ReviewForm
from .auth import role_required

bp = Blueprint("resources", __name__, url_prefix="/resources", template_folder="../views")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def _extract_search_params():
    """Normalize search query parameters and provide template context."""

    raw_keyword = (request.args.get("q") or "").strip()
    raw_category = (request.args.get("category") or "").strip()
    raw_location = (request.args.get("location") or "").strip()
    raw_start = (request.args.get("start_date") or "").strip()
    raw_end = (request.args.get("end_date") or "").strip()
    sort = (request.args.get("sort") or "recent").strip() or "recent"
    if sort not in {"recent", "top-rated"}:
        sort = "recent"

    search_params = {
        "keyword": raw_keyword or None,
        "category": raw_category or None,
        "location": raw_location or None,
        "start_date": f"{raw_start}T00:00:00" if raw_start else None,
        "end_date": f"{raw_end}T23:59:59" if raw_end else None,
        "sort": sort,
    }
    search_context = SimpleNamespace(
        keyword=raw_keyword,
        category=raw_category,
        location=raw_location,
        start_date=raw_start,
        end_date=raw_end,
        sort=sort,
    )
    has_active_filters = any(
        [
            raw_keyword,
            raw_category,
            raw_location,
            raw_start,
            raw_end,
            sort != "recent",
        ]
    )
    return search_params, search_context, has_active_filters


def _save_image(file_storage) -> Optional[str]:
    """Persist a validated upload and return the stored filename."""

    if not file_storage:
        return None

    filename = file_storage.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file extension.")

    safe_name = f"{uuid4().hex}.{extension}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    file_path = upload_folder / safe_name
    file_storage.save(file_path)
    return safe_name


class ResourceForm(FlaskForm):
    """Form for creating and editing resources."""

    title = StringField("Title", validators=[InputRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[InputRequired(), Length(max=2000)])
    category = SelectField(
        "Category",
        choices=[
            ("Innovation", "Innovation"),
            ("Study", "Study"),
            ("Equipment", "Equipment"),
            ("Wellness", "Wellness"),
            ("Other", "Other"),
        ],
    )
    location = StringField("Location", validators=[InputRequired(), Length(max=150)])
    capacity = IntegerField("Capacity", validators=[InputRequired(), NumberRange(min=0, max=1000)])
    availability_rules = TextAreaField("Availability Rules", validators=[Length(max=500)])
    requires_approval = BooleanField("Requires approval before confirming bookings")
    image = FileField(
        "Primary Image",
        validators=[
            FileAllowed(list(ALLOWED_EXTENSIONS), "Images must be PNG or JPG."),
        ],
    )
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft",
    )
    submit = SubmitField("Save resource")


@bp.route("/")
def list_resources():
    """Display published resources."""

    search_params, search_context, has_active_filters = _extract_search_params()
    resources = resources_dao.search_resources(
        keyword=search_params["keyword"],
        category=search_params["category"],
        location=search_params["location"],
        start_date=search_params["start_date"],
        end_date=search_params["end_date"],
        sort=search_params["sort"],
    )
    categories = resources_dao.list_distinct_categories()
    return render_template(
        "resources_list.html",
        resources=resources,
        category_filters=categories,
        search_context=search_context,
        has_active_filters=has_active_filters,
    )


@bp.route("/my")
@login_required
def my_resources():
    """List resources owned by the current user."""

    items = resources_dao.list_resources_for_owner(current_user.user_id)
    categories = resources_dao.list_distinct_categories()
    _, search_context, has_active_filters = _extract_search_params()
    return render_template(
        "resources_list.html",
        resources=items,
        show_owner_actions=True,
        category_filters=categories,
        search_context=search_context,
        has_active_filters=has_active_filters,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("staff", "admin")
def create_resource():
    """Allow staff to create a new resource."""

    form = ResourceForm()
    if form.validate_on_submit():
        image_name = None
        if form.image.data:
            try:
                image_name = _save_image(form.image.data)
            except ValueError as exc:
                form.image.errors.append(str(exc))
                return render_template("resources_form.html", form=form)

        resource = resources_dao.create_resource(
            owner_id=current_user.user_id,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            location=form.location.data,
            capacity=form.capacity.data,
            images=image_name,
            availability_rules=form.availability_rules.data or None,
            requires_approval=form.requires_approval.data,
            status=form.status.data,
        )
        flash("Resource created successfully.", "success")
        return redirect(url_for("resources.detail", resource_id=resource.resource_id))
    return render_template("resources_form.html", form=form)


@bp.route("/<int:resource_id>")
def detail(resource_id: int):
    """Show resource details, bookings, and reviews."""

    include_unpublished = current_user.is_authenticated
    resource = resources_dao.get_resource_by_id(resource_id, include_unpublished=include_unpublished)
    if not resource:
        abort(404)
    if resource.status != "published" and (
        not current_user.is_authenticated
        or (resource.owner_id != current_user.user_id and not current_user.is_admin)
    ):
        abort(403)
    bookings = bookings_dao.list_bookings_for_resource(resource_id)
    reviews = reviews_dao.list_reviews_for_resource(resource_id)
    user_can_review = False
    thread_form = ThreadStartForm()
    if current_user.is_authenticated:
        thread_form.receiver_id.data = str(resource.owner_id)
        thread_form.context_type.data = "resource"
        thread_form.context_id.data = str(resource.resource_id)
        completed = any(
            booking.resource_id == resource_id and booking.status == "completed"
            for booking in bookings_dao.list_bookings_for_user(current_user.user_id)
        )
        already_reviewed = reviews_dao.user_review_exists(resource_id, current_user.user_id)
        user_can_review = completed and not already_reviewed
    return render_template(
        "resource_detail.html",
        resource=resource,
        bookings=bookings,
        reviews=reviews,
        booking_form=BookingRequestForm(),
        review_form=ReviewForm(),
        user_can_review=user_can_review,
        thread_form=thread_form,
    )


@bp.route("/<int:resource_id>/edit", methods=["GET", "POST"])
@login_required
def edit(resource_id: int):
    """Edit an existing resource."""

    resource = resources_dao.get_resource_by_id(resource_id, include_unpublished=True)
    if not resource:
        abort(404)
    if resource.owner_id != current_user.user_id and not current_user.is_admin:
        abort(403)

    form = ResourceForm(obj=resource)
    if form.validate_on_submit():
        image_name = resource.images
        if form.image.data:
            try:
                image_name = _save_image(form.image.data)
            except ValueError as exc:
                form.image.errors.append(str(exc))
                return render_template("resources_form.html", form=form, resource=resource)
        resources_dao.update_resource(
            resource_id,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            location=form.location.data,
            capacity=form.capacity.data,
            availability_rules=form.availability_rules.data or None,
            images=image_name,
            requires_approval=form.requires_approval.data,
            status=form.status.data,
        )
        flash("Resource updated.", "success")
        return redirect(url_for("resources.detail", resource_id=resource_id))
    return render_template("resources_form.html", form=form, resource=resource)


@bp.route("/<int:resource_id>/archive", methods=["POST"])
@login_required
def archive(resource_id: int):
    """Archive a resource listing."""

    resource = resources_dao.get_resource_by_id(resource_id, include_unpublished=True)
    if not resource:
        abort(404)
    if resource.owner_id != current_user.user_id and not current_user.is_admin:
        abort(403)
    resources_dao.set_status(resource_id, "archived")
    flash("Resource archived.", "info")
    return redirect(url_for("resources.list_resources"))

