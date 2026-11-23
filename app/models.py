from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    favorites = db.relationship('Favorite', back_populates='user', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='user', cascade='all, delete-orphan')
    test_drives = db.relationship('TestDriveRequest', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    def __repr__(self) -> str:
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class Brand(db.Model):
    __tablename__ = 'brands'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    logo = db.Column(db.String(255), nullable=True)

    cars = db.relationship('Car', back_populates='brand', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Brand {self.name}>'


class Car(db.Model):
    __tablename__ = 'cars'
    __table_args__ = (
        db.Index('ix_cars_slug', 'slug'),
        db.Index('ix_cars_price', 'price'),
        db.Index('ix_cars_brand_id', 'brand_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.BigInteger, nullable=False)
    mileage = db.Column(db.Integer, nullable=False, default=0)
    fuel_type = db.Column(db.String(40), nullable=False)
    transmission = db.Column(db.String(40), nullable=False)
    body_type = db.Column(db.String(40), nullable=False)
    seats = db.Column(db.Integer, nullable=False, default=4)
    description = db.Column(db.Text, nullable=False)
    model_url = db.Column(db.String(255), nullable=True)
    body_material_names = db.Column(db.JSON, nullable=True)
    model_scale = db.Column(db.Float, nullable=True, default=1.0)
    model_offset_y = db.Column(db.Float, nullable=True, default=0.0)
    hero_video_url = db.Column(db.String(255), nullable=True)
    thumbnail = db.Column(db.String(255), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=1)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    brand = db.relationship('Brand', back_populates='cars')
    colors = db.relationship('CarColor', back_populates='car', cascade='all, delete-orphan')
    images = db.relationship(
        'CarImage',
        back_populates='car',
        cascade='all, delete-orphan',
        order_by='CarImage.sort_order.asc(), CarImage.id.asc()',
    )
    models_3d = db.relationship(
        'CarModel',
        back_populates='car',
        cascade='all, delete-orphan',
        order_by='CarModel.id.desc()',
    )
    favorites = db.relationship('Favorite', back_populates='car', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='car', cascade='all, delete-orphan')
    test_drives = db.relationship('TestDriveRequest', back_populates='car', cascade='all, delete-orphan')

    @property
    def active_model(self):
        for m in self.models_3d:
            if m.is_active:
                return m
        return None

    @property
    def hero_image(self):
        active = [img for img in self.images if img.is_active]
        for img in active:
            if img.is_hero:
                return img
        return active[0] if active else None

    @property
    def active_images(self):
        return sorted(
            [img for img in self.images if img.is_active],
            key=lambda img: (0 if img.is_hero else 1, img.sort_order or 0, img.id or 0),
        )

    def __repr__(self) -> str:
        return f'<Car {self.name}>'


class CarColor(db.Model):
    __tablename__ = 'car_colors'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    color_name = db.Column(db.String(60), nullable=False)
    hex_code = db.Column(db.String(16), nullable=False)

    car = db.relationship('Car', back_populates='colors')
    orders = db.relationship('Order', back_populates='color')

    def __repr__(self) -> str:
        return f'<CarColor {self.color_name} {self.hex_code}>'


class CarModel(db.Model):
    __tablename__ = 'car_models'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_format = db.Column(db.String(20), nullable=False, default='glb')
    file_size = db.Column(db.BigInteger, nullable=False, default=0)
    sha256 = db.Column(db.String(64), nullable=False, index=True)
    poly_count = db.Column(db.Integer, nullable=False, default=0)
    source_name = db.Column(db.String(80), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(160), nullable=False)
    license = db.Column(db.String(80), nullable=False)
    license_url = db.Column(db.String(500), nullable=True)
    body_material_names = db.Column(db.JSON, nullable=True)
    scale = db.Column(db.Float, nullable=False, default=1.0)
    offset_y = db.Column(db.Float, nullable=False, default=0.0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    car = db.relationship('Car', back_populates='models_3d')

    def __repr__(self) -> str:
        return f'<CarModel {self.file_path} ({self.poly_count} tris)>'


class CarImage(db.Model):
    __tablename__ = 'car_images'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    license = db.Column(db.String(80), nullable=True)
    author = db.Column(db.String(160), nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    sha256 = db.Column(db.String(64), nullable=True, index=True)
    phash = db.Column(db.String(32), nullable=True, index=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    is_hero = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    shot_type = db.Column(db.String(30), nullable=False, default='exterior')
    caption = db.Column(db.String(255), nullable=True)
    match_level = db.Column(db.String(20), nullable=False, default='exact')
    source_name = db.Column(db.String(80), nullable=True)
    source_id = db.Column(db.String(160), nullable=True)
    image_blob = db.Column(db.LargeBinary(length=(2**32) - 1), nullable=True)
    fetched_at = db.Column(db.DateTime, nullable=True, default=_utcnow)

    car = db.relationship('Car', back_populates='images')

    def __repr__(self) -> str:
        return f'<CarImage {self.image_url}>'


class AssetFetchLog(db.Model):
    __tablename__ = 'asset_fetch_log'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    car_slug = db.Column(db.String(160), nullable=True, index=True)
    asset_type = db.Column(db.String(30), nullable=False)
    source_name = db.Column(db.String(80), nullable=False)
    query = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)


class Favorite(db.Model):
    __tablename__ = 'favorites'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'car_id', name='uq_favorites_user_car'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)

    user = db.relationship('User', back_populates='favorites')
    car = db.relationship('Car', back_populates='favorites')


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('car_colors.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship('User', back_populates='orders')
    car = db.relationship('Car', back_populates='orders')
    color = db.relationship('CarColor', back_populates='orders')


class TestDriveRequest(db.Model):
    __tablename__ = 'test_drive_requests'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    preferred_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship('User', back_populates='test_drives')
    car = db.relationship('Car', back_populates='test_drives')
