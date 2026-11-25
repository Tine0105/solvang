"""Định nghĩa các biểu mẫu Flask-WTF kèm bộ kiểm tra hợp lệ (Validators) và bảo vệ CSRF."""

from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, MultipleFileField
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)


class RegisterForm(FlaskForm):
    """Biểu mẫu đăng ký tài khoản khách hàng mới."""

    full_name = StringField(
        "Họ và tên",
        validators=[
            DataRequired(message="Vui lòng nhập họ và tên."),
            Length(min=2, max=120, message="Họ tên phải từ 2 đến 120 ký tự."),
        ],
    )
    email = StringField(
        "Địa chỉ Email",
        validators=[
            DataRequired(message="Vui lòng nhập địa chỉ email."),
            Email(message="Định dạng email không hợp lệ."),
            Length(max=180),
        ],
    )
    phone = StringField(
        "Số điện thoại",
        validators=[
            Optional(),
            Regexp(r"^[0-9+\-\s]{8,20}$", message="Số điện thoại không hợp lệ."),
        ],
    )
    password = PasswordField(
        "Mật khẩu",
        validators=[
            DataRequired(message="Vui lòng nhập mật khẩu."),
            Length(min=6, max=128, message="Mật khẩu phải có ít nhất 6 ký tự."),
        ],
    )
    confirm_password = PasswordField(
        "Xác nhận mật khẩu",
        validators=[
            DataRequired(message="Vui lòng nhập lại mật khẩu."),
            EqualTo("password", message="Mật khẩu xác nhận không trùng khớp."),
        ],
    )
    submit = SubmitField("Đăng ký tài khoản")


class LoginForm(FlaskForm):
    """Biểu mẫu đăng nhập hệ thống."""

    email = StringField(
        "Email đăng nhập",
        validators=[
            DataRequired(message="Vui lòng nhập email."),
            Email(message="Email không đúng định dạng."),
        ],
    )
    password = PasswordField(
        "Mật khẩu",
        validators=[DataRequired(message="Vui lòng nhập mật khẩu.")],
    )
    remember_me = BooleanField("Ghi nhớ đăng nhập")
    submit = SubmitField("Đăng nhập")


class ProfileForm(FlaskForm):
    """Biểu mẫu cập nhật thông tin hồ sơ cá nhân."""

    full_name = StringField(
        "Họ và tên",
        validators=[DataRequired(message="Vui lòng nhập họ tên."), Length(min=2, max=120)],
    )
    phone = StringField(
        "Số điện thoại",
        validators=[Optional(), Length(max=30)],
    )
    submit = SubmitField("Lưu thay đổi")


class ForgotPasswordForm(FlaskForm):
    """Biểu mẫu yêu cầu gửi email đặt lại mật khẩu."""

    email = StringField(
        "Email tài khoản đã đăng ký",
        validators=[
            DataRequired(message="Vui lòng nhập địa chỉ email."),
            Email(message="Email không hợp lệ."),
        ],
    )
    submit = SubmitField("Gửi liên kết đặt lại mật khẩu")


class ResetPasswordForm(FlaskForm):
    """Biểu mẫu đặt mật khẩu mới thông qua token xác thực."""

    password = PasswordField(
        "Mật khẩu mới",
        validators=[
            DataRequired(message="Vui lòng nhập mật khẩu mới."),
            Length(min=6, max=128, message="Mật khẩu tối thiểu 6 ký tự."),
        ],
    )
    confirm_password = PasswordField(
        "Xác nhận mật khẩu mới",
        validators=[
            DataRequired(message="Vui lòng xác nhận mật khẩu."),
            EqualTo("password", message="Mật khẩu xác nhận không trùng khớp."),
        ],
    )
    submit = SubmitField("Cập nhật mật khẩu")


