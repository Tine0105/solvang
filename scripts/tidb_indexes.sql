-- ============================================================================
-- Đề xuất Index cho TiDB Cloud Serverless / MySQL 8 (Solvang Motors)
-- Chạy thủ công trong TiDB Cloud SQL Editor hoặc MySQL Workbench (KHÔNG tự chạy)
-- ============================================================================

-- 1. Bảng cars: tối ưu query trang chủ (is_featured + ORDER BY created_at DESC)
--    và bộ lọc / sắp xếp ở trang /cars/
CREATE INDEX ix_cars_featured_created ON cars (is_featured, created_at DESC);
CREATE INDEX ix_cars_body_type ON cars (body_type);
CREATE INDEX ix_cars_fuel_type ON cars (fuel_type);
CREATE INDEX ix_cars_created_at ON cars (created_at DESC);

-- 2. Bảng car_images: tối ưu eager-load / lọc ảnh active, hero và thứ tự hiển thị
CREATE INDEX ix_car_images_car_active_hero_sort
    ON car_images (car_id, is_active, is_hero, sort_order, id);

-- 3. Bảng car_models: tối ưu tìm model 3D active của mỗi xe
CREATE INDEX ix_car_models_car_active ON car_models (car_id, is_active, id);

-- 4. Bảng car_colors: tối ưu lấy danh sách màu sơn theo car_id
CREATE INDEX ix_car_colors_car_id ON car_colors (car_id);

-- Ghi chú:
-- - cars.slug (unique), cars.price, cars.brand_id đã có index từ migration trước.
-- - favorites(user_id, car_id) đã có unique index uq_favorites_user_car.
