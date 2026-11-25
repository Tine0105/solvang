"""Các decorator kiểm soát phân quyền truy cập theo vai trò (RBAC)."""

from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def admin_required(view_func):
    """Chỉ cho phép người dùng đã đăng nhập có vai trò 'admin' truy cập route."""

    @wraps(view_func)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped_view
