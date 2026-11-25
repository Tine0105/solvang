"""Cấu hình trung tâm cho ứng dụng LuxAuto Showroom theo từng môi trường."""

import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Cấu hình cơ sở đọc từ biến môi trường (không hard-code thông tin nhạy cảm)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-luxauto-secret-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'luxauto.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Bảo mật phiên & CSRF
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Cấu hình gửi email (Flask-Mail)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 2525))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "LuxAuto Showroom <noreply@luxauto.vn>"
    )
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "true").lower() in ("1", "true", "yes")
    RESET_TOKEN_MAX_AGE = int(os.environ.get("RESET_TOKEN_MAX_AGE", 3600))

    # Cấu hình tích hợp API tỷ giá ngoại tệ (CLO3)
    EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY", "").strip()
    EXCHANGE_API_TIMEOUT = int(os.environ.get("EXCHANGE_API_TIMEOUT", 5))
    EXCHANGE_FALLBACK_USD_VND = float(os.environ.get("EXCHANGE_FALLBACK_USD_VND", 25450.0))
    EXCHANGE_FALLBACK_EUR_VND = float(os.environ.get("EXCHANGE_FALLBACK_EUR_VND", 27100.0))

    # Upload ảnh xe sang, Mô hình 3D (.glb) & Phân trang
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "cars")
    MODEL_UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "models")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 50)) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_MODEL_EXTENSIONS = {"glb"}
    CARS_PER_PAGE = int(os.environ.get("CARS_PER_PAGE", 6))


class DevelopmentConfig(Config):
    """Cấu hình phục vụ phát triển cục bộ."""

    DEBUG = True


class TestingConfig(Config):
    """Cấu hình phục vụ kiểm thử tự động với pytest (SQLite in-memory)."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    EXCHANGE_API_TIMEOUT = 2


class ProductionConfig(Config):
    """Cấu hình triển khai thực tế."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
