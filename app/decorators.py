from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def admin_required(f):
    """Restrict access to authenticated users with role == 'admin'."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
