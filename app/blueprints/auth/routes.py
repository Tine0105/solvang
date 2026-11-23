from urllib.parse import urlparse
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.forms import RegisterForm, LoginForm, ProfileForm
from app.models import User


def _is_safe_redirect(target: str) -> bool:
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == '' and parsed.netloc == '' and target.startswith('/')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            form.email.errors.append('Email này đã được đăng ký.')
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                email=email,
                phone=form.phone.data.strip() if form.phone.data else None,
                role='user',
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Đăng ký tài khoản thành công. Chào mừng đến với Solvang.', 'success')
            return redirect(url_for('main.index'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    next_page = request.args.get('next') or request.form.get('next')
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Đăng nhập thành công.', 'success')
            if _is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        flash('Email hoặc mật khẩu không chính xác.', 'danger')

    return render_template('auth/login.html', form=form, next_page=next_page)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất khỏi hệ thống.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        db.session.commit()
        flash('Hồ sơ cá nhân đã được cập nhật.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', form=form)
