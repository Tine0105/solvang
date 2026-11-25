"""Application Factory khởi tạo ứng dụng Flask LuxAuto Showroom."""

import os
from flask import Flask, render_template

from config import INSTANCE_DIR, config_by_name
from app.extensions import csrf, db, login_manager, mail, migrate


def create_app(config_name: str | type = "default") -> Flask:
    """Tạo và cấu hình đối tượng Flask theo mẫu Application Factory."""
    app = Flask(__name__, instance_path=INSTANCE_DIR)

    if isinstance(config_name, str):
        config_obj = config_by_name.get(config_name, config_by_name["default"])
    else:
        config_obj = config_name
    app.config.from_object(config_obj)

    # Đảm bảo thư mục instance (SQLite), thư mục upload ảnh và mô hình 3D tồn tại
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MODEL_UPLOAD_FOLDER"], exist_ok=True)

    # Khởi tạo các extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Nạp models để SQLAlchemy & Flask-Migrate nhận diện đầy đủ metadata
    from app import models  # noqa: F401

    # Đăng ký các Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Bộ lọc định dạng tiền tệ VNĐ & USD dùng trong Jinja2
    @app.template_filter("vnd")
    def format_vnd(value) -> str:
        try:
            amount = int(value or 0)
            return f"{amount:,}".replace(",", ".") + " ₫"
        except (TypeError, ValueError):
            return "0 ₫"

    @app.template_filter("usd")
    def format_usd(value) -> str:
        try:
            amount = float(value or 0)
            return f"${amount:,.0f}"
        except (TypeError, ValueError):
            return "$0"

    # Error handlers chuẩn
    @app.errorhandler(403)
    def forbidden_error(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
