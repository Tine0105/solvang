"""Các route phía khách hàng: Trang chủ, Danh mục (Tìm kiếm + Phân trang), Chi tiết, Yêu thích, Đặt cọc."""

from datetime import datetime, timezone
import secrets
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.blueprints.main import main_bp
from app.extensions import db
from app.forms import CarSearchForm, OrderForm, TestDriveForm
from app.models import Brand, Car, Order, TestDrive
from app.services.email_service import send_order_confirmation_email
from app.services.exchange_service import convert_vnd, get_exchange_rates


def _generate_order_code() -> str:
    """Sinh mã đơn đặt xe duy nhất theo định dạng LUX-YYYYMMDD-XXXX."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"LUX-{stamp}-{suffix}"


@main_bp.route("/")
def index():
    """Trang chủ Showroom hiển thị xe tiêu điểm, danh sách hãng và tỷ giá trực tuyến."""
    featured_cars = (
        Car.query.options(joinedload(Car.brand))
        .filter_by(is_featured=True)
        .order_by(Car.price.desc())
        .limit(6)
        .all()
    )
    if not featured_cars:
        featured_cars = Car.query.options(joinedload(Car.brand)).limit(6).all()

    hero_car = featured_cars[0] if featured_cars else None
    brands = Brand.query.order_by(Brand.name.asc()).all()
    total_cars = Car.query.count()
    rates = get_exchange_rates()

    return render_template(
        "main/index.html",
        hero_car=hero_car,
        featured_cars=featured_cars,
        brands=brands,
        total_cars=total_cars,
        rates=rates,
    )


@main_bp.route("/cars")
def car_list():
    """Danh mục xe sang kết hợp tìm kiếm đa tiêu chí (CarSearchForm) và phân trang (paginate)."""
    brands = Brand.query.order_by(Brand.name.asc()).all()
    search_form = CarSearchForm(request.args)
    search_form.brand_id.choices = [(0, "Tất cả thương hiệu")] + [(b.id, b.name) for b in brands]

    query = Car.query.options(joinedload(Car.brand)).join(Brand)

    q = (search_form.q.data or "").strip()
    brand_id = search_form.brand_id.data or 0
    body_type = (search_form.body_type.data or "").strip()
    fuel_type = (search_form.fuel_type.data or "").strip()
    price_range = (search_form.price_range.data or "").strip()
    sort = (search_form.sort.data or "newest").strip()
    page = request.args.get("page", 1, type=int)

    if q:
        like_term = f"%{q}%"
        query = query.filter(
            or_(
                Car.name.ilike(like_term),
                Brand.name.ilike(like_term),
                Car.exterior_color.ilike(like_term),
                Car.description.ilike(like_term),
            )
        )
    if brand_id > 0:
        query = query.filter(Car.brand_id == brand_id)
    if body_type:
        query = query.filter(Car.body_type == body_type)
    if fuel_type:
        query = query.filter(Car.fuel_type == fuel_type)

    if price_range == "under_5b":
        query = query.filter(Car.price < 5_000_000_000)
    elif price_range == "5b_to_10b":
        query = query.filter(Car.price >= 5_000_000_000, Car.price <= 10_000_000_000)
    elif price_range == "over_10b":
        query = query.filter(Car.price > 10_000_000_000)

    if sort == "price_asc":
        query = query.order_by(Car.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Car.price.desc())
    elif sort == "power_desc":
        query = query.order_by(Car.horsepower.desc())
    else:
        query = query.order_by(Car.created_at.desc(), Car.id.desc())

    per_page = current_app.config.get("CARS_PER_PAGE", 6)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    rates = get_exchange_rates()

    query_params = {
        k: v
        for k, v in {
            "q": q,
            "brand_id": brand_id if brand_id > 0 else "",
            "body_type": body_type,
            "fuel_type": fuel_type,
            "price_range": price_range,
            "sort": sort if sort != "newest" else "",
        }.items()
        if v != ""
    }

    return render_template(
        "main/car_list.html",
        cars=pagination.items,
        pagination=pagination,
        search_form=search_form,
        query_params=query_params,
        rates=rates,
    )


@main_bp.route("/cars/<slug>")
def car_detail(slug: str):
    """Trang chi tiết thông số kỹ thuật, quy đổi USD/EUR trực tiếp, đặt cọc và lái thử."""
    car = (
        Car.query.options(joinedload(Car.brand), selectinload(Car.images))
        .filter_by(slug=slug)
        .first_or_404()
    )
    related_cars = (
        Car.query.options(joinedload(Car.brand))
        .filter(Car.brand_id == car.brand_id, Car.id != car.id)
        .limit(3)
        .all()
    )
    if not related_cars:
        related_cars = (
            Car.query.options(joinedload(Car.brand))
            .filter(Car.id != car.id)
            .order_by(Car.is_featured.desc())
            .limit(3)
            .all()
        )

    rates = get_exchange_rates()
    converted = convert_vnd(car.price, rates=rates)
    deposit_vnd = int(car.price * 0.05)

    is_favorite = False
    order_form = OrderForm()
    test_drive_form = TestDriveForm()
    if current_user.is_authenticated:
        is_favorite = car in current_user.favorite_cars
        if current_user.phone and not order_form.customer_phone.data:
            order_form.customer_phone.data = current_user.phone
            test_drive_form.phone.data = current_user.phone

    return render_template(
        "main/car_detail.html",
        car=car,
        related_cars=related_cars,
        rates=rates,
        converted=converted,
        deposit_vnd=deposit_vnd,
        is_favorite=is_favorite,
        order_form=order_form,
        test_drive_form=test_drive_form,
    )


@main_bp.route("/favorites")
@login_required
def favorites():
    """Hiển thị bộ sưu tập xe sang yêu thích của người dùng (quan hệ n-n)."""
    rates = get_exchange_rates()
    return render_template(
        "main/favorites.html",
        cars=current_user.favorite_cars,
        rates=rates,
    )


@main_bp.route("/favorites/toggle/<int:car_id>", methods=["POST"])
@login_required
def toggle_favorite(car_id: int):
    """Thêm hoặc gỡ xe sang khỏi danh sách yêu thích."""
    car = db.session.get(Car, car_id)
    if not car:
        flash("Mẫu xe không tồn tại.", "danger")
        return redirect(url_for("main.car_list"))

    if car in current_user.favorite_cars:
        current_user.favorite_cars.remove(car)
        db.session.commit()
        flash(f"Đã gỡ {car.name} khỏi danh sách yêu thích.", "info")
    else:
        current_user.favorite_cars.append(car)
        db.session.commit()
        flash(f"Đã lưu {car.name} vào bộ sưu tập yêu thích.", "success")

    return redirect(url_for("main.car_detail", slug=car.slug))


@main_bp.route("/orders/create/<int:car_id>", methods=["POST"])
@login_required
def create_order(car_id: int):
    """Tạo đơn đặt cọc xe sang (5% giá trị xe) và chuyển tới màn hình thanh toán Demo."""
    car = db.session.get(Car, car_id)
    if not car:
        flash("Không tìm thấy mẫu xe.", "danger")
        return redirect(url_for("main.car_list"))

    if car.stock <= 0:
        flash("Mẫu xe này hiện đã tạm hết xe sẵn kho.", "warning")
        return redirect(url_for("main.car_detail", slug=car.slug))

    form = OrderForm()
    if form.validate_on_submit():
        deposit_amount = int(car.price * 0.05)
        order = Order(
            order_code=_generate_order_code(),
            user_id=current_user.id,
            car_id=car.id,
            total_price=car.price,
            deposit_amount=deposit_amount,
            payment_method=form.payment_method.data,
            payment_status="unpaid",
            status="pending",
            customer_phone=form.customer_phone.data.strip(),
            note=form.note.data.strip() if form.note.data else None,
        )
        db.session.add(order)
        db.session.commit()
        send_order_confirmation_email(current_user, order)

        flash(f"Đã tạo đơn đặt xe {order.order_code}. Vui lòng hoàn tất xác nhận đặt cọc.", "success")
        return redirect(url_for("main.order_payment_demo", order_id=order.id))

    for errors in form.errors.values():
        for err in errors:
            flash(err, "danger")
    return redirect(url_for("main.car_detail", slug=car.slug))


@main_bp.route("/orders/<int:order_id>/pay-demo", methods=["GET", "POST"])
@login_required
def order_payment_demo(order_id: int):
    """Màn hình mô phỏng thanh toán đặt cọc trực tuyến bằng QR Ngân hàng (Chức năng mở rộng)."""
    order = Order.query.options(joinedload(Order.car).joinedload(Car.brand)).filter_by(id=order_id).first_or_404()
    if order.user_id != current_user.id and not current_user.is_admin:
        flash("Bạn không có quyền truy cập đơn hàng này.", "danger")
        return redirect(url_for("main.my_orders"))

    if request.method == "POST":
        order.payment_status = "paid"
        if order.status == "pending":
            order.status = "confirmed"
        db.session.commit()
        flash(f"Thanh toán cọc thành công cho đơn hàng {order.order_code}!", "success")
        return redirect(url_for("main.my_orders"))

    rates = get_exchange_rates()
    deposit_usd = round(order.deposit_amount / rates["usd_to_vnd"], 2)
    return render_template(
        "main/payment_demo.html",
        order=order,
        rates=rates,
        deposit_usd=deposit_usd,
    )


@main_bp.route("/my-orders")
@login_required
def my_orders():
    """Lịch sử đơn đặt mua xe và lịch hẹn lái thử của khách hàng."""
    orders = (
        Order.query.options(joinedload(Order.car).joinedload(Car.brand))
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    test_drives = (
        TestDrive.query.options(joinedload(TestDrive.car))
        .filter_by(user_id=current_user.id)
        .order_by(TestDrive.created_at.desc())
        .all()
    )
    return render_template("main/my_orders.html", orders=orders, test_drives=test_drives)


@main_bp.route("/test-drive/<int:car_id>", methods=["POST"])
@login_required
def create_test_drive(car_id: int):
    """Xử lý đăng ký lịch hẹn lái thử xe sang."""
    car = db.session.get(Car, car_id)
    if not car:
        flash("Mẫu xe không tồn tại.", "danger")
        return redirect(url_for("main.car_list"))

    form = TestDriveForm()
    if form.validate_on_submit():
        booking = TestDrive(
            user_id=current_user.id,
            car_id=car.id,
            preferred_date=form.preferred_date.data,
            time_slot=form.time_slot.data,
            phone=form.phone.data.strip(),
            note=form.note.data.strip() if form.note.data else None,
            status="pending",
        )
        db.session.add(booking)
        db.session.commit()
        flash(
            f"Đã đặt lịch lái thử {car.name} vào ngày {booking.preferred_date.strftime('%d/%m/%Y')} ({booking.time_slot}).",
            "success",
        )
        return redirect(url_for("main.my_orders"))

    for errors in form.errors.values():
        for err in errors:
            flash(err, "danger")
    return redirect(url_for("main.car_detail", slug=car.slug))
