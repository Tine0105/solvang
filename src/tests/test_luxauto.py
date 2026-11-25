"""Bộ kiểm thử tự động các chức năng cốt lõi của hệ thống LuxAuto Showroom (14 ca kiểm thử)."""

import io
from urllib.error import URLError
from unittest.mock import patch
from PIL import Image

from app.extensions import db, mail
from app.models import Brand, Car, Order, User
from app.services.exchange_service import clear_rate_cache, get_exchange_rates


def _login(client, email: str, password: str):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_01_home_page_loads(client):
    """TC01: Trang chủ hiển thị thành công (HTTP 200) kèm danh sách xe tiêu điểm."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "LUXAUTO" in html
    assert "Porsche Model S1" in html


def test_02_register_account_and_send_welcome_email(client, app):
    """TC02: Đăng ký thành viên mới băm mật khẩu an toàn và gửi email xác nhận qua Flask-Mail."""
    with mail.record_messages() as outbox:
        resp = client.post(
            "/auth/register",
            data={
                "full_name": "Nguyễn Văn Khách",
                "email": "newmember@luxauto.vn",
                "phone": "0988123456",
                "password": "Secret@123",
                "confirm_password": "Secret@123",
            },
            follow_redirects=True,
        )
    assert resp.status_code == 200
    assert len(outbox) == 1
    assert "newmember@luxauto.vn" in outbox[0].recipients

    with app.app_context():
        created = User.query.filter_by(email="newmember@luxauto.vn").first()
        assert created is not None
        assert created.password_hash != "Secret@123"
        assert created.check_password("Secret@123")


def test_03_register_duplicate_email_rejected(client):
    """TC03: Từ chối đăng ký khi địa chỉ email đã tồn tại trong CSDL."""
    resp = client.post(
        "/auth/register",
        data={
            "full_name": "Trùng Email",
            "email": "user@luxauto.vn",
            "password": "User@123",
            "confirm_password": "User@123",
        },
        follow_redirects=True,
    )
    assert "đã được đăng ký" in resp.get_data(as_text=True)


def test_04_login_and_logout_flow(client):
    """TC04: Kiểm tra đăng nhập sai mật khẩu, đăng nhập đúng và đăng xuất."""
    bad = _login(client, "user@luxauto.vn", "WrongPass")
    assert "không chính xác" in bad.get_data(as_text=True)

    ok = _login(client, "user@luxauto.vn", "User@123")
    assert "đăng nhập thành công" in ok.get_data(as_text=True)

    out = client.post("/auth/logout", follow_redirects=True)
    assert "đăng xuất" in out.get_data(as_text=True)


def test_05_rbac_user_forbidden_on_admin_routes(client):
    """TC05: Phân quyền RBAC chặn tài khoản 'user' truy cập '/admin/' bằng mã 403."""
    _login(client, "user@luxauto.vn", "User@123")
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_06_admin_dashboard_and_kpi_stats(client):
    """TC06: Quản trị viên truy cập thành công Dashboard kèm dữ liệu biểu đồ."""
    _login(client, "admin@luxauto.vn", "Admin@123")
    resp = client.get("/admin/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Bảng Điều Khiển" in html
    assert "brandChart" in html


def test_07_admin_crud_create_update_delete_car_with_upload(client, app):
    """TC07: Admin thực hiện trọn vẹn Thêm xe mới (kèm upload ảnh), Sửa giá và Xóa xe."""
    _login(client, "admin@luxauto.vn", "Admin@123")

    with app.app_context():
        brand_id = Brand.query.filter_by(name="Porsche").first().id

    # Sinh 1 ảnh PNG hợp lệ trong bộ nhớ để test upload thực tế
    img_buf = io.BytesIO()
    Image.new("RGB", (640, 400), color=(30, 40, 60)).save(img_buf, format="PNG")
    img_buf.seek(0)

    create_resp = client.post(
        "/admin/cars/new",
        data={
            "brand_id": brand_id,
            "name": "Porsche 911 Turbo S",
            "slug": "porsche-911-turbo-s",
            "year": 2026,
            "price": 15_800_000_000,
            "horsepower": 650,
            "mileage": 0,
            "fuel_type": "Xăng",
            "transmission": "Ly hợp kép PDK 8 cấp",
            "body_type": "Coupe",
            "exterior_color": "Vàng Racing Yellow",
            "seats": 4,
            "stock": 2,
            "is_featured": "y",
            "description": "Phiên bản đầu bảng dòng 911 với công suất 650 mã lực và dẫn động bốn bánh.",
            "thumbnail_file": (img_buf, "turbo_s.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert create_resp.status_code == 200

    with app.app_context():
        car = Car.query.filter_by(slug="porsche-911-turbo-s").first()
        assert car is not None
        assert car.thumbnail_url.startswith("/static/uploads/cars/")
        car_id = car.id

    # Cập nhật giá xe
    edit_resp = client.post(
        f"/admin/cars/{car_id}/edit",
        data={
            "brand_id": brand_id,
            "name": "Porsche 911 Turbo S Cabriolet",
            "slug": "porsche-911-turbo-s",
            "year": 2026,
            "price": 16_500_000_000,
            "horsepower": 650,
            "mileage": 100,
            "fuel_type": "Xăng",
            "transmission": "Ly hợp kép PDK 8 cấp",
            "body_type": "Roadster",
            "exterior_color": "Vàng Racing Yellow",
            "seats": 4,
            "stock": 1,
            "description": "Phiên bản mui trần cập nhật giá niêm yết mới chính hãng.",
        },
        follow_redirects=True,
    )
    assert edit_resp.status_code == 200
    with app.app_context():
        assert db.session.get(Car, car_id).price == 16_500_000_000

    # Xóa xe
    del_resp = client.post(f"/admin/cars/{car_id}/delete", follow_redirects=True)
    assert del_resp.status_code == 200
    with app.app_context():
        assert db.session.get(Car, car_id) is None


def test_08_car_search_and_multi_filter(client):
    """TC08: Tìm kiếm theo từ khóa 'Lamborghini' trả về đúng các xe thuộc hãng."""
    resp = client.get("/cars?q=Lamborghini")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Lamborghini Model S6" in html
    assert "Porsche Model S1" not in html


def test_09_car_catalog_pagination(client):
    """TC09: Phân trang danh sách xe (8 xe, per_page=6 -> trang 1 có 6 xe, trang 2 có 2 xe)."""
    page1 = client.get("/cars?page=1")
    page2 = client.get("/cars?page=2")
    assert page1.status_code == 200
    assert page2.status_code == 200
    assert "Trang 1/2" in page1.get_data(as_text=True)
    assert "Trang 2/2" in page2.get_data(as_text=True)


def test_10_forgot_and_reset_password_with_signed_token(client, app):
    """TC10: Luồng quên mật khẩu gửi email token và đặt lại mật khẩu mới thành công."""
    with mail.record_messages() as outbox:
        client.post("/auth/forgot-password", data={"email": "user@luxauto.vn"})
    assert len(outbox) == 1

    with app.app_context():
        user = User.query.filter_by(email="user@luxauto.vn").first()
        token = user.generate_reset_token()

    reset_resp = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "NewPass@999", "confirm_password": "NewPass@999"},
        follow_redirects=True,
    )
    assert reset_resp.status_code == 200
    login_new = _login(client, "user@luxauto.vn", "NewPass@999")
    assert "đăng nhập thành công" in login_new.get_data(as_text=True)


def test_11_favorites_many_to_many_relationship(client, app):
    """TC11: Kiểm tra thêm và xóa xe trong danh sách yêu thích (quan hệ n-n)."""
    _login(client, "user@luxauto.vn", "User@123")
    with app.app_context():
        car_id = Car.query.first().id

    client.post(f"/favorites/toggle/{car_id}", follow_redirects=True)
    with app.app_context():
        u = User.query.filter_by(email="user@luxauto.vn").first()
        assert len(u.favorite_cars) == 1

    client.post(f"/favorites/toggle/{car_id}", follow_redirects=True)
    with app.app_context():
        u = User.query.filter_by(email="user@luxauto.vn").first()
        assert len(u.favorite_cars) == 0


def test_12_order_deposit_and_qr_payment_demo(client, app):
    """TC12: Khách hàng đặt cọc xe sang (5%) và hoàn tất thanh toán QR Demo."""
    _login(client, "user@luxauto.vn", "User@123")
    with app.app_context():
        car = Car.query.first()
        car_id = car.id
        expected_deposit = int(car.price * 0.05)

    resp = client.post(
        f"/orders/create/{car_id}",
        data={
            "customer_phone": "0909888777",
            "payment_method": "bank_qr",
            "note": "Đặt cọc kiểm thử tự động",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "CỔNG THANH TOÁN ĐẶT CỌC DEMO" in resp.get_data(as_text=True)

    with app.app_context():
        order = Order.query.first()
        assert order is not None
        assert order.deposit_amount == expected_deposit
        order_id = order.id

    pay_resp = client.post(f"/orders/{order_id}/pay-demo", follow_redirects=True)
    assert pay_resp.status_code == 200
    with app.app_context():
        updated_order = db.session.get(Order, order_id)
        assert updated_order.payment_status == "paid"
        assert updated_order.status == "confirmed"


def test_13_rest_api_cars_and_detail_endpoints(client):
    """TC13: Kiểm tra RESTful API '/api/cars' và '/api/cars/<slug>' trả JSON chuẩn."""
    list_resp = client.get("/api/cars?q=Porsche&per_page=3")
    assert list_resp.status_code == 200
    payload = list_resp.get_json()
    assert payload["status"] == "success"
    assert payload["total"] == 5
    assert len(payload["items"]) == 3
    assert "price_usd_estimated" in payload["items"][0]

    detail_resp = client.get("/api/cars/porsche-model-s1")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["data"]["slug"] == "porsche-model-s1"

    missing_resp = client.get("/api/cars/khong-ton-tai")
    assert missing_resp.status_code == 404


def test_14_exchange_service_urllib_network_error_fallback(app):
    """TC14: Khi urllib gặp lỗi mạng/timeout, dịch vụ tỷ giá tự động chuyển sang giá trị dự phòng."""
    with app.app_context():
        clear_rate_cache()
        with patch("app.services.exchange_service.urlopen", side_effect=URLError("Network unreachable")):
            rates = get_exchange_rates(force_refresh=True)
        assert rates["source"] == "fallback"
        assert rates["usd_to_vnd"] > 0


def test_15_car_3d_glb_upload_and_viewer_stage(client, app):
    """TC15: Kiểm tra upload tệp mô hình 3D (.glb) nhị phân hợp lệ và hiển thị trình xem Three.js."""
    _login(client, "admin@luxauto.vn", "Admin@123")
    with app.app_context():
        car = Car.query.first()
        car_id = car.id
        slug = car.slug
        brand_id = car.brand_id

    # Giả lập tệp glTF 2.0 nhị phân hợp lệ bắt đầu bằng magic bytes b'glTF'
    fake_glb = io.BytesIO(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 64)
    resp = client.post(
        f"/admin/cars/{car_id}/edit",
        data={
            "brand_id": brand_id,
            "name": "Porsche 3D Studio Edition",
            "slug": slug,
            "year": 2026,
            "price": 9_500_000_000,
            "horsepower": 520,
            "mileage": 0,
            "fuel_type": "Xăng",
            "transmission": "Ly hợp kép PDK 8 cấp",
            "body_type": "Coupe",
            "exterior_color": "Vàng Champagne",
            "seats": 4,
            "stock": 2,
            "description": "Phiên bản tích hợp mô hình 3D glTF tương tác 360 độ.",
            "model_file": (fake_glb, "porsche_studio.glb"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200

    detail_resp = client.get(f"/cars/{slug}")
    html = detail_resp.get_data(as_text=True)
    assert "data-car-viewer" in html
    assert "/static/models/" in html
