"""Cấu hình fixtures dùng chung cho bộ kiểm thử tự động pytest."""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Brand, Car, User  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    """Tạo ứng dụng Flask ở chế độ TestingConfig với SQLite in-memory và thư mục upload tạm."""
    test_app = create_app("testing")
    test_app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    os.makedirs(test_app.config["UPLOAD_FOLDER"], exist_ok=True)

    with test_app.app_context():
        db.create_all()

        admin = User(full_name="Admin Test", email="admin@luxauto.vn", role="admin")
        admin.set_password("Admin@123")
        user = User(full_name="User Test", email="user@luxauto.vn", phone="0909111222", role="user")
        user.set_password("User@123")
        db.session.add_all([admin, user])
        db.session.flush()

        porsche = Brand(name="Porsche", country="Đức", logo_url="/static/img/brands/porsche.svg")
        lambo = Brand(name="Lamborghini", country="Ý", logo_url="/static/img/brands/lamborghini.svg")
        db.session.add_all([porsche, lambo])
        db.session.flush()

        # Tạo 8 mẫu xe sang để kiểm tra tìm kiếm và phân trang (per_page = 6 -> 2 trang)
        for i in range(1, 9):
            brand = porsche if i <= 5 else lambo
            db.session.add(
                Car(
                    brand_id=brand.id,
                    name=f"{brand.name} Model S{i}",
                    slug=f"{brand.name.lower()}-model-s{i}",
                    year=2026,
                    price=4_000_000_000 + i * 1_200_000_000,
                    horsepower=450 + i * 25,
                    mileage=0,
                    fuel_type="Xăng" if i % 2 == 1 else "Hybrid",
                    transmission="Ly hợp kép PDK 8 cấp",
                    body_type="Coupe" if i <= 6 else "SUV",
                    exterior_color="Đen Obsidian",
                    seats=4,
                    stock=2,
                    is_featured=(i <= 3),
                    thumbnail_url="/static/img/cars/porsche-911-carrera/hero-1280w.webp",
                    description=f"Mô tả chi tiết kiểm thử cho mẫu xe hạng sang số {i} chính hãng.",
                )
            )
        db.session.commit()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """HTTP test client của Flask."""
    return app.test_client()
