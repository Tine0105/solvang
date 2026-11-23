from flask import render_template, request
from flask_login import current_user
from sqlalchemy import or_

from app.blueprints.cars import cars_bp
from app.forms import OrderForm, TestDriveForm
from app.models import Brand, Car, Favorite


@cars_bp.route('/')
def list_cars():
    query = Car.query.join(Brand)

    q = request.args.get('q', '').strip()
    brand_id = request.args.get('brand', type=int)
    body_type = request.args.get('body_type', '').strip()
    fuel_type = request.args.get('fuel_type', '').strip()
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)

    if q:
        like_term = f'%{q}%'
        query = query.filter(
            or_(
                Car.name.ilike(like_term),
                Brand.name.ilike(like_term),
                Car.description.ilike(like_term),
            )
        )
    if brand_id:
        query = query.filter(Car.brand_id == brand_id)
    if body_type:
        query = query.filter(Car.body_type == body_type)
    if fuel_type:
        query = query.filter(Car.fuel_type == fuel_type)
    if min_price is not None:
        query = query.filter(Car.price >= min_price)
    if max_price is not None:
        query = query.filter(Car.price <= max_price)

    if sort == 'price_asc':
        query = query.order_by(Car.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Car.price.desc())
    elif sort == 'year_desc':
        query = query.order_by(Car.year.desc())
    else:
        query = query.order_by(Car.created_at.desc())

    pagination = query.paginate(page=page, per_page=9, error_out=False)
    brands = Brand.query.order_by(Brand.name.asc()).all()

    return render_template(
        'cars/list.html',
        cars=pagination.items,
        pagination=pagination,
        brands=brands,
        filters={
            'q': q,
            'brand': brand_id,
            'body_type': body_type,
            'fuel_type': fuel_type,
            'min_price': min_price,
            'max_price': max_price,
            'sort': sort,
        },
    )


@cars_bp.route('/<slug>')
def detail(slug):
    car = Car.query.filter_by(slug=slug).first_or_404()

    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = (
            Favorite.query.filter_by(user_id=current_user.id, car_id=car.id).first() is not None
        )

    order_form = OrderForm()
    order_form.color_id.choices = [(c.id, c.color_name) for c in car.colors]
    if not order_form.color_id.choices:
        order_form.color_id.choices = [(0, 'Màu tiêu chuẩn')]

    test_drive_form = TestDriveForm()

    related_cars = (
        Car.query.filter(Car.brand_id == car.brand_id, Car.id != car.id)
        .limit(3)
        .all()
    )

    return render_template(
        'cars/detail.html',
        car=car,
        is_favorite=is_favorite,
        order_form=order_form,
        test_drive_form=test_drive_form,
        related_cars=related_cars,
    )
