import logging
import os
import logging

import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, send_from_directory
from flask_migrate import Migrate
from sqlalchemy import inspect

from mcp_liquidation_map.config import Config
from mcp_liquidation_map.models.user import db
from mcp_liquidation_map.routes.crypto import crypto_bp
from mcp_liquidation_map.routes.user import user_bp


_LOG_LEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}


def configure_logging():
    """Configure application logging once, respecting existing handlers."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level_name = os.getenv('APP_LOG_LEVEL', 'INFO').upper()
    level = _LOG_LEVELS.get(level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

configure_logging()

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config.from_object(Config)


db.init_app(app)
migrate = Migrate(app, db)


def _ensure_user_schema(application: Flask) -> None:
    """Ensure the user schema exists when the user API is enabled."""

    database_uri = application.config.get("SQLALCHEMY_DATABASE_URI", "")
    with application.app_context():
        if database_uri.startswith("sqlite:///"):
            sqlite_path = database_uri.replace("sqlite:///", "", 1)
            sqlite_dir = os.path.dirname(sqlite_path)
            if sqlite_dir:
                os.makedirs(sqlite_dir, exist_ok=True)
            db.create_all()
            return

        inspector = inspect(db.engine)
        if not inspector.has_table("user"):
            raise RuntimeError(
                "ENABLE_USER_API is set but the database schema is missing. "
                "Run your migrations (e.g. `flask --app mcp_liquidation_map.main db upgrade`)."
            )


if app.config.get("ENABLE_USER_API"):
    _ensure_user_schema(app)
    app.register_blueprint(user_bp, url_prefix="/api")
else:
    logging.getLogger(__name__).info(
        "User API disabled. Set ENABLE_USER_API=1 to opt in."
    )

app.register_blueprint(crypto_bp, url_prefix="/api")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


@app.route("/api/features", methods=["GET"])
def feature_flags():
    """Expose frontend feature flags."""

    return jsonify({"userApiEnabled": bool(app.config.get("ENABLE_USER_API"))})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=app.config.get("DEBUG", False))
