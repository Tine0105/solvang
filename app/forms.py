from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    IntegerField, TextAreaField, SelectField, DateField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Optional, NumberRange, Regexp, ValidationError
)


class RegisterForm(FlaskForm):
    full_name = StringField('Họ và tên', validators=[DataRequired('Vui lòng nhập họ tên.'), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired('Vui lòng nhập email.'), Email('Email không hợp lệ.'), Length(max=180)])
    phone = StringField('Số điện thoại', validators=[Optional(), Length(max=30)])
    password = PasswordField('Mật khẩu', validators=[DataRequired('Vui lòng nhập mật khẩu.'), Length(min=6, max=128, message='Mật khẩu tối thiểu 6 ký tự.')])
    confirm_password = PasswordField(
        'Xác nhận mật khẩu',
        validators=[DataRequired('Vui lòng xác nhận mật khẩu.'), EqualTo('password', message='Mật khẩu xác nhận không khớp.')]
    )
    submit = SubmitField('Tạo tài khoản')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired('Vui lòng nhập email.'), Email('Email không hợp lệ.')])
    password = PasswordField('Mật khẩu', validators=[DataRequired('Vui lòng nhập mật khẩu.')])
    remember_me = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')


class ProfileForm(FlaskForm):
    full_name = StringField('Họ và tên', validators=[DataRequired('Vui lòng nhập họ tên.'), Length(min=2, max=120)])
    phone = StringField('Số điện thoại', validators=[Optional(), Length(max=30)])
    submit = SubmitField('Cập nhật hồ sơ')


class OrderForm(FlaskForm):
    color_id = SelectField('Màu sơn ngoại thất', coerce=int, validators=[DataRequired('Vui lòng chọn màu sơn.')])
    note = TextAreaField('Ghi chú đặt xe', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Xác nhận đặt mua')


class TestDriveForm(FlaskForm):
    preferred_date = DateField('Ngày lái thử mong muốn', validators=[DataRequired('Vui lòng chọn ngày.')])
    submit = SubmitField('Đặt lịch lái thử')

    def validate_preferred_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError('Ngày lái thử phải từ hôm nay trở đi.')


class BrandForm(FlaskForm):
    name = StringField('Tên hãng xe', validators=[DataRequired('Vui lòng nhập tên hãng.'), Length(min=2, max=80)])
    logo_file = FileField('Logo hãng (PNG/JPG/WEBP)', validators=[Optional(), FileAllowed(['png', 'jpg', 'jpeg', 'webp'], 'Chỉ chấp nhận ảnh PNG, JPG, WEBP.')])
    submit = SubmitField('Lưu hãng xe')


class CarForm(FlaskForm):
    brand_id = SelectField('Hãng xe', coerce=int, validators=[DataRequired('Vui lòng chọn hãng xe.')])
    name = StringField('Tên mẫu xe', validators=[DataRequired('Vui lòng nhập tên xe.'), Length(min=2, max=140)])
    slug = StringField('Slug URL', validators=[DataRequired('Vui lòng nhập slug.'), Length(min=2, max=160), Regexp(r'^[a-z0-9-]+$', message='Slug chỉ gồm chữ thường, số và dấu gạch ngang.')])
    year = IntegerField('Năm sản xuất', validators=[DataRequired(), NumberRange(min=1990, max=2030)])
    price = IntegerField('Giá niêm yết (VNĐ)', validators=[DataRequired(), NumberRange(min=1000000)])
    mileage = IntegerField('Số km đã đi', validators=[NumberRange(min=0)], default=0)
    fuel_type = SelectField('Nhiên liệu', choices=[
        ('Điện', 'Điện (EV)'),
        ('Hybrid', 'Hybrid'),
        ('Xăng', 'Xăng'),
        ('Diesel', 'Diesel'),
    ], validators=[DataRequired()])
    transmission = SelectField('Hộp số', choices=[
        ('Tự động 1 cấp', 'Tự động 1 cấp (EV)'),
        ('Tự động 8 cấp', 'Tự động 8 cấp'),
        ('Ly hợp kép 7 cấp', 'Ly hợp kép 7 cấp'),
        ('Số sàn 6 cấp', 'Số sàn 6 cấp'),
    ], validators=[DataRequired()])
    body_type = SelectField('Kiểu dáng', choices=[
        ('Coupe', 'Coupé'),
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Roadster', 'Roadster'),
        ('Touring', 'Touring'),
    ], validators=[DataRequired()])
    seats = IntegerField('Số chỗ ngồi', validators=[DataRequired(), NumberRange(min=1, max=9)], default=4)
    stock = IntegerField('Tồn kho', validators=[NumberRange(min=0, max=999)], default=1)
    is_featured = BooleanField('Hiển thị nổi bật')
    description = TextAreaField('Mô tả chi tiết', validators=[DataRequired(), Length(min=10, max=5000)])
    thumbnail_file = FileField('Ảnh đại diện (PNG/JPG/WEBP)', validators=[Optional(), FileAllowed(['png', 'jpg', 'jpeg', 'webp'], 'Chỉ chấp nhận ảnh PNG, JPG, WEBP.')])
    gallery_files = FileField('Ảnh bộ sưu tập', validators=[Optional(), FileAllowed(['png', 'jpg', 'jpeg', 'webp'], 'Chỉ chấp nhận ảnh PNG, JPG, WEBP.')])
    model_file = FileField('Mô hình 3D (.glb)', validators=[Optional(), FileAllowed(['glb'], 'Chỉ chấp nhận file 3D định dạng .glb.')])
    submit = SubmitField('Lưu thông tin xe')


class CarColorForm(FlaskForm):
    color_name = StringField('Tên màu sơn', validators=[DataRequired(), Length(min=2, max=60)])
    hex_code = StringField('Mã màu HEX', validators=[DataRequired(), Regexp(r'^#[0-9A-Fa-f]{6}$', message='Mã màu phải có dạng #RRGGBB.')])
    submit = SubmitField('Thêm màu')


class OrderStatusForm(FlaskForm):
    status = SelectField('Trạng thái', choices=[
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('cancelled', 'Đã hủy'),
    ], validators=[DataRequired()])
    submit = SubmitField('Cập nhật')


class TestDriveStatusForm(FlaskForm):
    status = SelectField('Trạng thái', choices=[
        ('pending', 'Chờ duyệt'),
        ('confirmed', 'Đã xác nhận'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], validators=[DataRequired()])
    submit = SubmitField('Cập nhật')
