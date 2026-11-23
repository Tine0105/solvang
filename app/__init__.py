import os
from flask import Flask, render_template

from config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_IMAGE_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_MODEL_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so Flask-Migrate discovers them
    from app import models  # noqa: F401

    # Register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.cars import cars_bp
    from app.blueprints.orders import orders_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cars_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    # Template filters
    @app.template_filter('vnd')
    def format_vnd(value):
        try:
            num = int(value or 0)
            return f'{num:,}'.replace(',', '.') + ' ₫'
        except (TypeError, ValueError):
            return '0 ₫'

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app


def __getattr__(name):
    # Support default Render/Gunicorn entrypoint `gunicorn app:app` without eager init on normal imports
    if name == 'app':
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
