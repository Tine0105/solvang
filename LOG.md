# Dev Log — Solvang WebLab

## 2026-11-22 — Kiểm tra & sửa lỗi ban đầu

### 1. Kiểm tra hệ thống
- **Cú pháp & import Python:** Chạy `compileall` trên `app/`, `config.py`, `run.py`, `seed.py` và import ứng dụng — không có lỗi cú pháp.
- **Kiểm thử route & template (`TestingConfig`, SQLite in-memory):**
  - Kiểm tra các route GET công khai (`/`, `/cars/`, `/cars/<slug>`, `/auth/login`, `/auth/register`, `404`), route user (`/auth/profile`, `/orders/*`, `/admin/` trả `403`), và route admin (`/admin/*`) — đều trả về mã HTTP hợp lệ.
  - Kiểm tra các route POST chính (đăng ký, cập nhật hồ sơ, yêu thích, đặt mua, đặt lịch lái thử, thêm hãng, thêm xe).
  - Rà soát toàn bộ `url_for(...)` và đường dẫn `/static/...` trong `app/templates/` — không có endpoint sai hay file tĩnh bị thiếu.

### 2. Các lỗi đã phát hiện & khắc phục
- **Khởi tạo Flask-Migrate (`migrations/`):**
  - Chạy `flask db init`, tạo migration đầu tiên `migrations/versions/7870ef806351_initial_schema.py` cho các bảng `brands`, `users`, `cars`, `car_colors`, `car_images`, `favorites`, `test_drive_requests`, `orders`.
  - Chạy `flask db upgrade` lên MySQL thành công (`7870ef806351 (head)`).
- **Lỗi 404 ảnh fallback khi tạo xe mới:**
  - Sửa `app/blueprints/admin/routes.py`: đổi đường dẫn fallback từ `/static/img/cars/aurelia-gt.svg` (không tồn tại) sang `/static/img/cars/aurelia-gt-r9.svg`.
- **Lộ mật khẩu trong file mẫu:**
  - Sửa `.env.example`: thay `DB_PASSWORD=monatinguyen1@` thành `DB_PASSWORD=your_mysql_password`.
- **Thiếu hiển thị lỗi validation trên form xe Admin:**
  - Sửa `app/templates/admin/car_form.html`: bổ sung hiển thị `field__error` cho các trường `brand_id`, `year`, `seats`, `stock`, `mileage`, `fuel_type`, `transmission`, `body_type`.

### 3. Kiểm tra sau khi sửa
- Test lại với `TestingConfig`: tạo xe không upload thumbnail trả về `302` với ảnh `/static/img/cars/aurelia-gt-r9.svg` tồn tại trên đĩa; submit thiếu `mileage`/`stock` trả về `200` và hiển thị `field__error`.
- `flask db current` xác nhận database đang ở revision `7870ef806351 (head)`.

### Trạng thái hiện tại
- **Đã xong:** Sửa lỗi mã nguồn, khởi tạo & nâng cấp schema MySQL.
- **Chưa chạy:** `python seed.py` và `flask run`.

## 2026-11-22 (Phần 2) — Nâng cấp giao diện điện ảnh & hệ thống tải tài nguyên mở

### 1. Nâng cấp Frontend (Cinematic Supercar Style + `design-taste-frontend`)
- **Typography & Theme:** Dùng `Chakra Petch` (in hoa góc cạnh) + `Plus Jakarta Sans`, nền `#07080a` / `#0b0d10`, màu nhấn `#e07a2b`.
- **Chuyển động & Tương tác (`app/static/js/cinema.js`, `app/static/css/app.css`):**
  - Lenis smooth scroll đồng bộ với GSAP + ScrollTrigger.
  - Preloader kèm phần trăm tải, page transition curtain (`clip-path`), custom cursor trên desktop (`pointer: fine`), nút `.btn--magnetic`, và menu toàn màn hình dạng overlay có stagger.
  - Hero `100svh` toàn màn hình (hỗ trợ video nền loop hoặc ảnh 4K + gradient tối + split-line reveal), section telemetry count-up (`0–100 km/h`, `HP`, `km/h`), parallax nhẹ.
  - Trang chi tiết xe (`app/templates/cars/detail.html`): bố cục scrollytelling gắn đường đi camera 3D (`setCameraProgress`) với ScrollTrigger `scrub`.
  - Hỗ trợ `prefers-reduced-motion` và tách `viewer3d.js` chỉ nạp ở trang cần.
- **Tối ưu hiệu năng & Cache:** Thêm `SEND_FILE_MAX_AGE_DEFAULT = 604800` trong `config.py`.

