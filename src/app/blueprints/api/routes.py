"""Blueprint RESTful API cung cấp dữ liệu xe sang và tỷ giá định dạng JSON (CLO3)."""

from flask import current_app, jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.api import api_bp
from app.models import Brand, Car
from app.services.exchange_service import get_exchange_rates


@api_bp.route("/cars", methods=["GET"])
def get_cars():
    """Trả về danh sách xe sang dạng JSON hỗ trợ tìm kiếm, lọc và phân trang."""
    q = request.args.get("q", "").strip()
    brand_id = request.args.get("brand_id", type=int)
    body_type = request.args.get("body_type", "").strip()
    fuel_type = request.args.get("fuel_type", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", current_app.config["CARS_PER_PAGE"], type=int), 24)

    query = Car.query.options(joinedload(Car.brand)).join(Brand)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Car.name.ilike(pattern),
                Brand.name.ilike(pattern),
                Car.description.ilike(pattern),
            )
        )
    if brand_id:
        query = query.filter(Car.brand_id == brand_id)
    if body_type:
        query = query.filter(Car.body_type == body_type)
    if fuel_type:
        query = query.filter(Car.fuel_type == fuel_type)

    pagination = query.order_by(Car.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    rates = get_exchange_rates()
    usd_rate = rates["usd_to_vnd"]

    return jsonify(
        {
            "status": "success",
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "exchange_rate_usd_vnd": usd_rate,
            "rate_source": rates["source"],
            "items": [car.to_dict(usd_rate=usd_rate) for car in pagination.items],
        }
    )


@api_bp.route("/cars/<slug>", methods=["GET"])
def get_car_detail(slug: str):
    """Trả về thông tin chi tiết một mẫu xe sang theo slug dưới dạng JSON."""
    car = Car.query.options(joinedload(Car.brand)).filter_by(slug=slug).first()
    if not car:
        return jsonify({"status": "error", "message": "Không tìm thấy mẫu xe yêu cầu."}), 404

    rates = get_exchange_rates()
    data = car.to_dict(usd_rate=rates["usd_to_vnd"])
    data["description"] = car.description
    data["gallery"] = [img.image_url for img in car.images]
    return jsonify({"status": "success", "data": data})


@api_bp.route("/exchange-rate", methods=["GET"])
def exchange_rate():
    """Endpoint trả về tỷ giá quy đổi USD/VND và EUR/VND hiện tại."""
    rates = get_exchange_rates()
    return jsonify({"status": "success", "data": rates})
