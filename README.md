# LuxAuto Showroom — Website Bán Xe Sang Với Flask

Đồ án môn học **Lập trình Python nâng cao (`71ITSE31003`)** – Khoa Công nghệ Thông tin, Trường Đại học Văn Lang.  
- **Sinh viên thực hiện:** Nguyễn Minh Tiến (`2374802011070`) – Nhóm: Tiến  
- **Giảng viên hướng dẫn:** ThS. Nguyễn Thị Mỹ Linh (`11/2026`)

---

## 1. Cấu trúc thư mục dự án

```text
WebLab/
├── src/                                  # Mã nguồn chính của ứng dụng Flask
│   ├── app/
│   │   ├── __init__.py                   # Application Factory create_app() & Jinja2 filters
│   │   ├── extensions.py                 # Khởi tạo db, migrate, login_manager, csrf, mail
│   │   ├── models.py                     # 6 Model SQLAlchemy & bảng trung gian favorites (n-n)
│   │   ├── forms.py                      # 11 lớp FlaskForm & Validators (Flask-WTF + CSRF)
│   │   ├── decorators.py                 # Kiểm soát phân quyền @admin_required (HTTP 403)
│   │   ├── services/                     # email_service.py, exchange_service.py (urllib), image_service.py
│   │   ├── blueprints/                   # 4 Blueprints: main/, auth/, admin/, api/
│   │   ├── templates/                    # Giao diện kế thừa base.html (Bootstrap 5.3 Responsive)
│   │   └── static/                       # CSS, JS biểu đồ & bộ ảnh xe sang mẫu
│   ├── migrations/                       # Quản lý phiên bản CSDL (Flask-Migrate)
│   ├── tests/                            # 14 ca kiểm thử tự động pytest
│   ├── config.py                         # Cấu hình Development / Testing / Production qua biến môi trường
│   ├── run.py                            # Entrypoint khởi chạy Flask trong src/
│   ├── seed.py                           # Script khởi tạo dữ liệu mẫu & tài khoản Demo
│   ├── .flaskenv                         # Cấu hình mặc định cho lệnh `flask run`
│   ├── .env.example                      # Mẫu biến môi trường (không chứa mật khẩu/API key thật)
│   └── requirements.txt                  # Danh sách gói thư viện Python
├── docs/
│   ├── Mau_Bao_Cao_DoAn_LapTrinhPythonNangCao.docx   # File mẫu gốc của học phần
│   ├── diagrams/                         # Sơ đồ Use Case (Hình 2.1), ERD (Hình 2.2), Luồng màn hình (Hình 2.3)
│   └── screenshots/                      # 6 ảnh chụp màn hình thực tế từ trình duyệt
├── output/
│   ├── BaoCao_DoAn_Tien.docx             # Báo cáo hoàn chỉnh (.docx)
│   └── BaoCao_DoAn_Tien.pdf              # Bản xuất PDF chuẩn A4 đã cập nhật tự động Mục lục
├── run.py                                # Entrypoint gốc hỗ trợ chạy trực tiếp từ thư mục WebLab/
├── seed.py                               # Entrypoint gốc gọi tạo dữ liệu mẫu
├── requirements.txt                      # Danh sách gói thư viện cài đặt nhanh từ thư mục gốc
├── pytest.ini                            # Cấu hình chạy pytest trực tiếp từ thư mục gốc
└── README.md                             # Tài liệu hướng dẫn cài đặt & vận hành
```

---

## 2. Tính năng nổi bật

1. **Xác thực & Phân quyền 2 vai trò (`Flask-Login` + `Werkzeug Security`):**
   - Đăng ký, đăng nhập, ghi nhớ phiên, đăng xuất, cập nhật hồ sơ cá nhân.
   - Phân quyền `admin` và `user` qua decorator `@admin_required` (chặn truy cập trái phép bằng HTTP `403`).
2. **Quản lý danh mục CRUD, Tìm kiếm đa tiêu chí & Phân trang (`Flask-SQLAlchemy` + `Flask-WTF`):**
   - Thêm, sửa, xóa, hiển thị mẫu xe sang (`Car`) và thương hiệu (`Brand`).
   - Tìm kiếm từ khóa kết hợp lọc theo hãng, kiểu dáng, nhiên liệu, khoảng giá, sắp xếp và phân trang với `query.paginate()`.
   - Quản lý danh sách xe yêu thích theo quan hệ nhiều-nhiều (`n–n`).
