import hashlib
import os
import uuid
from pathlib import Path
from flask import render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import func
from PIL import Image

from app.blueprints.admin import admin_bp
from app.decorators import admin_required
from app.extensions import db
from app.forms import BrandForm, CarForm, CarColorForm, OrderStatusForm, TestDriveStatusForm
from app.models import Brand, Car, CarColor, CarImage, CarModel, Order, TestDriveRequest, User
from scripts.inspect_glb import inspect_glb
from scripts.optimize_images import compute_dhash


def _allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def _save_upload(file_storage, target_folder: str, allowed_extensions: set[str], web_prefix: str) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not _allowed_file(filename, allowed_extensions):
        return None
    os.makedirs(target_folder, exist_ok=True)
    unique_name = f'{uuid.uuid4().hex[:10]}_{filename}'
    file_storage.save(os.path.join(target_folder, unique_name))
    return f'{web_prefix}/{unique_name}'


def _record_uploaded_image(car: Car, web_url: str, is_hero: bool = False) -> CarImage:
    disk_path = Path(current_app.static_folder) / web_url.lstrip('/').replace('static/', '', 1)
    raw = disk_path.read_bytes()
    sha256_hex = hashlib.sha256(raw).hexdigest()
    with Image.open(disk_path) as im:
        w, h = im.size
        phash = compute_dhash(im)
    img = CarImage(
        car_id=car.id,
        image_url=web_url,
        license='Admin Upload',
        author='Showroom Admin',
        source_url=web_url,
        sha256=sha256_hex,
        phash=phash,
        width=w,
        height=h,
        file_size=len(raw),
        is_hero=is_hero,
        is_active=True,
        sort_order=0 if is_hero else 10,
        shot_type='hero' if is_hero else 'exterior',
        match_level='exact',
        source_name='Admin Upload',
    )
    db.session.add(img)
    return img


def _record_uploaded_model(car: Car, web_url: str) -> CarModel | None:
    disk_path = Path(current_app.static_folder) / web_url.lstrip('/').replace('static/', '', 1)
    try:
        info = inspect_glb(disk_path)
    except Exception as exc:
        flash(f'File .glb không hợp lệ: {exc}', 'danger')
        disk_path.unlink(missing_ok=True)
        return None

    raw = disk_path.read_bytes()
    for old_m in car.models_3d:
        old_m.is_active = False

    cm = CarModel(
        car_id=car.id,
        file_path=web_url,
        file_format='glb',
        file_size=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        poly_count=info.get('poly_count', 0),
        source_name='Admin Upload',
        source_url=web_url,
        author='Showroom Admin',
        license='Custom Upload',
        body_material_names=info.get('body_material_names', []),
        scale=1.0,
        offset_y=0.0,
        is_active=True,
    )
    db.session.add(cm)
    car.model_url = web_url
    car.body_material_names = cm.body_material_names
    return cm


@admin_bp.route('/')
@admin_required
def dashboard():
    stats = {
        'total_cars': Car.query.count(),
        'total_brands': Brand.query.count(),
        'total_users': User.query.count(),
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'pending_test_drives': TestDriveRequest.query.filter_by(status='pending').count(),
        'confirmed_revenue': (
            db.session.query(func.coalesce(func.sum(Car.price), 0))
            .select_from(Order)
            .join(Car, Order.car_id == Car.id)
            .filter(Order.status == 'confirmed')
            .scalar()
        ),
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    recent_test_drives = TestDriveRequest.query.order_by(TestDriveRequest.created_at.desc()).limit(6).all()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_orders=recent_orders,
        recent_test_drives=recent_test_drives,
    )


# --- Brands ---
@admin_bp.route('/brands', methods=['GET', 'POST'])
@admin_required
def brands():
    form = BrandForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Brand.query.filter_by(name=name).first():
            flash('Hãng xe này đã tồn tại.', 'warning')
        else:
            logo_url = _save_upload(
                form.logo_file.data,
                current_app.config['UPLOAD_IMAGE_FOLDER'],
                current_app.config['ALLOWED_IMAGE_EXTENSIONS'],
                '/static/img/uploads',
            )
            brand = Brand(name=name, logo=logo_url or '/static/img/brands/default.svg')
            db.session.add(brand)
            db.session.commit()
            flash(f'Đã thêm hãng xe {brand.name}.', 'success')
            return redirect(url_for('admin.brands'))

    all_brands = Brand.query.order_by(Brand.name.asc()).all()
    return render_template('admin/brands.html', brands=all_brands, form=form)


@admin_bp.route('/brands/<int:brand_id>/delete', methods=['POST'])
@admin_required
def delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    db.session.delete(brand)
    db.session.commit()
    flash(f'Đã xóa hãng xe {brand.name}.', 'info')
    return redirect(url_for('admin.brands'))


# --- Cars ---
@admin_bp.route('/cars')
@admin_required
def cars():
    all_cars = Car.query.order_by(Car.created_at.desc()).all()
    return render_template('admin/cars.html', cars=all_cars)


