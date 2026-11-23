import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def _build_mysql_uri() -> str:
    explicit_url = os.environ.get('DATABASE_URL')
    if explicit_url:
        if explicit_url.startswith('mysql://'):
            return 'mysql+pymysql://' + explicit_url[len('mysql://'):]
        return explicit_url
    host = os.environ.get('DB_HOST', '127.0.0.1')
    port = os.environ.get('DB_PORT', '3306')
    name = os.environ.get('DB_NAME', 'solvang_motors')
    user = os.environ.get('DB_USER', 'root')
    password = quote_plus(os.environ.get('DB_PASSWORD', ''))
    return f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = _build_mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

    # Security & Session Cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True

    # Static file cache (0 in dev to prevent stale CSS/JS in browser)
    SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get('STATIC_MAX_AGE', 0))

    # Uploads
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH_MB', 25)) * 1024 * 1024
    UPLOAD_IMAGE_FOLDER = os.path.join(basedir, 'app', 'static', 'img', 'uploads')
    UPLOAD_MODEL_FOLDER = os.path.join(basedir, 'app', 'static', 'models')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_MODEL_EXTENSIONS = {'glb'}
    STORE_IMAGES_IN_DB = os.environ.get('STORE_IMAGES_IN_DB', 'false').lower() in ('1', 'true', 'yes')


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_ENGINE_OPTIONS = {}
