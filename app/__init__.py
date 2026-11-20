import os

from flask import Flask, jsonify, request

try:  # optional: load variables from a local .env file during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEV_SECRET = "dev-only-change-me"


def create_app(test_config=None):
    from . import admin, auth, db, tasks

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", DEV_SECRET),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "app.sqlite")
        ),
        TOKEN_HOURS=int(os.environ.get("TOKEN_HOURS", "2")),
        MAX_CONTENT_LENGTH=64 * 1024,  # reject oversized request bodies
    )
    if test_config:
        app.config.update(test_config)

    if app.config["SECRET_KEY"] == DEV_SECRET and not app.config.get("TESTING"):
        app.logger.warning(
            "Using the default SECRET_KEY. Set SECRET_KEY in your environment "
            "before deploying."
        )

    os.makedirs(os.path.dirname(app.config["DATABASE"]) or ".", exist_ok=True)
    db.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(admin.bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return "Not found", 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "Request too large"}), 413

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"error": "Internal server error"}), 500

    return app