@admin_bp.route('/cars/new', methods=['GET', 'POST'])
@admin_required
def create_car():
    form = CarForm()
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.order_by(Brand.name.asc()).all()]

    if form.validate_on_submit():
        if Car.query.filter_by(slug=form.slug.data.strip()).first():
            form.slug.errors.append('Slug này đã tồn tại.')
        else:
            uploaded_thumb = _save_upload(
                form.thumbnail_file.data,
                current_app.config['UPLOAD_IMAGE_FOLDER'],
                current_app.config['ALLOWED_IMAGE_EXTENSIONS'],
                '/static/img/uploads',
            )
            thumb_url = uploaded_thumb or '/static/img/brands/default.svg'

            model_url = _save_upload(
                form.model_file.data,
                current_app.config['UPLOAD_MODEL_FOLDER'],
                current_app.config['ALLOWED_MODEL_EXTENSIONS'],
                '/static/models',
            )

            car = Car(
                brand_id=form.brand_id.data,
                name=form.name.data.strip(),
                slug=form.slug.data.strip(),
                year=form.year.data,
                price=form.price.data,
                mileage=form.mileage.data or 0,
                fuel_type=form.fuel_type.data,
                transmission=form.transmission.data,
                body_type=form.body_type.data,
                seats=form.seats.data,
                stock=form.stock.data,
                is_featured=form.is_featured.data,
                description=form.description.data.strip(),
                thumbnail=thumb_url,
                model_url=model_url,
            )
            db.session.add(car)
            db.session.flush()

            db.session.add(CarColor(car_id=car.id, color_name='Đen Obsidian', hex_code='#16191f'))

            if uploaded_thumb:
                _record_uploaded_image(car, uploaded_thumb, is_hero=True)
            if model_url:
                _record_uploaded_model(car, model_url)

            for img_file in request.files.getlist('gallery_files'):
                saved_img = _save_upload(
                    img_file,
                    current_app.config['UPLOAD_IMAGE_FOLDER'],
                    current_app.config['ALLOWED_IMAGE_EXTENSIONS'],
                    '/static/img/uploads',
                )
                if saved_img:
                    _record_uploaded_image(car, saved_img, is_hero=False)

            db.session.commit()
            flash(f'Đã thêm mẫu xe {car.name}.', 'success')
            return redirect(url_for('admin.edit_car', car_id=car.id))

    return render_template('admin/car_form.html', form=form, car=None, color_form=None)


@admin_bp.route('/cars/<int:car_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    form = CarForm(obj=car)
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.order_by(Brand.name.asc()).all()]
    color_form = CarColorForm()

    if form.validate_on_submit():
        existing_slug = Car.query.filter(Car.slug == form.slug.data.strip(), Car.id != car.id).first()
        if existing_slug:
            form.slug.errors.append('Slug này đã được sử dụng bởi xe khác.')
        else:
            car.brand_id = form.brand_id.data
            car.name = form.name.data.strip()
            car.slug = form.slug.data.strip()
            car.year = form.year.data
            car.price = form.price.data
            car.mileage = form.mileage.data or 0
            car.fuel_type = form.fuel_type.data
            car.transmission = form.transmission.data
            car.body_type = form.body_type.data
            car.seats = form.seats.data
            car.stock = form.stock.data
            car.is_featured = form.is_featured.data
            car.description = form.description.data.strip()

            new_thumb = _save_upload(
                form.thumbnail_file.data,
                current_app.config['UPLOAD_IMAGE_FOLDER'],
                current_app.config['ALLOWED_IMAGE_EXTENSIONS'],
                '/static/img/uploads',
            )
            if new_thumb:
                car.thumbnail = new_thumb
                for old_img in car.images:
                    old_img.is_hero = False
                _record_uploaded_image(car, new_thumb, is_hero=True)

            new_model = _save_upload(
                form.model_file.data,
                current_app.config['UPLOAD_MODEL_FOLDER'],
                current_app.config['ALLOWED_MODEL_EXTENSIONS'],
                '/static/models',
            )
            if new_model:
                _record_uploaded_model(car, new_model)

            for img_file in request.files.getlist('gallery_files'):
                saved_img = _save_upload(
                    img_file,
                    current_app.config['UPLOAD_IMAGE_FOLDER'],
                    current_app.config['ALLOWED_IMAGE_EXTENSIONS'],
                    '/static/img/uploads',
                )
                if saved_img:
                    _record_uploaded_image(car, saved_img, is_hero=False)

            db.session.commit()
            flash(f'Đã cập nhật thông tin xe {car.name}.', 'success')
            return redirect(url_for('admin.edit_car', car_id=car.id))

    return render_template('admin/car_form.html', form=form, car=car, color_form=color_form)


@admin_bp.route('/cars/<int:car_id>/delete', methods=['POST'])
@admin_required
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    flash(f'Đã xóa mẫu xe {car.name}.', 'info')
    return redirect(url_for('admin.cars'))