### 2. Migration & Route `/credits`
- Migration `551a746e1148_add_car_hero_video_url_and_image_.py`: thêm `cars.hero_video_url` và `car_images.license`, `car_images.author`, `car_images.source_url`.
- Route `/credits` (`app/templates/main/credits.html`) đọc `app/static/ASSETS.json` và đặt link tại footer.

### 3. Script tải tài nguyên mở (`scripts/fetch_assets.py`, `scripts/optimize_images.py`)
- Hỗ trợ Pexels, Unsplash (có download tracking), Wikimedia Commons (lọc `CC0`/`PD`/`CC-BY`/`CC-BY-SA`), Openverse, Poly Haven (HDRI 2K `.hdr` CC0), và Sketchfab (`.glb`).
- Đã chạy `python scripts/fetch_assets.py --limit-cars 3` (tải được 4 ảnh Wikimedia Commons + 3 HDRI 2K Poly Haven) và `python scripts/fetch_assets.py --verify` (`[OK]`).

## 2026-11-22 (Phần 3) — Model 3D .glb thật, Render PBR & Ảnh chụp thật

### 1. Xóa placeholder khối hộp & Nạp `.glb` cục bộ
- Xóa `buildProceduralCar` khỏi `app/static/js/viewer3d.js`; nạp `.glb` bằng `GLTFLoader` + `DRACOLoader` + `MeshoptDecoder` với decoder đặt cục bộ tại `app/static/js/libs/draco/` và `app/static/js/libs/meshopt_decoder.module.js`.
- Khi xe chưa có `.glb`, hiển thị ảnh tĩnh và nhãn `"Model 3D đang cập nhật"`.
- Bổ sung `scripts/fetch_models.py` (Sketchfab API → fallback `mrdoob/three.js` `ferrari.glb`) và `scripts/inspect_glb.py`.

### 2. Gắn DB & Render PBR chân thực
- Migration `8fb48a88edc9_add_model_material_and_transform_fields_.py`: thêm `cars.body_material_names` (JSON), `cars.model_scale`, `cars.model_offset_y`.
- `viewer3d.js`: tự chuẩn hóa bounding box chạm sàn, chỉ đổi màu material trong `body_material_names` (`Body_Color`), `ACESFilmicToneMapping`, `SRGBColorSpace`, HDRI 2K (`RGBELoader` + `PMREMGenerator`), sàn tối phản chiếu + contact shadow, camera fly-in, tự hạ chất lượng trên thiết bị yếu và `dispose()` khi rời trang.
- Xóa ảnh `.svg` minh họa trong `app/static/img/cars/`, cập nhật `seed.py` và `admin/routes.py` sang ảnh thật `.webp`.

### 3. Kiểm tra & Trạng thái hiện tại
- Chạy `python scripts/fetch_models.py` tải `app/static/models/ferrari.glb` (`1,681,572 bytes`, `MIT License (three.js examples)`), gắn cho 12 xe với `body_material_names = ['Body_Color']`.
- Chạy `python scripts/inspect_glb.py app/static/models/ferrari.glb` xác nhận danh sách mesh & material.
- Chạy `python scripts/fetch_assets.py --verify` → `[OK]`, `compileall` và kiểm tra template/endpoint đạt `0` lỗi.
- Chạy server Flask (`5055`) và chụp màn hình `/cars/aurelia-gt-r9` ở desktop (`1440x900`) và mobile (`390x844`).
- **Còn thiếu / Tùy chọn:** Thêm `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY`, `SKETCHFAB_TOKEN` vào `.env` để tải thêm ảnh/video/model riêng cho từng xe.

## 2026-11-22 (Phần 4) — Chuyển đổi 100% sang Catalog Xe Thật, 12 Model 3D Sketchfab Riêng & 78 Ảnh Thật

### 1. Rà soát & loại bỏ `ferrari.glb` và dữ liệu xe hư cấu
- Kiểm tra header `ferrari.glb` (`asset={'generator': 'FBX2glTF', 'version': '2.0'}`) không chứa `copyright`/license, và URL Sketchfab gốc (`57bf6cc56931426e87494f554df1dab6`) đã `404` -> ghi log vào `asset_fetch_log` và xóa `ferrari.glb`.
- Ánh xạ (in-place update) 12 bản ghi xe hư cấu sang 12 mẫu xe thật ngoài đời thuộc 12 hãng thật (`Porsche`, `BMW`, `Audi`, `Mercedes-Benz`, `Lamborghini`, `Nissan`, `Ford`, `Mazda`, `Land Rover`, `Tesla`, `Volkswagen`, `Subaru`), bảo toàn 100% khóa ngoại (`orders`, `favorites`, `test_drive_requests`).

