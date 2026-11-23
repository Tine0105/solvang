from flask import Blueprint

cars_bp = Blueprint('cars', __name__, url_prefix='/cars')

from app.blueprints.cars import routes  # noqa: E402, F401
