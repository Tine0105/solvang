from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.blueprints.orders import orders_bp
from app.extensions import db
from app.forms import OrderForm, TestDriveForm
from app.models import Car, CarColor, Favorite, Order, TestDriveRequest


@orders_bp.route('/favorites')
@login_required
def favorites():
    fav_items = (
        Favorite.query.filter_by(user_id=current_user.id)
        .join(Car)
        .order_by(Favorite.id.desc())
        .all()
    )
    return render_template('orders/favorites.html', favorites=fav_items)


@orders_bp.route('/favorites/toggle/<int:car_id>', methods=['POST'])
@login_required
def toggle_favorite(car_id):
    car = Car.query.get_or_404(car_id)
    existing = Favorite.query.filter_by(user_id=current_user.id, car_id=car.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Đã xóa {car.name} khỏi danh sách yêu thích.', 'info')
    else:
        db.session.add(Favorite(user_id=current_user.id, car_id=car.id))
        db.session.commit()
        flash(f'Đã thêm {car.name} vào danh sách yêu thích.', 'success')

    next_url = request.form.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('cars.detail', slug=car.slug))


@orders_bp.route('/create/<int:car_id>', methods=['POST'])
@login_required
def create_order(car_id):
    car = Car.query.get_or_404(car_id)
    form = OrderForm()
    form.color_id.choices = [(c.id, c.color_name) for c in car.colors] or [(0, 'Màu tiêu chuẩn')]

    if car.stock <= 0:
        flash('Mẫu xe này hiện đã hết hàng trong kho.', 'warning')
        return redirect(url_for('cars.detail', slug=car.slug))

    if form.validate_on_submit():
        color_id = form.color_id.data if form.color_id.data != 0 else None
        if color_id is not None:
            valid_color = CarColor.query.filter_by(id=color_id, car_id=car.id).first()
            if not valid_color:
                flash('Màu sơn được chọn không hợp lệ.', 'danger')
                return redirect(url_for('cars.detail', slug=car.slug))

        order = Order(
            user_id=current_user.id,
            car_id=car.id,
            color_id=color_id,
            status='pending',
            note=form.note.data.strip() if form.note.data else None,
        )
        db.session.add(order)
        db.session.commit()
        flash(f'Đã gửi đơn đặt mua xe {car.name}. Chuyên viên sẽ liên hệ xác nhận.', 'success')
        return redirect(url_for('orders.my_orders'))

    for field_errors in form.errors.values():
        for err in field_errors:
            flash(err, 'danger')
    return redirect(url_for('cars.detail', slug=car.slug))


@orders_bp.route('/my-orders')
@login_required
def my_orders():
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template('orders/my_orders.html', orders=orders)


@orders_bp.route('/test-drive/<int:car_id>', methods=['POST'])
@login_required
def create_test_drive(car_id):
    car = Car.query.get_or_404(car_id)
    form = TestDriveForm()
    if form.validate_on_submit():
        req = TestDriveRequest(
            user_id=current_user.id,
            car_id=car.id,
            preferred_date=form.preferred_date.data,
            status='pending',
        )
        db.session.add(req)
        db.session.commit()
        flash(f'Đã đặt lịch lái thử xe {car.name} vào ngày {req.preferred_date.strftime("%d/%m/%Y")}.', 'success')
        return redirect(url_for('orders.my_test_drives'))

    for field_errors in form.errors.values():
        for err in field_errors:
            flash(err, 'danger')
    return redirect(url_for('cars.detail', slug=car.slug))


@orders_bp.route('/my-test-drives')
@login_required
def my_test_drives():
    requests = (
        TestDriveRequest.query.filter_by(user_id=current_user.id)
        .order_by(TestDriveRequest.created_at.desc())
        .all()
    )
    return render_template('orders/my_test_drives.html', test_drives=requests)
