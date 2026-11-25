"""Các route xử lý Đăng ký, Đăng nhập, Đăng xuất, Hồ sơ và Đặt lại mật khẩu."""

from urllib.parse import urlparse
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.forms import (
    ForgotPasswordForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    ResetPasswordForm,
)
from app.models import User
from app.services.email_service import send_password_reset_email, send_welcome_email


def _is_safe_redirect_url(target: str | None) -> bool:
    """Đảm bảo đường dẫn chuyển hướng nội bộ nhằm chống lỗ hổng Open Redirect."""
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == "" and target.startswith("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Đăng ký tài khoản khách hàng mới, băm mật khẩu và gửi email xác nhận."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            form.email.errors.append("Địa chỉ email này đã được đăng ký trong hệ thống.")
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                email=email,
                phone=form.phone.data.strip() if form.phone.data else None,
                role="user",
                is_verified=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            send_welcome_email(user)
            login_user(user)
            flash("Đăng ký thành công! Email xác nhận đã được gửi tới hộp thư của bạn.", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Xác thực thông tin đăng nhập bằng Flask-Login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    next_page = request.args.get("next") or request.form.get("next")

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f"Xin chào {user.full_name}, bạn đã đăng nhập thành công.", "success")
            if _is_safe_redirect_url(next_page):
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("main.index"))
        flash("Email hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.", "danger")

    return render_template("auth/login.html", form=form, next_page=next_page)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Đăng xuất khỏi phiên làm việc hiện tại."""
    logout_user()
    flash("Bạn đã đăng xuất khỏi hệ thống.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Tạo token ký số và gửi email hướng dẫn đặt lại mật khẩu."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = ForgotPasswordForm()
    demo_reset_url = None

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_password_reset_email(user, reset_url)
            if current_app.config.get("MAIL_SUPPRESS_SEND"):
                demo_reset_url = reset_url
        flash(
            "Nếu email tồn tại trong hệ thống, liên kết đặt lại mật khẩu đã được gửi đi.",
            "info",
        )
        if not demo_reset_url:
            return redirect(url_for("auth.login"))

    return render_template(
        "auth/forgot_password.html",
        form=form,
        demo_reset_url=demo_reset_url,
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """Xác minh token và cập nhật mật khẩu mới cho người dùng."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_reset_token(token)
    if not user:
        flash("Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Mật khẩu của bạn đã được cập nhật. Vui lòng đăng nhập lại.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Xem và cập nhật thông tin hồ sơ cá nhân."""
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        db.session.commit()
        flash("Đã lưu thông tin hồ sơ cá nhân.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form)
