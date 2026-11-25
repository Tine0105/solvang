"""Điểm khởi chạy ứng dụng Flask LuxAuto Showroom."""

import os
import sys

# Đảm bảo thư mục src/ luôn nằm đầu sys.path dù gọi từ thư mục gốc hay từ src/
SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app import create_app  # noqa: E402

env_name = os.environ.get("FLASK_CONFIG", "default")
app = create_app(env_name)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