3. **Gửi Email tự động (`Flask-Mail` + `itsdangerous`):**
   - Gửi email chào mừng xác nhận đăng ký tài khoản mới và email khôi phục mật khẩu qua liên kết token ký số có thời hạn (60 phút).
   - Cấu hình SMTP qua biến môi trường; mặc định bật `MAIL_SUPPRESS_SEND=true` an toàn khi chạy demo ngoại tuyến.
4. **Lập trình mạng & RESTful JSON API (CLO3):**
   - Tích hợp `urllib.request` đọc tỷ giá ngoại tệ trực tuyến `USD/EUR ↔ VND` từ ExchangeRate-API (ưu tiên mở miễn phí, hỗ trợ `EXCHANGE_API_KEY` trong `.env`, có `timeout=5s`, bộ nhớ đệm TTL và fallback khi mất mạng).
   - Cung cấp các REST API trả JSON: `GET /api/cars`, `GET /api/cars/<slug>`, `GET /api/exchange-rate`.
5. **Chức năng mở rộng:**
   - **Trình xem mô hình 3D tương tác 360° (`Three.js` / `WebGL` / `glTF .glb`):** Xoay 360°, thu phóng, ánh sáng môi trường HDRI Studio và đổi màu sơn ngoại thất trực tiếp trên mô hình 3D tại trang chi tiết xe.
   - **Upload tệp 3D `.glb` & tối ưu ảnh xe sang (`Pillow`):** Kiểm tra magic bytes `b'glTF'` cho mô hình 3D và chuyển đổi ảnh sang chuẩn `.webp`.
   - **Đặt cọc 5% qua VietQR Demo & Thống kê biểu đồ (`Chart.js`):** Quy trình đặt cọc xe trực tuyến và bảng điều khiển biểu đồ quản trị theo thời gian thực.

---

## 3. Hướng dẫn cài đặt và khởi chạy

Bạn có thể mở terminal ngay tại thư mục **`WebLab/`** (hoặc trong **`WebLab/src/`**) và thực hiện tuần tự:

```powershell
# 1. Tạo và kích hoạt môi trường ảo (Virtual Environment)
python -m venv .venv
.venv\Scripts\Activate.ps1
# (Trên macOS / Linux dùng: source .venv/bin/activate)

# 2. Cài đặt các gói thư viện phụ thuộc
pip install -r requirements.txt

# 3. Khởi tạo cơ sở dữ liệu SQLite và nạp dữ liệu mẫu
python seed.py

# 4. Khởi chạy máy chủ phát triển Flask
flask run
```

Sau khi chạy lệnh `flask run`, mở trình duyệt truy cập: **http://127.0.0.1:5000**

---

## 4. Tài khoản Demo kiểm thử

Sau khi chạy `python seed.py`, sử dụng các tài khoản sau để kiểm tra phân quyền:

| Vai trò | Email đăng nhập | Mật khẩu | Quyền hạn chính |
| :--- | :--- | :--- | :--- |
| **Quản trị viên (Admin)** | `admin@luxauto.vn` | `Admin@123` | Toàn quyền Dashboard biểu đồ (`/admin/`), CRUD xe/hãng, upload ảnh, duyệt đơn đặt cọc & lịch lái thử |
| **Khách hàng (User)** | `user@luxauto.vn` | `User@123` | Tra cứu, lưu xe yêu thích, đặt cọc 5% qua QR Demo, đặt lịch lái thử, quản lý hồ sơ |

---

## 5. Chạy bộ kiểm thử tự động (`pytest`)

Từ thư mục gốc `WebLab/` (hoặc `WebLab/src/`), chạy lệnh:

```powershell
pytest -v
```

Bộ kiểm thử gồm **14 kịch bản** kiểm tra toàn diện: Trang chủ, Đăng ký + Flask-Mail, Chống trùng email, Đăng nhập/Đăng xuất, Phân quyền RBAC 403, Dashboard Admin, CRUD Xe + Upload ảnh, Tìm kiếm, Phân trang `paginate`, Quên/Đặt lại mật khẩu bằng token, Yêu thích `n–n`, Đặt cọc QR Demo, REST API JSON và xử lý lỗi mạng `urllib`.
