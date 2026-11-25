"""Dịch vụ kiểm tra định dạng, đổi tên an toàn và tối ưu kích thước ảnh xe upload."""

import os
import uuid
from PIL import Image, UnidentifiedImageError
from flask import current_app
from werkzeug.utils import secure_filename


def save_car_image(file_storage) -> str | None:
    """Lưu và tối ưu ảnh upload về định dạng WEBP chuẩn; trả về URL tĩnh hoặc None."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None

    safe_name = secure_filename(file_storage.filename)
    if "." not in safe_name:
        return None

    ext = safe_name.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})
    if ext not in allowed:
        return None

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    stem = safe_name.rsplit(".", 1)[0][:40] or "car"
    out_filename = f"{uuid.uuid4().hex[:10]}_{stem}.webp"
    out_path = os.path.join(upload_dir, out_filename)

    try:
        with Image.open(file_storage.stream) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            if img.width > 1600:
                new_height = int(img.height * (1600 / img.width))
                img = img.resize((1600, new_height), Image.Resampling.LANCZOS)
            img.save(out_path, format="WEBP", quality=86)
        return f"/static/uploads/cars/{out_filename}"
    except (UnidentifiedImageError, OSError):
        return None


def save_car_model_glb(file_storage) -> str | None:
    """Kiểm tra magic bytes glTF 2.0 nhị phân và lưu tệp mô hình 3D (.glb) an toàn."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None

    safe_name = secure_filename(file_storage.filename)
    if "." not in safe_name or safe_name.rsplit(".", 1)[1].lower() != "glb":
        return None

    header = file_storage.stream.read(4)
    file_storage.stream.seek(0)
    if header != b"glTF":
        return None

    model_dir = current_app.config["MODEL_UPLOAD_FOLDER"]
    os.makedirs(model_dir, exist_ok=True)
    stem = safe_name.rsplit(".", 1)[0][:40] or "model3d"
    out_filename = f"{uuid.uuid4().hex[:8]}_{stem}.glb"
    out_path = os.path.join(model_dir, out_filename)
    file_storage.save(out_path)
    return f"/static/models/{out_filename}"
