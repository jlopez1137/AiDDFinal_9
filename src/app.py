"""Application factory for the Campus Resource Hub."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from flask import Flask, render_template
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

from .config import BaseConfig, get_config
from .data_access import resources_dao, users_dao
from .data_access.db import get_db, init_app as init_db_app
from .models.entities import User

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Look up a user for Flask-Login session handling."""
    if not user_id:
        return None
    return users_dao.get_user_by_id(int(user_id))


def create_app(config_object: type[BaseConfig] | None = None) -> Flask:
    """Create and configure the Flask application instance."""

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "views"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    config_cls = config_object or get_config()
    app.config.from_object(config_cls)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    csrf.init_app(app)
    login_manager.init_app(app)
    init_db_app(app)

    register_blueprints(app)
    register_error_handlers(app)

    @app.route("/")
    def index() -> str:
        """Render the landing page with featured resources and search form."""

        db = get_db()
        featured = resources_dao.list_published_resources(db, limit=6)
        categories = resources_dao.list_distinct_categories(db)
        return render_template(
            "index.html",
            featured_resources=featured,
            category_filters=categories,
        )

    @app.context_processor
    def inject_globals() -> Dict[str, Any]:
        """Expose common template variables."""

        return {
            "current_user": current_user,
            "current_year": datetime.now(timezone.utc).year,
            "csrf_token": generate_csrf,
        }

    return app


def register_blueprints(app: Flask) -> None:
    """Import and register application blueprints."""

    from .controllers import (  # pylint: disable=import-outside-toplevel
        admin,
        auth,
        bookings,
        messaging,
        resources,
        reviews,
        search,
    )

    # AI Contribution: Initial blueprint registration drafted and reviewed by team.
    app.register_blueprint(auth.bp)
    app.register_blueprint(resources.bp)
    app.register_blueprint(bookings.bp)
    app.register_blueprint(messaging.bp)
    app.register_blueprint(reviews.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(search.bp)


def register_error_handlers(app: Flask) -> None:
    """Register user-friendly error handlers."""

    @app.errorhandler(404)
    def not_found(error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                title="Page Not Found",
                message="We could not locate the page you requested.",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                title="Server Error",
                message="An unexpected error occurred. The team has been notified.",
            ),
            500,
        )

