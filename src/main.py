import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_migrate import Migrate

from src.config import Config
from src.models.user import db
from src.routes.crypto import crypto_bp
from src.routes.user import user_bp

app = Flask(
    __name__, static_folder=os.path.join(os.path.dirname(__file__), "static")
)
app.config.from_object(Config)

app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(crypto_bp, url_prefix="/api")

db.init_app(app)
migrate = Migrate(app, db)

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=app.config.get("DEBUG", False))
