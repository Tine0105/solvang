"""Dịch vụ gửi email thông báo và đặt lại mật khẩu sử dụng Flask-Mail."""

from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail


def _safe_send(msg: Message) -> bool:
    """Thực hiện gửi email an toàn, ghi log nếu máy chủ SMTP không phản hồi."""
    try:
        mail.send(msg)
        current_app.logger.info("Đã xử lý gửi email tới %s: %s", msg.recipients, msg.subject)
        return True
    except Exception as exc:  # pragma: no cover - bảo vệ khi cấu hình SMTP lỗi
        current_app.logger.warning("Không thể gửi email SMTP (%s): %s", msg.subject, exc)
        return False


def send_welcome_email(user) -> bool:
    """Gửi email xác nhận đăng ký tài khoản thành công tới thành viên mới."""
    msg = Message(
        subject="[LuxAuto Showroom] Xác nhận đăng ký tài khoản thành công",
        recipients=[user.email],
    )
    msg.body = (
        f"Xin chào {user.full_name},\n\n"
        f"Chào mừng bạn đến với LuxAuto Showroom! Tài khoản ({user.email}) của bạn đã được kích hoạt.\n"
        "Giờ đây bạn có thể lưu các mẫu siêu xe yêu thích, đặt lịch hẹn lái thử và đặt cọc trực tuyến.\n\n"
        "Trân trọng,\nĐội ngũ LuxAuto Showroom"
    )
    msg.html = render_template("emails/welcome.html", user=user)
    return _safe_send(msg)


def send_password_reset_email(user, reset_url: str) -> bool:
    """Gửi email chứa liên kết token có thời hạn để đặt lại mật khẩu."""
    msg = Message(
        subject="[LuxAuto Showroom] Yêu cầu đặt lại mật khẩu",
        recipients=[user.email],
    )
    msg.body = (
        f"Xin chào {user.full_name},\n\n"
        "Hệ thống nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.\n"
        f"Vui lòng truy cập liên kết sau (hiệu lực trong 60 phút):\n{reset_url}\n\n"
        "Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.\n"
    )
    msg.html = render_template("emails/reset_password.html", user=user, reset_url=reset_url)
    return _safe_send(msg)


def send_order_confirmation_email(user, order) -> bool:
    """Gửi email xác nhận đơn đặt cọc xe sang."""
    msg = Message(
        subject=f"[LuxAuto Showroom] Xác nhận đơn đặt xe #{order.order_code}",
        recipients=[user.email],
    )
    deposit_fmt = f"{int(order.deposit_amount):,}".replace(",", ".")
    msg.body = (
        f"Xin chào {user.full_name},\n\n"
        f"LuxAuto Showroom đã tiếp nhận đơn đặt xe mã {order.order_code} "
        f"cho mẫu xe {order.car.name}.\n"
        f"Số tiền đặt cọc (5%): {deposit_fmt} VNĐ.\n"
        "Chuyên viên tư vấn sẽ liên hệ sớm qua số điện thoại của bạn.\n"
    )
    return _safe_send(msg)
