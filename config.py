import os
import ssl
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

_UNSUPPORTED_PYMYSQL_SSL_PARAMS = {
    'ssl-mode',
    'ssl_mode',
    'ssl_ca',
    'ssl_verify_cert',
    'ssl_verify_identity',
}


def _needs_ssl(raw_url: str) -> bool:
    if os.environ.get('DB_SSL', '').lower() in ('1', 'true', 'yes'):
        return True
    lowered = raw_url.lower()
    return (
        'tidbcloud.com' in lowered
        or 'ssl-mode=' in lowered
        or 'ssl_mode=' in lowered
        or 'ssl_ca=' in lowered
    )


def _build_mysql_uri() -> str:
    explicit_url = os.environ.get('DATABASE_URL')
    if explicit_url:
        if explicit_url.startswith('mysql://'):
            explicit_url = 'mysql+pymysql://' + explicit_url[len('mysql://'):]
        parts = urlsplit(explicit_url)
        filtered_qs = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in _UNSUPPORTED_PYMYSQL_SSL_PARAMS
        ]
        if parts.scheme.startswith('mysql') and not any(k.lower() == 'charset' for k, _ in filtered_qs):
            filtered_qs.append(('charset', 'utf8mb4'))
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(filtered_qs),
            parts.fragment,
        ))
    host = os.environ.get('DB_HOST', '127.0.0.1')
    port = os.environ.get('DB_PORT', '3306')
    name = os.environ.get('DB_NAME', 'solvang_motors')
    user = os.environ.get('DB_USER', 'root')
    password = quote_plus(os.environ.get('DB_PASSWORD', ''))
    return f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'


def _build_engine_options(db_uri: str) -> dict:
    options = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    raw_url = os.environ.get('DATABASE_URL') or db_uri
    if _needs_ssl(raw_url):
        try:
            import certifi
            ca_path = certifi.where()
        except ImportError:
            ca_path = None
        options['connect_args'] = {
            'ssl': ssl.create_default_context(cafile=ca_path),
        }
    return options


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = _build_mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _build_engine_options(SQLALCHEMY_DATABASE_URI)

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
