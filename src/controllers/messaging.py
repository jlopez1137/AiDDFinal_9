"""Messaging between resource requesters and owners."""

from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length

from ..data_access import bookings_dao, messages_dao, resources_dao

bp = Blueprint("messaging", __name__, url_prefix="/messages", template_folder="../views")

THREAD_CONTEXTS = {"resource", "booking", "general"}


class MessageForm(FlaskForm):
    """Form for sending a message."""

    content = TextAreaField("Message", validators=[InputRequired(), Length(max=2000)])
    submit = SubmitField("Send")


class ThreadStartForm(FlaskForm):
    """Form to initiate a new thread."""

    receiver_id = HiddenField(validators=[InputRequired()])
    context_type = HiddenField(validators=[InputRequired()])
    context_id = HiddenField()
    content = TextAreaField("Message", validators=[InputRequired(), Length(max=2000)])
    submit = SubmitField("Send message")


def _thread_participants(thread_id: int) -> set[int]:
    """Determine allowed participants for a thread."""

    thread = messages_dao.get_thread(thread_id)
    if not thread:
        abort(404)
    messages = messages_dao.get_messages(thread_id)
    participants = {msg.sender_id for msg in messages} | {msg.receiver_id for msg in messages}
    if thread.context_type == "resource" and thread.context_id:
        resource = resources_dao.get_resource_by_id(thread.context_id, include_unpublished=True)
        if resource:
            participants.add(resource.owner_id)
    elif thread.context_type == "booking" and thread.context_id:
        booking = bookings_dao.get_booking_by_id(thread.context_id)
        if booking:
            participants.add(booking.requester_id)
            resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
            if resource:
                participants.add(resource.owner_id)
    return participants


def _ensure_thread_access(thread_id: int) -> tuple:
    """Guard that the current user participates in the thread."""

    thread = messages_dao.get_thread(thread_id)
    if not thread:
        abort(404)
    participants = _thread_participants(thread_id)
    if current_user.user_id not in participants and not current_user.is_admin:
        abort(403)
    return thread, participants


def _resolve_context(thread):
    """Return contextual metadata for display."""

    context = {"type": thread.context_type, "id": thread.context_id}
    if thread.context_type == "resource" and thread.context_id:
        context["resource"] = resources_dao.get_resource_by_id(thread.context_id, include_unpublished=True)
    elif thread.context_type == "booking" and thread.context_id:
        booking = bookings_dao.get_booking_by_id(thread.context_id)
        if booking:
            context["booking"] = booking
            context["resource"] = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
    return context


@bp.route("/")
@login_required
def inbox():
    """List threads for the current user."""

    try:
        thread_rows = messages_dao.list_threads_for_user(current_user.user_id)
    except messages_dao.MessagingSchemaError as exc:
        flash(str(exc), "warning")
        return render_template("messaging_inbox.html", threads=[])

    threads = []
    for row in thread_rows:
        try:
            thread = messages_dao.get_thread(row["thread_id"])
        except messages_dao.MessagingSchemaError as exc:
            flash(str(exc), "warning")
            break
        if not thread:
            continue
        try:
            last_message = messages_dao.get_last_message(thread.thread_id)
        except messages_dao.MessagingSchemaError as exc:
            flash(str(exc), "warning")
            break
        context = _resolve_context(thread)
        threads.append(
            {
                "thread": thread,
                "context": context,
                "last_message": last_message,
                "message_count": row["message_count"],
                "has_unread": last_message is not None
                and last_message.sender_id != current_user.user_id,
            }
        )
    return render_template("messaging_inbox.html", threads=threads)


@bp.route("/<int:thread_id>", methods=["GET", "POST"])
@login_required
def thread(thread_id: int):
    """Display a message thread and handle replies."""

    try:
        thread, participants = _ensure_thread_access(thread_id)
        messages = messages_dao.get_messages(thread_id)
    except messages_dao.MessagingSchemaError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("messaging.inbox"))

    form = MessageForm()
    if form.validate_on_submit():
        if not messages:
            abort(400)
        last_message = messages[-1]
        recipient = last_message.receiver_id if last_message.sender_id == current_user.user_id else last_message.sender_id
        try:
            messages_dao.post_message(
                thread_id=thread_id,
                sender_id=current_user.user_id,
                receiver_id=recipient,
                content=form.content.data,
            )
        except messages_dao.MessagingSchemaError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("messaging.inbox"))
        flash("Message sent.", "success")
        return redirect(url_for("messaging.thread", thread_id=thread_id))
    context = _resolve_context(thread)
    return render_template(
        "messaging_thread.html",
        thread=thread,
        messages=messages,
        form=form,
        participants=participants,
        context=context,
    )


@bp.route("/<int:thread_id>/since")
@login_required
def thread_since(thread_id: int):
    """Return recent messages for polling."""

    try:
        _ensure_thread_access(thread_id)
    except messages_dao.MessagingSchemaError:
        return jsonify([])
    since = request.args.get("ts")
    if not since:
        abort(400)
    try:
        messages = messages_dao.get_messages_since(thread_id, since)
    except messages_dao.MessagingSchemaError:
        return jsonify([])
    return jsonify(
        [
            {
                "message_id": msg.message_id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
    )


@bp.route("/start", methods=["POST"])
@login_required
def start():
    """Start a new thread between participants."""

    form = ThreadStartForm()
    if not form.validate_on_submit():
        flash("Unable to start conversation. Please try again.", "danger")
        return redirect(request.referrer or url_for("resources.list_resources"))

    context_type = form.context_type.data
    if context_type not in THREAD_CONTEXTS:
        abort(400)

    receiver_id = int(form.receiver_id.data)
    context_id = int(form.context_id.data) if form.context_id.data else None

    if receiver_id == current_user.user_id:
        flash("You cannot start a thread with yourself.", "warning")
        return redirect(request.referrer or url_for("resources.list_resources"))

    if context_type == "resource":
        resource = resources_dao.get_resource_by_id(context_id, include_unpublished=True)
        if not resource:
            abort(404)
        allowed_participants = {resource.owner_id, current_user.user_id}
        if receiver_id not in allowed_participants:
            abort(403)
    elif context_type == "booking":
        booking = bookings_dao.get_booking_by_id(context_id) if context_id else None
        if not booking:
            abort(404)
        resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
        allowed_participants = {booking.requester_id}
        if resource:
            allowed_participants.add(resource.owner_id)
        if receiver_id not in allowed_participants or current_user.user_id not in allowed_participants:
            abort(403)
    else:
        if not current_user.is_admin:
            abort(403)

    try:
        thread = messages_dao.create_thread(context_type, context_id, current_user.user_id)
        messages_dao.post_message(thread.thread_id, current_user.user_id, receiver_id, form.content.data)
    except messages_dao.MessagingSchemaError as exc:
        flash(str(exc), "warning")
        return redirect(request.referrer or url_for("resources.list_resources"))
    flash("Conversation started.", "success")
    return redirect(url_for("messaging.thread", thread_id=thread.thread_id))

