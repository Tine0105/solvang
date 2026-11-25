"""Các route Quản trị viên (Admin): Dashboard biểu đồ, CRUD Xe sang & Hãng xe, Quản lý Đơn đặt cọc."""

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.blueprints.admin import admin_bp
from app.decorators import admin_required
from app.extensions import db
from app.forms import BrandForm, CarForm, OrderStatusForm
from app.models import Brand, Car, CarImage, Order, TestDrive, User
from app.services.image_service import save_car_image, save_car_model_glb


@admin_bp.route("/")
@admin_required
def dashboard():
    """Trang tổng quan Quản trị kèm dữ liệu biểu đồ thống kê (Chart.js)."""
    total_cars = Car.query.count()
    total_brands = Brand.query.count()
    total_users = User.query.count()
    total_orders = Order.query.count()

    paid_deposit_sum = (
        db.session.query(func.coalesce(func.sum(Order.deposit_amount), 0))
        .filter(Order.payment_status == "paid")
        .scalar()
    )
    confirmed_value_sum = (
        db.session.query(func.coalesce(func.sum(Order.total_price), 0))
        .filter(Order.status.in_(["confirmed", "completed"]))
        .scalar()
    )

    # Dữ liệu Biểu đồ 1: Số lượng mẫu xe theo từng Thương hiệu
    brand_rows = (
        db.session.query(Brand.name, func.count(Car.id))
        .outerjoin(Car, Car.brand_id == Brand.id)
        .group_by(Brand.id, Brand.name)
        .order_by(func.count(Car.id).desc())
        .all()
    )
    brand_chart = {
        "labels": [r[0] for r in brand_rows],
        "values": [int(r[1]) for r in brand_rows],
    }

    # Dữ liệu Biểu đồ 2: Phân bố trạng thái Đơn đặt xe
    status_labels_map = [
        ("pending", "Chờ xác nhận"),
        ("confirmed", "Đã xác nhận"),
        ("completed", "Đã bàn giao"),
        ("cancelled", "Đã hủy"),
    ]
    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    )
    order_chart = {
        "labels": [label for _, label in status_labels_map],
        "values": [int(status_counts.get(code, 0)) for code, _ in status_labels_map],
    }

    recent_orders = (
        Order.query.options(joinedload(Order.user), joinedload(Order.car))
        .order_by(Order.created_at.desc())
        .limit(6)
        .all()
    )
    recent_test_drives = (
        TestDrive.query.options(joinedload(TestDrive.user), joinedload(TestDrive.car))
        .order_by(TestDrive.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats={
            "total_cars": total_cars,
            "total_brands": total_brands,
            "total_users": total_users,
            "total_orders": total_orders,
            "paid_deposit_sum": paid_deposit_sum,
            "confirmed_value_sum": confirmed_value_sum,
        },
        brand_chart=brand_chart,
        order_chart=order_chart,
        recent_orders=recent_orders,
        recent_test_drives=recent_test_drives,
    )


@admin_bp.route("/cars")
@admin_required
def cars():
    """Danh sách quản lý toàn bộ xe sang có hỗ trợ tìm kiếm nhanh và phân trang."""
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Car.query.options(joinedload(Car.brand)).join(Brand)
    if q:
        pattern = f"%{q}%"
        query = query.filter(Car.name.ilike(pattern) | Brand.name.ilike(pattern))

    pagination = query.order_by(Car.id.desc()).paginate(page=page, per_page=8, error_out=False)
    return render_template("admin/cars.html", cars=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/cars/new", methods=["GET", "POST"])
@admin_required
def create_car():
    """Thêm mẫu xe sang mới kèm chức năng upload và tối ưu hóa ảnh."""
    form = CarForm()
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.order_by(Brand.name.asc()).all()]

    if form.validate_on_submit():
        slug = form.slug.data.strip().lower()
        if Car.query.filter_by(slug=slug).first():
            form.slug.errors.append("Đường dẫn tĩnh (slug) này đã tồn tại.")
        else:
            uploaded_thumb = save_car_image(form.thumbnail_file.data)
            thumbnail_url = uploaded_thumb or "/static/img/cars/porsche-911-carrera/hero-1280w.webp"
            uploaded_model = save_car_model_glb(form.model_file.data)

            car = Car(
                brand_id=form.brand_id.data,
                name=form.name.data.strip(),
                slug=slug,
                year=form.year.data,
                price=form.price.data,
                horsepower=form.horsepower.data,
                mileage=form.mileage.data or 0,
                fuel_type=form.fuel_type.data,
                transmission=form.transmission.data,
                body_type=form.body_type.data,
                exterior_color=form.exterior_color.data.strip(),
                seats=form.seats.data,
                stock=form.stock.data,
                is_featured=bool(form.is_featured.data),
                description=form.description.data.strip(),
                thumbnail_url=thumbnail_url,
                model_3d_url=uploaded_model,
            )
            db.session.add(car)
            db.session.flush()

            if uploaded_thumb:
                db.session.add(
                    CarImage(car_id=car.id, image_url=uploaded_thumb, caption="Ảnh đại diện", sort_order=0)
                )

            for idx, file_item in enumerate(request.files.getlist("gallery_files"), start=1):
                gallery_url = save_car_image(file_item)
                if gallery_url:
                    db.session.add(
                        CarImage(
                            car_id=car.id,
                            image_url=gallery_url,
                            caption=f"Ảnh chi tiết {idx}",
                            sort_order=idx,
                        )
                    )

            db.session.commit()
            flash(f"Đã thêm thành công mẫu xe sang: {car.name}.", "success")
            return redirect(url_for("admin.cars"))

    return render_template("admin/car_form.html", form=form, car=None)


@admin_bp.route("/cars/<int:car_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_car(car_id: int):
    """Cập nhật thông tin mẫu xe sang và quản lý thư viện ảnh chi tiết."""
    car = db.session.get(Car, car_id)
    if not car:
        flash("Mẫu xe không tồn tại.", "danger")
        return redirect(url_for("admin.cars"))

    form = CarForm(obj=car)
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.order_by(Brand.name.asc()).all()]

    if form.validate_on_submit():
        slug = form.slug.data.strip().lower()
        duplicate = Car.query.filter(Car.slug == slug, Car.id != car.id).first()
        if duplicate:
            form.slug.errors.append("Slug này đã thuộc về một mẫu xe khác.")
        else:
            car.brand_id = form.brand_id.data
            car.name = form.name.data.strip()
            car.slug = slug
            car.year = form.year.data
            car.price = form.price.data
            car.horsepower = form.horsepower.data
            car.mileage = form.mileage.data or 0
            car.fuel_type = form.fuel_type.data
            car.transmission = form.transmission.data
            car.body_type = form.body_type.data
            car.exterior_color = form.exterior_color.data.strip()
            car.seats = form.seats.data
            car.stock = form.stock.data
            car.is_featured = bool(form.is_featured.data)
            car.description = form.description.data.strip()

            new_thumb = save_car_image(form.thumbnail_file.data)
            if new_thumb:
                car.thumbnail_url = new_thumb

            new_model = save_car_model_glb(form.model_file.data)
            if new_model:
                car.model_3d_url = new_model

            for idx, file_item in enumerate(request.files.getlist("gallery_files"), start=1):
                gallery_url = save_car_image(file_item)
                if gallery_url:
                    db.session.add(
                        CarImage(
                            car_id=car.id,
                            image_url=gallery_url,
                            caption=f"Ảnh bổ sung {idx}",
                            sort_order=len(car.images) + idx,
                        )
                    )

            db.session.commit()
            flash(f"Đã lưu thay đổi cho mẫu xe {car.name}.", "success")
            return redirect(url_for("admin.cars"))

    return render_template("admin/car_form.html", form=form, car=car)


@admin_bp.route("/cars/<int:car_id>/delete", methods=["POST"])
@admin_required
def delete_car(car_id: int):
    """Xóa mẫu xe sang khỏi cơ sở dữ liệu."""
    car = db.session.get(Car, car_id)
    if car:
        car_name = car.name
        db.session.delete(car)
        db.session.commit()
        flash(f"Đã xóa mẫu xe {car_name} khỏi hệ thống.", "info")
    return redirect(url_for("admin.cars"))


@admin_bp.route("/brands", methods=["GET", "POST"])
@admin_required
def brands():
    """Quản lý danh mục các thương hiệu xe sang."""
    form = BrandForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Brand.query.filter_by(name=name).first():
            flash("Thương hiệu này đã tồn tại.", "warning")
        else:
            brand = Brand(
                name=name,
                country=form.country.data.strip(),
                logo_url="/static/img/brands/default.svg",
                description=form.description.data.strip() if form.description.data else None,
            )
            db.session.add(brand)
            db.session.commit()
            flash(f"Đã thêm thương hiệu {brand.name}.", "success")
            return redirect(url_for("admin.brands"))

    all_brands = Brand.query.order_by(Brand.name.asc()).all()
    return render_template("admin/brands.html", brands=all_brands, form=form)


@admin_bp.route("/brands/<int:brand_id>/delete", methods=["POST"])
@admin_required
def delete_brand(brand_id: int):
    """Xóa thương hiệu xe sang."""
    brand = db.session.get(Brand, brand_id)
    if brand:
        db.session.delete(brand)
        db.session.commit()
        flash(f"Đã xóa thương hiệu {brand.name}.", "info")
    return redirect(url_for("admin.brands"))


@admin_bp.route("/orders")
@admin_required
def orders():
    """Quản lý và phê duyệt trạng thái đơn đặt cọc và lịch hẹn lái thử."""
    all_orders = (
        Order.query.options(joinedload(Order.user), joinedload(Order.car))
        .order_by(Order.created_at.desc())
        .all()
    )
    all_test_drives = (
        TestDrive.query.options(joinedload(TestDrive.user), joinedload(TestDrive.car))
        .order_by(TestDrive.created_at.desc())
        .all()
    )
    status_form = OrderStatusForm()
    return render_template(
        "admin/orders.html",
        orders=all_orders,
        test_drives=all_test_drives,
        form=status_form,
    )


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id: int):
    """Cập nhật trạng thái đơn đặt xe và trạng thái thanh toán tiền cọc."""
    order = db.session.get(Order, order_id)
    form = OrderStatusForm()
    if order and form.validate_on_submit():
        order.status = form.status.data
        order.payment_status = form.payment_status.data
        db.session.commit()
        flash(f"Đã cập nhật trạng thái đơn hàng {order.order_code}.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/test-drives/<int:td_id>/approve", methods=["POST"])
@admin_required
def approve_test_drive(td_id: int):
    """Xác nhận lịch hẹn lái thử cho khách hàng."""
    td = db.session.get(TestDrive, td_id)
    if td:
        td.status = "confirmed"
        db.session.commit()
        flash(f"Đã xác nhận lịch hẹn lái thử #{td.id}.", "success")
    return redirect(url_for("admin.orders"))