class CarSearchForm(FlaskForm):
    """Biểu mẫu tìm kiếm và lọc danh mục xe sang (sử dụng phương thức GET)."""

    class Meta:
        csrf = False

    q = StringField("Từ khóa", validators=[Optional(), Length(max=100)])
    brand_id = SelectField("Thương hiệu", coerce=int, default=0, validators=[Optional()])
    body_type = SelectField(
        "Kiểu dáng",
        choices=[
            ("", "Tất cả kiểu dáng"),
            ("Coupe", "Coupé thể thao"),
            ("Sedan", "Sedan hạng sang"),
            ("SUV", "SUV hạng sang"),
            ("Roadster", "Roadster mui trần"),
        ],
        default="",
        validators=[Optional()],
    )
    fuel_type = SelectField(
        "Động cơ / Nhiên liệu",
        choices=[
            ("", "Tất cả nhiên liệu"),
            ("Xăng", "Xăng tăng áp / Hút khí tự nhiên"),
            ("Hybrid", "Hybrid hiệu năng cao"),
            ("Điện", "Thuần điện (EV)"),
        ],
        default="",
        validators=[Optional()],
    )
    price_range = SelectField(
        "Mức giá",
        choices=[
            ("", "Mọi mức giá"),
            ("under_5b", "Dưới 5 tỷ VNĐ"),
            ("5b_to_10b", "Từ 5 – 10 tỷ VNĐ"),
            ("over_10b", "Trên 10 tỷ VNĐ"),
        ],
        default="",
        validators=[Optional()],
    )
    sort = SelectField(
        "Sắp xếp",
        choices=[
            ("newest", "Mới cập nhật"),
            ("price_asc", "Giá tăng dần"),
            ("price_desc", "Giá giảm dần"),
            ("power_desc", "Công suất cao nhất"),
        ],
        default="newest",
        validators=[Optional()],
    )
    submit = SubmitField("Tìm kiếm")


class BrandForm(FlaskForm):
    """Biểu mẫu thêm mới thương hiệu xe sang dành cho Quản trị viên."""

    name = StringField(
        "Tên thương hiệu",
        validators=[DataRequired(message="Vui lòng nhập tên hãng xe."), Length(min=2, max=80)],
    )
    country = StringField(
        "Quốc gia xuất xứ",
        validators=[DataRequired(message="Vui lòng nhập quốc gia."), Length(min=2, max=60)],
    )
    description = StringField("Mô tả ngắn", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Lưu thương hiệu")


class CarForm(FlaskForm):
    """Biểu mẫu Thêm / Cập nhật thông tin xe sang (CRUD chính)."""

    brand_id = SelectField(
        "Thương hiệu xe",
        coerce=int,
        validators=[DataRequired(message="Vui lòng chọn thương hiệu.")],
    )
    name = StringField(
        "Tên mẫu xe sang",
        validators=[DataRequired(message="Vui lòng nhập tên xe."), Length(min=2, max=140)],
    )
    slug = StringField(
        "Đường dẫn tĩnh (Slug)",
        validators=[
            DataRequired(message="Vui lòng nhập slug URL."),
            Length(min=2, max=160),
            Regexp(r"^[a-z0-9-]+$", message="Slug chỉ gồm chữ thường, chữ số và dấu gạch ngang (-)."),
        ],
    )
    year = IntegerField(
        "Năm sản xuất",
        validators=[
            DataRequired(message="Vui lòng nhập năm sản xuất."),
            NumberRange(min=2000, max=2030, message="Năm sản xuất phải nằm trong khoảng 2000–2030."),
        ],
        default=2026,
    )
    price = IntegerField(
        "Giá niêm yết (VNĐ)",
        validators=[
            DataRequired(message="Vui lòng nhập giá bán."),
            NumberRange(min=500_000_000, message="Giá xe sang tối thiểu từ 500.000.000 VNĐ."),
        ],
    )
    horsepower = IntegerField(
        "Công suất cực đại (HP)",
        validators=[
            DataRequired(message="Vui lòng nhập công suất."),
            NumberRange(min=150, max=2500, message="Công suất từ 150 đến 2500 HP."),
        ],
        default=520,
    )
    mileage = IntegerField(
        "Số km đã lăn bánh (ODO)",
        validators=[NumberRange(min=0, max=500_000, message="Số km không được âm.")],
        default=0,
    )
    fuel_type = SelectField(
        "Hệ truyền động / Nhiên liệu",
        choices=[
            ("Xăng", "Xăng tăng áp / Hút khí tự nhiên"),
            ("Hybrid", "Plug-in Hybrid"),
            ("Điện", "Thuần điện (EV)"),
        ],
        validators=[DataRequired()],
    )
    transmission = SelectField(
        "Hộp số",
        choices=[
            ("Tự động 8 cấp ZF", "Tự động 8 cấp ZF"),
            ("Ly hợp kép PDK 8 cấp", "Ly hợp kép PDK / DCT"),
            ("Tự động 9G-TRONIC", "Tự động 9G-TRONIC"),
            ("Tự động 1 cấp (EV)", "Tự động 1 cấp (EV)"),
            ("Số sàn 6 cấp", "Số sàn 6 cấp thể thao"),
        ],
        validators=[DataRequired()],
    )
    body_type = SelectField(
        "Kiểu dáng thân xe",
        choices=[
            ("Coupe", "Coupé 2 cửa"),
            ("Sedan", "Executive Sedan"),
            ("SUV", "Luxury SUV"),
            ("Roadster", "Roadster mui trần"),
        ],
        validators=[DataRequired()],
    )
    exterior_color = StringField(
        "Màu sơn ngoại thất",
        validators=[DataRequired(message="Vui lòng nhập màu ngoại thất."), Length(max=60)],
        default="Đen Obsidian",
    )
    seats = IntegerField(
        "Số chỗ ngồi",
        validators=[DataRequired(), NumberRange(min=2, max=7)],
        default=4,
    )
    stock = IntegerField(
        "Số lượng xe sẵn kho",
        validators=[NumberRange(min=0, max=100)],
        default=2,
    )
    is_featured = BooleanField("Đánh dấu mẫu xe tiêu điểm tại Trang chủ")
    description = TextAreaField(
        "Mô tả chi tiết & Trang bị",
        validators=[
            DataRequired(message="Vui lòng nhập mô tả mẫu xe."),
            Length(min=15, max=5000, message="Mô tả cần từ 15 đến 5000 ký tự."),
        ],
    )
    thumbnail_file = FileField(
        "Ảnh đại diện mới (JPG, PNG, WEBP)",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Chỉ hỗ trợ định dạng ảnh JPG, PNG hoặc WEBP."),
        ],
    )
    gallery_files = MultipleFileField(
        "Bộ sưu tập ảnh chi tiết (tùy chọn nhiều file)",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Chỉ hỗ trợ định dạng ảnh JPG, PNG hoặc WEBP."),
        ],
    )
    model_file = FileField(
        "Mô hình 3D tương tác (.glb)",
        validators=[
            Optional(),
            FileAllowed(["glb"], "Chỉ hỗ trợ định dạng mô hình 3D nhị phân (.glb)."),
        ],
    )
    submit = SubmitField("Lưu thông tin xe")