@admin_bp.route('/cars/<int:car_id>/colors/add', methods=['POST'])
@admin_required
def add_car_color(car_id):
    car = Car.query.get_or_404(car_id)
    form = CarColorForm()
    if form.validate_on_submit():
        color = CarColor(
            car_id=car.id,
            color_name=form.color_name.data.strip(),
            hex_code=form.hex_code.data.strip().upper(),
        )
        db.session.add(color)
        db.session.commit()
        flash(f'Đã thêm màu {color.color_name}.', 'success')
    else:
        for errs in form.errors.values():
            for e in errs:
                flash(e, 'danger')
    return redirect(url_for('admin.edit_car', car_id=car.id))


@admin_bp.route('/colors/<int:color_id>/delete', methods=['POST'])
@admin_required
def delete_car_color(color_id):
    color = CarColor.query.get_or_404(color_id)
    car_id = color.car_id
    db.session.delete(color)
    db.session.commit()
    flash('Đã xóa màu sơn.', 'info')
    return redirect(url_for('admin.edit_car', car_id=car_id))


# --- Car Images & 3D Models Management ---
@admin_bp.route('/images/<int:image_id>/hero', methods=['POST'])
@admin_required
def set_hero_image(image_id):
    img = CarImage.query.get_or_404(image_id)
    car = img.car
    for item in car.images:
        item.is_hero = (item.id == img.id)
    img.is_active = True
    img.sort_order = 0
    car.thumbnail = img.image_url.replace('.webp', '-thumb.webp') if img.image_url.endswith('.webp') and not img.image_url.endswith('-thumb.webp') else img.image_url
    db.session.commit()
    flash('Đã đặt ảnh làm ảnh đại diện (Hero).', 'success')
    return redirect(url_for('admin.edit_car', car_id=car.id))


@admin_bp.route('/images/<int:image_id>/toggle', methods=['POST'])
@admin_required
def toggle_image_active(image_id):
    img = CarImage.query.get_or_404(image_id)
    img.is_active = not img.is_active
    db.session.commit()
    flash('Đã cập nhật trạng thái hiển thị ảnh.', 'info')
    return redirect(url_for('admin.edit_car', car_id=img.car_id))


@admin_bp.route('/images/<int:image_id>/sort', methods=['POST'])
@admin_required
def update_image_sort(image_id):
    img = CarImage.query.get_or_404(image_id)
    try:
        img.sort_order = int(request.form.get('sort_order', 0))
        db.session.commit()
        flash('Đã cập nhật thứ tự sắp xếp ảnh.', 'success')
    except ValueError:
        flash('Thứ tự không hợp lệ.', 'danger')
    return redirect(url_for('admin.edit_car', car_id=img.car_id))


@admin_bp.route('/images/<int:image_id>/delete', methods=['POST'])
@admin_required
def delete_car_image(image_id):
    img = CarImage.query.get_or_404(image_id)
    car_id = img.car_id
    db.session.delete(img)
    db.session.commit()
    flash('Đã xóa ảnh khỏi thư viện.', 'info')
    return redirect(url_for('admin.edit_car', car_id=car_id))


@admin_bp.route('/models/<int:model_id>/toggle', methods=['POST'])
@admin_required
def toggle_car_model(model_id):
    cm = CarModel.query.get_or_404(model_id)
    car = cm.car
    if not cm.is_active:
        for other in car.models_3d:
            other.is_active = (other.id == cm.id)
        car.model_url = cm.file_path
        car.body_material_names = cm.body_material_names
    else:
        cm.is_active = False
    db.session.commit()
    flash('Đã cập nhật trạng thái Model 3D.', 'success')
    return redirect(url_for('admin.edit_car', car_id=car.id))


# --- Orders ---
@admin_bp.route('/orders')
@admin_required
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    form = OrderStatusForm()
    return render_template('admin/orders.html', orders=all_orders, form=form)


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    form = OrderStatusForm()
    if form.validate_on_submit():
        order.status = form.status.data
        db.session.commit()
        flash(f'Đã cập nhật trạng thái đơn hàng #{order.id}.', 'success')
    return redirect(url_for('admin.orders'))


# --- Test Drives ---
@admin_bp.route('/test-drives')
@admin_required
def test_drives():
    all_requests = TestDriveRequest.query.order_by(TestDriveRequest.created_at.desc()).all()
    form = TestDriveStatusForm()
    return render_template('admin/test_drives.html', test_drives=all_requests, form=form)


@admin_bp.route('/test-drives/<int:req_id>/status', methods=['POST'])
@admin_required
def update_test_drive_status(req_id):
    req = TestDriveRequest.query.get_or_404(req_id)
    form = TestDriveStatusForm()
    if form.validate_on_submit():
        req.status = form.status.data
        db.session.commit()
        flash(f'Đã cập nhật lịch lái thử #{req.id}.', 'success')
    return redirect(url_for('admin.test_drives'))