### 2. Schema Database mới (`d932fbcdbacc`)
- Thêm bảng `car_models` (nguồn sự thật duy nhất cho `.glb`, lưu `poly_count`, `file_size`, `sha256`, `author`, `license`, `license_url`, `source_url`, `body_material_names`, `scale`, `offset_y`, `is_active`).
- Bổ sung metadata cho `car_images` (`sha256`, `phash`, `width`, `height`, `file_size`, `is_hero`, `is_active`, `sort_order`, `shot_type`, `caption`, `match_level`, `source_name`, `source_id`, `image_blob`, `fetched_at`) và route `/media/image/<id>` (`ETag` + `304`).
- Thêm bảng `asset_fetch_log` lưu lịch sử tải và lý do từ chối của bộ lọc.

### 3. Công cụ `scripts/build_catalog.py` & Kết quả kiểm định (`--verify`)
- Tải thành công **12 model `.glb` xe thật riêng biệt** từ Sketchfab Data API (`CC BY 4.0`, `38,912 <= poly_count <= 489,304`, kiểm định tỷ lệ bounding box `L/W` và `L/H` bằng `scripts/inspect_glb.py`, loại bỏ 69 model không đạt chuẩn).
- Tải và tối ưu thành công **78 ảnh chụp thật** từ Wikimedia Commons (`72 exact` / `6 similar`, mỗi xe `5–7` ảnh đa góc chụp, kiểm định độ nét Laplacian variance, chống trùng `sha256` + `phash`).
- Cập nhật `/credits` truy vấn trực tiếp từ MySQL theo từng xe và nâng cấp Admin (`/admin/cars/<id>/edit`) quản lý model 3D & thư viện ảnh.
- Chạy `python scripts/build_catalog.py --verify` đạt `[OK]` (exit code `0`) và chụp 10 ảnh màn hình Desktop/Mobile không còn bất kỳ lỗi 404 nào.

## 2026-11-23 (Phần 5) — Tái thiết kế giao diện theo hệ thống `ai-design-skills` (`landing-page-design` & `figma-designer`)

### 1. Hệ thống Token & Visual System (`app/static/css/app.css`)
- **Typography (`B1`):** Dùng duy nhất font **Geist** (+ **Geist Mono** cho số liệu), thang chữ chuẩn Tailwind (`12px` đến `60px`), 26 class text style chuẩn tên (`.heading-1`..`.heading-6`, `.title-1`..`.title-5`, `.body-1`..`.body-6`, `.button-lg/md/sm/xsm`, `.caption-1`..`.caption-5`), không in nghiêng, không ultra-bold, `text-wrap: balance` / `pretty`, sentence case và bỏ dấu gạch nối trong câu.
- **Spacing & Radius (`B2`, `B3`):** Chỉ dùng đúng 13 bước `--spacing-0`..`--spacing-900` (`0..96px`), nút chính padding `8px 12px`; áp dụng công thức nested radius (`inner = outer - gap`: `.hero-frame` ngoài `24px` - đệm `16px` = ảnh trong `8px`; `.car-card` ngoài `16px` - đệm `8px` = ảnh trong `8px`).
- **Two-Layer Color Tokens & Bề mặt phẳng (`B4`, `figma-designer`):** Tách `Core Colors` và `Color System`, chỉ dùng nền tối được phép (`#000000`, `#181818`, `#1F1F1F`, `#272727`, `#313131`, `#131209`), không dùng background gradient, viền thẻ luôn bao kín 4 cạnh.

### 2. Cấu trúc Trang chủ & Chuyển động (`app/templates/main/index.html`, `app/static/js/cinema.html`)
- **Hero (`A2`, `B5`):** Tiêu đề gradient chữ trái sang phải `#FFFFFF → #9B9B9B`, giới hạn `680px`, 1 CTA chính duy nhất ở màn đầu (`Khám phá 12 mẫu xe có sẵn`), dải bằng chứng thương hiệu và khung ảnh tiêu điểm.
- **Mandatory Tagline Reveal (`B11`):** Section chữ lớn tách riêng, từng từ sáng dần theo thứ tự đọc khi cuộn qua vạch kích hoạt bằng `IntersectionObserver` + `requestAnimationFrame` trên đường cong `cubic-bezier(0.22, 1, 0.36, 1)`.
- **Các section chuyển đổi (`A2`):** Bento grid 4 lợi ích (kèm Phosphor Icons nét `1.75`), 2-column Featured Fleet, 3 bước How It Works, Telemetry + Testimonials thực tế, 6 câu hỏi FAQ (kèm JSON-LD `FAQPage`), và Risk Reversal + Final CTA.
- **Floating Navigation (`B7`):** Thanh điều hướng nổi cách mép trên `16px`, căn giữa, nền mờ `backdrop-filter: blur(16px)` và bảng menu toàn chiều cao với hiệu ứng stagger `60ms` (tối đa `400ms`).

