import os
from flask import Flask, jsonify
from app.config import Config, DevelopmentConfig
from app.extensions import db, migrate, cors


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = DevelopmentConfig

    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        supports_credentials=True,
    )

    # Ensure upload and audio directories exist
    upload_folder = app.config.get("UPLOAD_FOLDER")
    audio_folder = app.config.get("AUDIO_FOLDER")
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
    if audio_folder:
        os.makedirs(audio_folder, exist_ok=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.faculty import faculty_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(admin_bp)

    # Health check route
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "online",
            "app": "KARE Viva Evaluation System",
            "institution": "Kalasalingam Academy of Research and Education",
            "database": "Neon PostgreSQL",
        }), 200

    # Clean error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "details": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden: Access denied"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error. Please try again later."}), 500

    return app
