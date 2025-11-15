"""Administrative dashboard and moderation routes."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import sqlite3
import traceback

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required

from ..data_access import bookings_dao, messages_dao, resources_dao, users_dao
from ..data_access.db import get_db, query_all, query_one
from .auth import role_required
from .messaging import MessageForm, _resolve_context

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../views")


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    """Render admin overview metrics."""

    db = get_db()
    users_total = query_one(db, "SELECT COUNT(*) AS total FROM users")["total"]
    resources_total = query_one(db, "SELECT COUNT(*) AS total FROM resources WHERE status = 'published'")["total"]
    active_bookings = query_one(
        db,
        "SELECT COUNT(*) AS total FROM bookings WHERE status IN ('pending', 'approved')",
    )["total"]
    pending_approvals = query_one(
        db,
        "SELECT COUNT(*) AS total FROM bookings WHERE status = 'pending'",
    )["total"]
    try:
        threads_total = query_one(
            db,
            "SELECT COUNT(*) AS total FROM threads",
        )["total"]
    except sqlite3.OperationalError:
        threads_total = 0

    recent_bookings = query_all(
        db,
        """
        SELECT
            b.booking_id,
            b.status,
            b.created_at,
            r.title AS resource_title,
            u.name AS requester_name
        FROM bookings b
        JOIN resources r ON r.resource_id = b.resource_id
        JOIN users u ON u.user_id = b.requester_id
        ORDER BY b.created_at DESC
        LIMIT 5
        """,
    )

    try:
        thread_rows = messages_dao.list_threads_for_admin()
    except (sqlite3.OperationalError, messages_dao.MessagingSchemaError) as exc:  # type: ignore[attr-defined]
        flash(str(exc), "warning")
        thread_rows = []
    recent_threads: list[dict] = []
    for row in thread_rows[:5]:
        try:
            thread = messages_dao.get_thread(row["thread_id"])
        except messages_dao.MessagingSchemaError as exc:  # type: ignore[attr-defined]
            flash(str(exc), "warning")
            break
        if not thread:
            continue
        context_label = thread.context_type.title()
        if thread.context_type == "resource" and thread.context_id:
            resource = resources_dao.get_resource_by_id(thread.context_id, include_unpublished=True)
            if resource:
                context_label = resource.title
        elif thread.context_type == "booking" and thread.context_id:
            booking = bookings_dao.get_booking_by_id(thread.context_id)
            if booking:
                resource = resources_dao.get_resource_by_id(booking.resource_id, include_unpublished=True)
                context_label = f"Booking #{booking.booking_id}"
                if resource:
                    context_label = f"{resource.title} (Booking #{booking.booking_id})"
        try:
            last_message = messages_dao.get_last_message(thread.thread_id)
        except messages_dao.MessagingSchemaError as exc:  # type: ignore[attr-defined]
            flash(str(exc), "warning")
            break
        row_keys = row.keys() if hasattr(row, "keys") else ()
        last_activity = row["last_activity"] if "last_activity" in row_keys else None
        if isinstance(last_activity, str):
            try:
                last_activity_dt = datetime.fromisoformat(last_activity.replace(" ", "T"))
            except ValueError:
                last_activity_dt = None
        else:
            last_activity_dt = last_activity
        recent_threads.append(
            {
                "thread_id": thread.thread_id,
                "context_label": context_label,
                "last_activity": last_activity_dt,
                "message_preview": last_message.content if last_message else None,
                "message_count": row["message_count"] if "message_count" in row_keys else 0,
            }
        )

    return render_template(
        "admin_dashboard.html",
        metrics={
            "users_total": users_total,
            "resources_total": resources_total,
            "active_bookings": active_bookings,
            "pending_approvals": pending_approvals,
            "threads_total": threads_total,
        },
        recent_bookings=recent_bookings,
        recent_threads=recent_threads,
    )


@bp.route("/users")
@login_required
@role_required("admin")
def users():
    """List all users for management."""

    all_users = users_dao.list_users()
    return render_template("admin_users.html", users=all_users)


@bp.route("/resources")
@login_required
@role_required("admin")
def resources():
    """List all resources for moderation."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT r.*, u.name as owner_name
        FROM resources r
        JOIN users u ON u.user_id = r.owner_id
        ORDER BY r.created_at DESC
        """,
    )
    return render_template("admin_resources.html", resources=rows)


@bp.route("/bookings")
@login_required
@role_required("admin")
def bookings():
    """List all bookings for approval pipeline."""

    db = get_db()
    rows = query_all(
        db,
        """
        SELECT
            b.*,
            r.title AS resource_title,
            r.requires_approval,
            u.name AS requester_name,
            owner.name AS owner_name
        FROM bookings b
        JOIN resources r ON r.resource_id = b.resource_id
        JOIN users u ON u.user_id = b.requester_id
        JOIN users owner ON owner.user_id = r.owner_id
        ORDER BY b.created_at DESC
        """,
    )
    return render_template("admin_bookings.html", bookings=rows)


@bp.route("/bookings/<int:booking_id>/approve", methods=["POST"])
@login_required
@role_required("admin")
def approve_booking(booking_id: int):
    """Approve a booking via admin override."""

    notes = request.form.get("approval_notes") or None
    bookings_dao.approve_booking(booking_id, current_user.user_id, notes)
    flash("Booking approved.", "success")
    return redirect(url_for("admin.bookings"))


@bp.route("/bookings/<int:booking_id>/reject", methods=["POST"])
@login_required
@role_required("admin")
def reject_booking(booking_id: int):
    """Reject a booking via admin override."""

    notes = request.form.get("approval_notes") or None
    bookings_dao.reject_booking(booking_id, current_user.user_id, notes)
    flash("Booking rejected.", "info")
    return redirect(url_for("admin.bookings"))


@bp.route("/resources/<int:resource_id>/publish", methods=["POST"])
@login_required
@role_required("admin")
def publish_resource(resource_id: int):
    """Publish a draft resource listing as admin."""

    resources_dao.set_status(resource_id, "published")
    flash("Resource published.", "success")
    return redirect(url_for("admin.resources"))


@bp.route("/resources/<int:resource_id>/archive", methods=["POST"])
@login_required
@role_required("admin")
def archive_resource(resource_id: int):
    """Archive a resource listing as admin."""

    resources_dao.set_status(resource_id, "archived")
    flash("Resource archived.", "info")
    return redirect(url_for("admin.resources"))


@bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@login_required
@role_required("admin")
def deactivate_user(user_id: int):
    """Deactivate a user record."""

    if user_id == current_user.user_id:
        flash("You cannot deactivate your own account.", "warning")
    else:
        users_dao.deactivate_user(user_id)
        flash("User deactivated.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/activate", methods=["POST"])
@login_required
@role_required("admin")
def activate_user(user_id: int):
    """Reactivate a user record."""

    users_dao.activate_user(user_id)
    flash("User reactivated.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/threads")
@login_required
@role_required("admin")
def threads():
    """Admin inbox showing every thread."""

    rows = messages_dao.list_threads_for_admin()
    thread_items = []
    for row in rows:
        thread = messages_dao.get_thread(row["thread_id"])
        if not thread:
            continue
        last_message = messages_dao.get_last_message(thread.thread_id)
        context = _resolve_context(thread)
        thread_items.append(
            {
                "thread": thread,
                "context": context,
                "message_count": row["message_count"],
                "last_message": last_message,
            }
        )
    return render_template("admin_threads.html", threads=thread_items)


@bp.route("/threads/<int:thread_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def thread_detail(thread_id: int):
    """Admin view of a specific thread."""

    thread = messages_dao.get_thread(thread_id)
    if not thread:
        abort(404)
    messages = messages_dao.get_messages(thread_id)
    participant_ids = {msg.sender_id for msg in messages} | {msg.receiver_id for msg in messages}
    users = {user_id: users_dao.get_user_by_id(user_id) for user_id in participant_ids}
    form = MessageForm()
    if form.validate_on_submit() and messages:
        last_message = messages[-1]
        recipient = last_message.sender_id if last_message.sender_id != current_user.user_id else last_message.receiver_id
        messages_dao.post_message(thread_id, current_user.user_id, recipient, form.content.data)
        flash("Reply sent.", "success")
        return redirect(url_for("admin.thread_detail", thread_id=thread_id))
    context = _resolve_context(thread)
    return render_template(
        "admin_thread_detail.html",
        thread=thread,
        messages=messages,
        context=context,
        form=form,
        users=users,
    )


@bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    """Render analytics dashboard with usage reports and charts."""

    try:
        db = get_db()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

        # Bookings by Department
        try:
            bookings_by_department = query_all(
                db,
                """
                SELECT 
                    COALESCE(u.department, 'No Department') AS department,
                    COUNT(*) AS booking_count
                FROM bookings b
                JOIN users u ON u.user_id = b.requester_id
                GROUP BY u.department
                ORDER BY booking_count DESC
                """,
            )
            dept_labels = []
            dept_values = []
            for row in bookings_by_department:
                row_dict = dict(row)  # Convert Row to plain dict
                dept = row_dict.get("department") if row_dict.get("department") else "No Department"
                dept_labels.append(str(dept))
                dept_values.append(int(row_dict.get("booking_count", 0)))
            dept_data = {
                "labels": dept_labels,
                "values": dept_values,
            }
        except Exception as e:
            current_app.logger.error(f"Error in bookings by department: {e}\n{traceback.format_exc()}")
            dept_data = {"labels": [], "values": []}

        # Bookings by Resource Category
        try:
            bookings_by_category = query_all(
                db,
                """
                SELECT 
                    r.category,
                    COUNT(*) AS booking_count
                FROM bookings b
                JOIN resources r ON r.resource_id = b.resource_id
                GROUP BY r.category
                ORDER BY booking_count DESC
                """,
            )
            cat_labels = []
            cat_values = []
            for row in bookings_by_category:
                row_dict = dict(row)  # Convert Row to plain dict
                cat_labels.append(str(row_dict.get("category", "")))
                cat_values.append(int(row_dict.get("booking_count", 0)))
            category_data = {
                "labels": cat_labels,
                "values": cat_values,
            }
        except Exception as e:
            current_app.logger.error(f"Error in bookings by category: {e}\n{traceback.format_exc()}")
            category_data = {"labels": [], "values": []}

        # Usage Trends (last 30 days, grouped by day)
        # SQLite: dates are stored as TEXT in ISO format (YYYY-MM-DD HH:MM:SS)
        # Use substr to extract date portion (first 10 characters)
        try:
            usage_trends = query_all(
                db,
                """
                SELECT 
                    substr(b.created_at, 1, 10) AS booking_date,
                    COUNT(*) AS booking_count
                FROM bookings b
                WHERE b.created_at >= ?
                GROUP BY substr(b.created_at, 1, 10)
                ORDER BY booking_date ASC
                """,
                (thirty_days_ago,),
            )
            trend_labels = []
            trend_values = []
            for row in usage_trends:
                row_dict = dict(row)  # Convert Row to plain dict
                date_val = row_dict.get("booking_date") if row_dict.get("booking_date") else ""
                trend_labels.append(str(date_val))
                trend_values.append(int(row_dict.get("booking_count", 0)))
            trend_data = {
                "labels": trend_labels,
                "values": trend_values,
            }
        except Exception as e:
            current_app.logger.error(f"Error in usage trends: {e}\n{traceback.format_exc()}")
            trend_data = {"labels": [], "values": []}

        # Most Popular Resources (Top 10)
        try:
            popular_resources_rows = query_all(
                db,
                """
                SELECT 
                    r.resource_id,
                    r.title,
                    r.category,
                    COUNT(b.booking_id) AS booking_count
                FROM resources r
                LEFT JOIN bookings b ON b.resource_id = r.resource_id
                WHERE r.status = 'published'
                GROUP BY r.resource_id, r.title, r.category
                ORDER BY booking_count DESC
                LIMIT 10
                """,
            )
            popular_resources = []
            for row in popular_resources_rows:
                row_dict = dict(row)  # Convert Row to plain dict
                popular_resources.append({
                    "resource_id": int(row_dict.get("resource_id", 0)),
                    "title": str(row_dict.get("title", "")),
                    "category": str(row_dict.get("category", "")),
                    "booking_count": int(row_dict.get("booking_count", 0)),
                })
        except Exception:
            popular_resources = []

        # Department Activity (which departments use the system most)
        try:
            department_activity_rows = query_all(
                db,
                """
                SELECT 
                    COALESCE(u.department, 'No Department') AS department,
                    COUNT(DISTINCT u.user_id) AS user_count,
                    COUNT(b.booking_id) AS booking_count
                FROM users u
                LEFT JOIN bookings b ON b.requester_id = u.user_id
                WHERE u.is_active = 1
                GROUP BY u.department
                ORDER BY booking_count DESC, user_count DESC
                """,
            )
            department_activity = []
            for row in department_activity_rows:
                row_dict = dict(row)  # Convert Row to plain dict
                department_activity.append({
                    "department": str(row_dict.get("department")) if row_dict.get("department") else "No Department",
                    "user_count": int(row_dict.get("user_count", 0)),
                    "booking_count": int(row_dict.get("booking_count", 0)),
                })
        except Exception:
            department_activity = []

        # Status Distribution
        try:
            status_distribution = query_all(
                db,
                """
                SELECT 
                    status,
                    COUNT(*) AS count
                FROM bookings
                GROUP BY status
                ORDER BY count DESC
                """,
            )
            status_labels = []
            status_values = []
            for row in status_distribution:
                row_dict = dict(row)  # Convert Row to plain dict
                status_labels.append(str(row_dict.get("status", "")).capitalize())
                status_values.append(int(row_dict.get("count", 0)))
            status_data = {
                "labels": status_labels,
                "values": status_values,
            }
        except Exception as e:
            current_app.logger.error(f"Error in status distribution: {e}\n{traceback.format_exc()}")
            status_data = {"labels": [], "values": []}

        # Summary metrics
        try:
            total_bookings_row = query_one(db, "SELECT COUNT(*) AS total FROM bookings")
            total_bookings = int(total_bookings_row["total"]) if total_bookings_row else 0
        except Exception:
            total_bookings = 0

        try:
            total_users_row = query_one(db, "SELECT COUNT(*) AS total FROM users WHERE is_active = 1")
            total_users = int(total_users_row["total"]) if total_users_row else 0
        except Exception:
            total_users = 0

        try:
            total_resources_row = query_one(
                db, "SELECT COUNT(*) AS total FROM resources WHERE status = 'published'"
            )
            total_resources = int(total_resources_row["total"]) if total_resources_row else 0
        except Exception:
            total_resources = 0

        try:
            bookings_last_30_days_row = query_one(
                db,
                "SELECT COUNT(*) AS total FROM bookings WHERE created_at >= ?",
                (thirty_days_ago,),
            )
            bookings_last_30_days = int(bookings_last_30_days_row["total"]) if bookings_last_30_days_row else 0
        except Exception:
            bookings_last_30_days = 0

        # Serialize chart data to JSON strings to avoid serialization issues in template
        try:
            dept_data_json = json.dumps(dept_data)
            category_data_json = json.dumps(category_data)
            trend_data_json = json.dumps(trend_data)
            status_data_json = json.dumps(status_data)
        except Exception as e:
            current_app.logger.error(f"Error serializing chart data: {e}\n{traceback.format_exc()}")
            dept_data_json = json.dumps({"labels": [], "values": []})
            category_data_json = json.dumps({"labels": [], "values": []})
            trend_data_json = json.dumps({"labels": [], "values": []})
            status_data_json = json.dumps({"labels": [], "values": []})

        return render_template(
            "admin_analytics.html",
            dept_data_json=dept_data_json,
            category_data_json=category_data_json,
            trend_data_json=trend_data_json,
            status_data_json=status_data_json,
            popular_resources=popular_resources,
            department_activity=department_activity,
            summary={
                "total_bookings": total_bookings,
                "total_users": total_users,
                "total_resources": total_resources,
                "bookings_last_30_days": bookings_last_30_days,
            },
        )
    except Exception as e:
        current_app.logger.error(f"Error in analytics route: {e}\n{traceback.format_exc()}")
        flash(f"Error loading analytics: {str(e)}", "danger")
        return redirect(url_for("admin.dashboard"))

