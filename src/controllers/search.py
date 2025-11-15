"""Search blueprint for resource discovery."""

from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

bp = Blueprint("search", __name__, url_prefix="/search", template_folder="../views")


@bp.route("/")
def search():
    """Redirect legacy search route to the unified resources listing."""

    query_string = request.query_string.decode("utf-8")
    target = url_for("resources.list_resources")
    if query_string:
        target = f"{target}?{query_string}"
    return redirect(target)

