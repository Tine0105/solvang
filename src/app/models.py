"""Định nghĩa các Model cơ sở dữ liệu SQLAlchemy cho hệ thống LuxAuto Showroom."""

from datetime import datetime, timezone
from flask import current_app
from flask_login import UserMixin
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def utcnow() -> datetime:
    """Trả về thời gian UTC hiện tại (naive) tương thích tốt với SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Bảng phụ biểu diễn quan hệ nhiều-nhiều (n-n) giữa User và Car (Danh sách yêu thích)
favorites = db.Table(
    "favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("car_id", db.Integer, db.ForeignKey("cars.id", ondelete="CASCADE"), primary_key=True),
    db.Column("created_at", db.DateTime, nullable=False, default=utcnow),
)


class User(UserMixin, db.Model):
    """Model người dùng hệ thống (phân quyền 2 vai trò: 'admin' và 'user')."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_verified = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Quan hệ 1-n và n-n
    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")
    test_drives = db.relationship("TestDrive", back_populates="user", cascade="all, delete-orphan")
    favorite_cars = db.relationship(
        "Car",
        secondary=favorites,
        back_populates="favorited_by",
        lazy="subquery",
    )

    def set_password(self, raw_password: str) -> None:
        """Băm mật khẩu một chiều bằng PBKDF2/Scrypt của Werkzeug."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Kiểm tra mật khẩu người dùng nhập so với chuỗi băm lưu trữ."""
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        """Trả về True nếu tài khoản thuộc nhóm quản trị viên."""
        return self.role == "admin"

    def generate_reset_token(self) -> str:
        """Sinh token ký số có thời hạn để đặt lại mật khẩu."""
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps({"user_id": self.id}, salt="luxauto-password-reset")

    @staticmethod
    def verify_reset_token(token: str, max_age: int | None = None):
        """Giải mã và xác thực token đặt lại mật khẩu; trả về User hoặc None."""
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        ttl = max_age or current_app.config.get("RESET_TOKEN_MAX_AGE", 3600)
        try:
            data = serializer.loads(token, salt="luxauto-password-reset", max_age=ttl)
        except (SignatureExpired, BadSignature):
            return None
        user_id = data.get("user_id")
        return db.session.get(User, int(user_id)) if user_id else None

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id: str):
    """Hàm callback nạp đối tượng User từ session cho Flask-Login."""
    return db.session.get(User, int(user_id))


class Brand(db.Model):
    """Model thương hiệu xe sang (Porsche, Lamborghini, Mercedes-AMG, ...)."""

    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    country = db.Column(db.String(60), nullable=False, default="Đức")
    logo_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(300), nullable=True)

    # Quan hệ 1-n với Car
    cars = db.relationship("Car", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Brand {self.name}>"


class Car(db.Model):
    """Model mẫu xe sang — đối tượng nghiệp vụ chính của hệ thống CRUD."""

    __tablename__ = "cars"

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(140), nullable=False, index=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.BigInteger, nullable=False, index=True)
    horsepower = db.Column(db.Integer, nullable=False, default=500)
    mileage = db.Column(db.Integer, nullable=False, default=0)
    fuel_type = db.Column(db.String(40), nullable=False)
    transmission = db.Column(db.String(50), nullable=False)
    body_type = db.Column(db.String(40), nullable=False)
    exterior_color = db.Column(db.String(60), nullable=False, default="Đen Obsidian")
    seats = db.Column(db.Integer, nullable=False, default=4)
    stock = db.Column(db.Integer, nullable=False, default=1)
    thumbnail_url = db.Column(db.String(255), nullable=False)
    model_3d_url = db.Column(db.String(255), nullable=True)
    body_material_names = db.Column(db.JSON, nullable=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Quan hệ với các bảng liên quan
    brand = db.relationship("Brand", back_populates="cars")
    images = db.relationship(
        "CarImage",
        back_populates="car",
        cascade="all, delete-orphan",
        order_by="CarImage.sort_order.asc(), CarImage.id.asc()",
    )
    orders = db.relationship("Order", back_populates="car", cascade="all, delete-orphan")
    test_drives = db.relationship("TestDrive", back_populates="car", cascade="all, delete-orphan")
    favorited_by = db.relationship("User", secondary=favorites, back_populates="favorite_cars")

    def to_dict(self, usd_rate: float | None = None) -> dict:
        """Tuần tự hóa thông tin xe sang sang dictionary phục vụ REST API JSON."""
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "brand": self.brand.name if self.brand else None,
            "year": self.year,
            "price_vnd": self.price,
            "horsepower": self.horsepower,
            "mileage_km": self.mileage,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "body_type": self.body_type,
            "exterior_color": self.exterior_color,
            "seats": self.seats,
            "stock": self.stock,
            "is_featured": self.is_featured,
            "thumbnail_url": self.thumbnail_url,
            "model_3d_url": self.model_3d_url,
        }
        if usd_rate and usd_rate > 0:
            data["price_usd_estimated"] = round(self.price / usd_rate, 2)
        return data

    def __repr__(self) -> str:
        return f"<Car {self.name} ({self.year})>"


class CarImage(db.Model):
    """Model ảnh chi tiết trong bộ sưu tập của từng mẫu xe (1-n với Car)."""

    __tablename__ = "car_images"

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey("cars.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(160), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    car = db.relationship("Car", back_populates="images")

    def __repr__(self) -> str:
        return f"<CarImage {self.image_url}>"


class Order(db.Model):
    """Model đơn đặt mua / đặt cọc xe sang của khách hàng."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(28), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    car_id = db.Column(db.Integer, db.ForeignKey("cars.id", ondelete="CASCADE"), nullable=False, index=True)
    total_price = db.Column(db.BigInteger, nullable=False)
    deposit_amount = db.Column(db.BigInteger, nullable=False)
    payment_method = db.Column(db.String(30), nullable=False, default="bank_qr")
    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")
    status = db.Column(db.String(20), nullable=False, default="pending")
    customer_phone = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="orders")
    car = db.relationship("Car", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order {self.order_code} ({self.status})>"


class TestDrive(db.Model):
    """Model yêu cầu đặt lịch hẹn lái thử xe sang tại showroom."""

    __tablename__ = "test_drives"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    car_id = db.Column(db.Integer, db.ForeignKey("cars.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(30), nullable=False, default="09:00 - 11:00")
    phone = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    note = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="test_drives")
    car = db.relationship("Car", back_populates="test_drives")

    def __repr__(self) -> str:
        return f"<TestDrive #{self.id} car={self.car_id}>"
