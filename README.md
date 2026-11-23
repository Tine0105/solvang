# Solvang — Website Bán Xe Hơi Với Trình Xem 3D Tương Tác

Website bán xe hơi hiệu năng cao sử dụng **Flask + Python 3.11+**, **MySQL 8**, **Flask-SQLAlchemy**, **Flask-Migrate**, **Flask-Login**, **Flask-WTF**, **Jinja2**, và **Three.js** (`GLTFLoader` + `OrbitControls`).

## Tính năng chính

- **Trình xem 3D tương tác (Three.js):** xoay 360°, zoom, bật/tắt tự xoay, đổi màu sơn ngoại thất theo `car_colors`, phóng to toàn màn hình, ánh sáng studio + environment map, lazy-load khi vào viewport, fallback ảnh tĩnh nếu thiết bị không hỗ trợ WebGL. Hỗ trợ nạp file `.glb` từ `/static/models/` hoặc tự động dựng mô hình 3D placeholder khi chưa có file `.glb`.
- **Xác thực & phân quyền:** Đăng ký, đăng nhập (hỗ trợ *Ghi nhớ đăng nhập* và quay lại trang trước `next`), đăng xuất, cập nhật hồ sơ cá nhân, bảo vệ route Admin bằng `@admin_required`.
- **Khách hàng:** Tìm kiếm, lọc xe theo hãng / kiểu dáng / nhiên liệu / sắp xếp / phân trang; lưu xe yêu thích; đặt mua xe; đặt lịch lái thử.
- **Quản trị (Admin):** Dashboard thống kê, CRUD xe & hãng & màu sơn, upload ảnh và file `.glb` (kiểm tra định dạng & giới hạn dung lượng), quản lý trạng thái đơn hàng và lịch lái thử.

## Cài đặt và chạy dự án

### 1. Tạo môi trường ảo và cài thư viện

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Tạo database MySQL 8 (utf8mb4)

Đăng nhập vào MySQL và chạy câu lệnh:

```sql
CREATE DATABASE solvang_motors CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Cấu hình biến môi trường `.env`

Sao chép file mẫu `.env.example` thành `.env` và điền thông tin kết nối MySQL của bạn:

```bash
cp .env.example .env
```

Ví dụ nội dung `.env`:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=thay-bang-chuoi-bi-mat-dai-ngau-nhien
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=solvang_motors
DB_USER=root
DB_PASSWORD=mat_khau_mysql_cua_ban
```

### 4. Khởi tạo bảng và dữ liệu mẫu

```bash
flask db upgrade
python seed.py
```

### 5. Tải & tối ưu tài nguyên hình ảnh, video, HDRI và mô hình 3D

Dự án sử dụng `scripts/fetch_assets.py` để tự động tìm kiếm và tải tài nguyên có giấy phép mở hợp lệ (CC0, Public Domain, CC-BY, CC-BY-SA, Pexels/Unsplash License), sau đó tối ưu sang WebP/JPG/thumbnail qua `scripts/optimize_images.py` và lưu thông tin bản quyền vào `app/static/ASSETS.json` (hiển thị tại `/credits`).

#### Cách lấy API key miễn phí (tùy chọn)
1. **Pexels API** (`PEXELS_API_KEY` — ảnh + video): Đăng ký miễn phí tại `https://www.pexels.com/api/` và tạo API key.
2. **Unsplash API** (`UNSPLASH_ACCESS_KEY` — ảnh): Tạo ứng dụng tại `https://unsplash.com/developers` để lấy Access Key.
3. **Sketchfab Data API** (`SKETCHFAB_TOKEN` — model `.glb`): Tạo tài khoản tại `https://sketchfab.com/` → *Settings → Password & API* để lấy API Token.
4. **Không cần API key:** Script tự động dùng **Wikimedia Commons API**, **Openverse API** (ảnh) và **Poly Haven API** (HDRI 2K `.hdr` CC0) nếu thiếu key.

#### Thư mục lưu trữ tài nguyên
- Ảnh xe theo slug: `app/static/img/cars/<slug>/`
- Video nền hero: `app/static/video/`
- Môi trường ánh sáng HDRI (`.hdr`): `app/static/hdri/`
- Mô hình 3D tùy chỉnh (`.glb`): `app/static/models/<slug>.glb` (nếu chưa có `.glb`, trình xem tự dựng mô hình Three.js placeholder)

#### Lệnh thực thi
```bash
# 1. Cập nhật schema database (thêm bảng car_models, asset_fetch_log, cột metadata car_images)
flask db migrate
flask db upgrade

# 2. Xây dựng toàn bộ catalog 12 xe thật (model 3D .glb Sketchfab + bộ ảnh chụp thật Wikimedia/Pexels/Unsplash/Openverse)
python scripts/build_catalog.py --cars 12

#Các cờ hỗ trợ khác:
# python scripts/build_catalog.py --dry-run
# python scripts/build_catalog.py --only-models
# python scripts/build_catalog.py --only-images
# python scripts/build_catalog.py --resume
# python scripts/build_catalog.py --car porsche-911-carrera

# 3. Kiểm tra toàn bộ DB & file trên đĩa (mỗi xe có .glb hợp lệ + >= 5 ảnh + đủ tác giả/license)
python scripts/build_catalog.py --verify

# 4. Kiểm tra chi tiết mesh/material/bounding-box của một file .glb bất kỳ
python scripts/inspect_glb.py app/static/models/porsche-911-carrera.glb

# 5. (Tùy chọn) Tối ưu lại thư mục ảnh thủ công
python scripts/optimize_images.py app/static/img/cars
```

*(Biến `.env` `STORE_IMAGES_IN_DB=false` mặc định lưu file trên đĩa; nếu bật `true`, bản thumbnail WebP tối ưu `<= 640px` sẽ được lưu thêm vào `car_images.image_blob` và phục vụ qua `/media/image/<id>` kèm `Cache-Control` + `ETag`)*

### 6. Chạy ứng dụng

```bash
python seed.py   # Tạo tài khoản Admin & User mẫu (nếu DB chưa có user)
flask run
```

Truy cập: `http://127.0.0.1:5000` (trang bản quyền tài nguyên: `http://127.0.0.1:5000/credits`).

### Tài khoản mẫu sau khi chạy `seed.py`

- **Admin:** `admin@example.com` / `Admin@123456`
- **Khách hàng 1:** `minh.tran@example.com` / `User@123456`
- **Khách hàng 2:** `linh.nguyen@example.com` / `User@123456`