## 2026-11-23 (Phần 6) — Khắc phục lỗi Cache CSS/JS, Navbar viên thuốc & Bố cục Hero 2 cột ở 1920x1080

### 1. Nguyên nhân gốc phát hiện được
- **Cache cứng 7 ngày (`SEND_FILE_MAX_AGE_DEFAULT = 604800` trong `config.py`) + thiếu query string `?v=`:** Trình duyệt Chrome thật ở `127.0.0.1:5000` nạp HTML mới nhưng dùng lại `app.css` và `cinema.js` cũ từ disk cache. File `app.css` cũ định nghĩa `.site-nav` full-width sát mép trái có `border-bottom`, thiếu hoàn toàn `.hero-gradient-title`, `.proof-strip__logos`, `.proof-brand`, `.hero-frame`, và ẩn `[data-reveal]` (`opacity: 0`).
- **Quá nhiều mục trên thanh điều hướng khi đã đăng nhập (`_navbar.html`):** Render tới 7 liên kết + tên user + nút Đăng xuất + hamburger trên cùng 1 hàng gây tràn và đè chữ.
- **Bố cục Hero 1 cột dọc (`index.html`):** Đẩy `.hero-frame` xuống dưới khiến nửa phải màn hình `1920x1080` bị trống và gắn `data-reveal` lên `.hero-frame`.
- **Reset `img, video, picture { width: 100%; }` quá rộng (`app.css`):** Làm ảnh hưởng tới các icon nhỏ trong flex container nếu không khóa kích thước.

### 2. Sửa lỗi & Kiểm chứng CDP ở 4 kích thước (`1920px`, `1440px`, `1280px`, `390px`)
- Đặt `SEND_FILE_MAX_AGE_DEFAULT = 0` trong `config.py` và gắn `?v=20261123b` cho `app.css` / `cinema.js` trong `base.html`.
- Giới hạn thanh điều hướng nổi (`.site-nav`, `border-radius: 9999px`, `top: 16px`, căn giữa trong `.wrap`) tối đa 4 liên kết chính + 1 nút hành động + nút hamburger; chuyển các mục còn lại vào bảng menu toàn màn hình.
- Chuyển Hero sang `.hero-layout` 2 cột trên desktop (`minmax(0, 640px) minmax(0, 1fr)`, `gap: 48px`), bỏ `data-reveal` trên `.hero-frame` để ảnh Porsche 911 Carrera luôn hiển thị ngay nửa phải màn đầu tiên.
- Đo đạc bằng Chrome DevTools Protocol (profile mới tắt cache) và chụp toàn bộ các đoạn cuộn ở `1920x1080`, `1440x900`, `1280x800`, `390x844` (`scrollWidth === clientWidth = 390` ở mobile).

## 2026-11-23 (Phần 7) — Bước 0 kiểm tra lớp CSS & Chuyển đổi toàn bộ sang Light Theme (`#FFFFFF` chủ đạo)

### 1. Kết quả Bước 0 (Kiểm tra template vs `app.css`)
- Chạy script đối chiếu toàn bộ `119` class trong `base.html`, `_navbar.html`, `_footer.html`, `_car_card.html`, `index.html`, `list.html`, `detail.html` với `app/static/css/app.css`: `118/119` class có định nghĩa, duy nhất `.scrolly-chapter` ở `detail.html` chưa có rule riêng.
- Nguyên nhân gốc khiến Chrome thật từng hiển thị sai trước đó: cache 7 ngày (`SEND_FILE_MAX_AGE_DEFAULT = 604800`) + thiếu `?v=` khiến Chrome nạp `app.css` cũ; đồng thời `app.css` đang dùng Dark Theme (`#000000` / `#181818`).

### 2. Chuyển đổi Light Theme & Bố cục 10 phần
- Áp dụng hệ màu 2 lớp nền trắng `#FFFFFF` (`80%` diện tích), `#F7F7F5` cho section xen kẽ, `#0A0A0A` cho khối CTA cuối, chữ `#0A0A0A` / `#55554F` / `#8A8A84`, nhấn cam `#E8792B` (`hover: #CF6A22`).
- Container chung `max-width: 1200px`, padding ngang `24px` (`16px` mobile).
- Navbar viên thuốc trắng mờ (`rgba(255,255,255,0.85) + blur(16px)`), 4 liên kết + 1 nút chính + hamburger mở menu toàn màn hình nền trắng.
- Hero 2 cột, dải thương hiệu marquee ngang, Tagline reveal chữ tối, Bento 4 ô, Xe nổi bật 3 cột, Quy trình 3 bước có đường nối, Social Proof, FAQ accordion 1 cột, CTA cuối `#0A0A0A` và Footer nền sáng.