class OrderForm(FlaskForm):
    """Biểu mẫu đặt cọc mua xe sang trực tuyến (mức cọc tiêu chuẩn 5%)."""

    customer_phone = StringField(
        "Số điện thoại liên hệ",
        validators=[
            DataRequired(message="Vui lòng nhập số điện thoại xác nhận hợp đồng."),
            Regexp(r"^[0-9+\-\s]{8,20}$", message="Số điện thoại không hợp lệ."),
        ],
    )
    payment_method = SelectField(
        "Phương thức đặt cọc",
        choices=[
            ("bank_qr", "Chuyển khoản nhanh qua mã QR Ngân hàng (Demo)"),
            ("showroom", "Thanh toán trực tiếp tại Showroom Quận 1"),
        ],
        validators=[DataRequired()],
    )
    note = TextAreaField("Yêu cầu cá nhân hóa / Ghi chú giao xe", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Tạo đơn đặt cọc (5% giá trị xe)")


class TestDriveForm(FlaskForm):
    """Biểu mẫu đăng ký lịch hẹn lái thử xe sang."""

    preferred_date = DateField(
        "Ngày hẹn lái thử",
        validators=[DataRequired(message="Vui lòng chọn ngày lái thử.")],
    )
    time_slot = SelectField(
        "Khung giờ",
        choices=[
            ("09:00 - 11:00", "Sáng (09:00 - 11:00)"),
            ("14:00 - 16:00", "Chiều (14:00 - 16:00)"),
            ("16:30 - 18:00", "Chiều muộn (16:30 - 18:00)"),
        ],
        validators=[DataRequired()],
    )
    phone = StringField(
        "Số điện thoại liên hệ",
        validators=[
            DataRequired(message="Vui lòng nhập số điện thoại."),
            Regexp(r"^[0-9+\-\s]{8,20}$", message="Số điện thoại không hợp lệ."),
        ],
    )
    note = StringField("Ghi chú thêm", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Đặt lịch lái thử")

    def validate_preferred_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Ngày hẹn lái thử phải tính từ hôm nay trở đi.")


class OrderStatusForm(FlaskForm):
    """Biểu mẫu cập nhật trạng thái đơn hàng trong trang Quản trị."""

    status = SelectField(
        "Trạng thái đơn",
        choices=[
            ("pending", "Chờ xác nhận"),
            ("confirmed", "Đã xác nhận"),
            ("completed", "Đã bàn giao xe"),
            ("cancelled", "Đã hủy"),
        ],
        validators=[DataRequired()],
    )
    payment_status = SelectField(
        "Thanh toán cọc",
        choices=[
            ("unpaid", "Chưa thanh toán cọc"),
            ("paid", "Đã nhận tiền cọc"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Cập nhật")
