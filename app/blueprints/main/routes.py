import hashlib
import json
import os
from flask import Response, abort, current_app, render_template, request
from app.blueprints.main import main_bp
from app.models import Brand, Car, CarImage, CarModel


@main_bp.route('/')
def index():
    featured_cars = (
        Car.query.filter_by(is_featured=True)
        .order_by(Car.created_at.desc())
        .limit(6)
        .all()
    )
    hero_car = featured_cars[0] if featured_cars else Car.query.order_by(Car.id.asc()).first()
    brands = Brand.query.order_by(Brand.name.asc()).all()
    total_cars = Car.query.count()
    return render_template(
        'main/index.html',
        hero_car=hero_car,
        featured_cars=featured_cars,
        brands=brands,
        total_cars=total_cars,
    )


@main_bp.route('/media/image/<int:image_id>')
def serve_image_blob(image_id: int):
    img = CarImage.query.get_or_404(image_id)
    if not img.image_blob:
        abort(404)
    etag = img.sha256 or hashlib.sha256(img.image_blob).hexdigest()
    if request.if_none_match and etag in request.if_none_match:
        return Response(status=304, headers={'ETag': f'"{etag}"', 'Cache-Control': 'public, max-age=604800'})
    return Response(
        img.image_blob,
        mimetype='image/webp',
        headers={
            'ETag': f'"{etag}"',
            'Cache-Control': 'public, max-age=604800',
        },
    )


@main_bp.route('/credits')
def credits():
    cars = Car.query.order_by(Car.id.asc()).all()
    assets_path = os.path.join(current_app.static_folder, 'ASSETS.json')
    hdris = []
    if os.path.exists(assets_path):
        try:
            with open(assets_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    hdris = loaded.get('hdris', [])
        except (OSError, json.JSONDecodeError):
            pass
    total_models = CarModel.query.filter_by(is_active=True).count()
    total_images = CarImage.query.filter_by(is_active=True).count()
    return render_template(
        'main/credits.html',
        cars=cars,
        hdris=hdris,
        total_models=total_models,
        total_images=total_images,
    )
