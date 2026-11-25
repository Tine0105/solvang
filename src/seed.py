"""Script khởi tạo dữ liệu mẫu và tài khoản Demo (Admin & User) cho hệ thống LuxAuto Showroom."""

from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models import Brand, Car, CarImage, Order, TestDrive, User


def seed_database() -> None:
    """Tạo bảng (nếu chưa có) và nạp dữ liệu mẫu gồm 7 hãng, 14 xe sang, 3 tài khoản và đơn đặt cọc."""
    app = create_app("default")
    with app.app_context():
        db.create_all()

        if User.query.first():
            print("Cơ sở dữ liệu đã có dữ liệu mẫu. Bỏ qua bước seed.")
            return

        # 1. Tạo tài khoản Demo (1 Admin + 2 User)
        admin = User(
            full_name="Nguyễn Minh Tiến (Admin)",
            email="admin@luxauto.vn",
            phone="0901234567",
            role="admin",
            is_verified=True,
        )
        admin.set_password("Admin@123")

        user1 = User(
            full_name="Trần Hoàng Nam",
            email="user@luxauto.vn",
            phone="0909888777",
            role="user",
            is_verified=True,
        )
        user1.set_password("User@123")

        user2 = User(
            full_name="Lê Ngọc Mai",
            email="khachhang@luxauto.vn",
            phone="0912345678",
            role="user",
            is_verified=True,
        )
        user2.set_password("User@123")

        db.session.add_all([admin, user1, user2])
        db.session.flush()

        # 2. Tạo 7 thương hiệu xe sang
        brands_seed = [
            ("Porsche", "Đức", "/static/img/brands/porsche.svg", "Biểu tượng xe thể thao hiệu năng cao từ Stuttgart."),
            ("Lamborghini", "Ý", "/static/img/brands/lamborghini.svg", "Siêu xe động cơ V10/V12 thiết kế góc cạnh từ Sant'Agata Bolognese."),
            ("Mercedes-AMG", "Đức", "/static/img/brands/mercedes-benz.svg", "Phân nhánh hiệu suất cao thủ công One Man, One Engine."),
            ("Audi Sport", "Đức", "/static/img/brands/audi.svg", "Đỉnh cao công nghệ dẫn động bốn bánh toàn thời gian Quattro."),
            ("BMW M", "Đức", "/static/img/brands/bmw.svg", "Dòng xe thể thao hiệu suất cao Motorsport từ Munich."),
            ("Land Rover", "Vương quốc Anh", "/static/img/brands/land-rover.svg", "SUV hạng sang địa hình hoàng gia Anh Quốc."),
            ("Tesla Performance", "Hoa Kỳ", "/static/img/brands/tesla.svg", "Xe điện thông minh tăng tốc siêu thanh."),
        ]
        brand_map: dict[str, Brand] = {}
        for b_name, country, logo, desc in brands_seed:
            b = Brand(name=b_name, country=country, logo_url=logo, description=desc)
            db.session.add(b)
            brand_map[b_name] = b
        db.session.flush()

        # 3. Tạo 14 mẫu xe sang (kèm bộ ảnh thật tại /static/img/cars/<folder>/)
        cars_seed = [
            (
                "Porsche", "Porsche 911 Carrera S", "porsche-911-carrera-s", 2026, 8_950_000_000, 480, 0,
                "Xăng", "Ly hợp kép PDK 8 cấp", "Coupe", "Bạc GT Silver", 4, 2, True, "porsche-911-carrera",
                "Mẫu coupé huyền thoại trang bị động cơ Boxer 6 xy-lanh tăng áp kép 3.0L đặt sau, gói Sport Chrono tăng tốc 0–100 km/h trong 3,3 giây và hệ thống treo chủ động PASM.",
            ),
            (
                "Lamborghini", "Lamborghini Huracán EVO", "lamborghini-huracan-evo", 2026, 18_500_000_000, 640, 0,
                "Xăng", "Ly hợp kép PDK 8 cấp", "Coupe", "Cam Arancio Xanto", 2, 1, True, "lamborghini-huracan-evo",
                "Siêu xe động cơ V10 5.2L hút khí tự nhiên sản sinh 640 mã lực, tích hợp hệ thống điều khiển khí động học chủ động ALA và đánh lái bánh sau thông minh.",
            ),
            (
                "Mercedes-AMG", "Mercedes-AMG GT 63 Coupé", "mercedes-amg-gt-63", 2026, 11_890_000_000, 585, 0,
                "Xăng", "Tự động 9G-TRONIC", "Coupe", "Xám Selenite Magno", 2, 2, True, "mercedes-amg-gt",
                "Tuyệt tác Grand Tourer lắp ráp thủ công tại Affalterbach với khối động cơ V8 4.0L Biturbo, dẫn động 4MATIC+ biến thiên toàn phần và nội thất da Nappa Exclusive.",
            ),
            (
                "Audi Sport", "Audi R8 V10 Performance", "audi-r8-v10-performance", 2025, 14_200_000_000, 620, 1200,
                "Xăng", "Ly hợp kép PDK 8 cấp", "Coupe", "Xanh Ascari Metallic", 2, 1, True, "audi-r8-v10",
                "Siêu xe chia sẻ khung gầm sợi carbon ASF và khối động cơ V10 vòng tua cao 8.700 vòng/phút, phanh gốm carbon tiêu chuẩn cùng buồng lái kỹ thuật số Virtual Cockpit.",
            ),
            (
                "Land Rover", "Range Rover Autobiography LWB", "range-rover-autobiography-lwb", 2026, 12_650_000_000, 530, 0,
                "Hybrid", "Tự động 8 cấp ZF", "SUV", "Đen Santorini", 5, 3, True, "range-rover-autobiography",
                "SUV hạng sang trục cơ sở dài với ghế thương gia Executive Class tích hợp massage đá nóng, hệ thống lọc khí Cabin Air Purification Pro và âm thanh Meridian Signature 35 loa.",
            ),
            (
                "BMW M", "BMW M3 Competition xDrive", "bmw-m3-competition-xdrive", 2026, 5_390_000_000, 510, 0,
                "Xăng", "Tự động 8 cấp ZF", "Sedan", "Xanh Isle of Man", 5, 3, True, "bmw-m3-competition",
                "Sedan thể thao hiệu suất cao sử dụng động cơ S58 I6 3.0L M TwinPower Turbo, mui xe sợi carbon M Carbon trần và ghế đua M Carbon Bucket Seats.",
            ),
            (
                "Porsche", "Porsche 911 Targa 4 GTS", "porsche-911-targa-4-gts", 2025, 10_450_000_000, 541, 800,
                "Hybrid", "Ly hợp kép PDK 8 cấp", "Roadster", "Đỏ Carmine", 4, 1, False, "porsche-911-carrera",
                "Phiên bản Targa mui vòm kính biểu tượng kết hợp công nghệ T-Hybrid thế hệ mới với bộ tăng áp điện tử eTurbo phản hồi tức thì.",
            ),
            (
                "Mercedes-AMG", "Mercedes-AMG SL 63 Roadster", "mercedes-amg-sl-63-roadster", 2025, 10_950_000_000, 585, 500,
                "Xăng", "Tự động 9G-TRONIC", "Roadster", "Trắng Manufaktur Opalite", 4, 2, False, "mercedes-amg-gt",
                "Roadster 2+2 hạng sang mui mềm 3 lớp đóng mở trong 15 giây, trang bị hệ thống sưởi cổ AIRSCARF và màn hình trung tâm điều chỉnh góc nghiêng chống chói.",
            ),
            (
                "Lamborghini", "Lamborghini Huracán Sterrato", "lamborghini-huracan-sterrato", 2025, 19_200_000_000, 610, 600,
                "Xăng", "Ly hợp kép PDK 8 cấp", "Coupe", "Xanh Verde Gea", 2, 1, False, "lamborghini-huracan-evo",
                "Phiên bản siêu xe đa địa hình giới hạn toàn cầu với khoảng sáng gầm nâng cao 44 mm, chế độ lái Rally chuyên biệt và ốp vòm bánh cơ bắp.",
            ),
            (
                "Land Rover", "Range Rover SV Bespoke", "range-rover-sv-bespoke", 2026, 16_800_000_000, 615, 0,
                "Xăng", "Tự động 8 cấp ZF", "SUV", "Đồng Sunrise Copper", 4, 1, False, "range-rover-autobiography",
                "Đỉnh cao cá nhân hóa từ bộ phận Special Vehicle Operations với chi tiết ốp gốm sứ thủ công, bàn làm việc chỉnh điện Club Table và tủ lạnh Champagne.",
            ),
            (
                "Tesla Performance", "Tesla Model 3 Performance AWD", "tesla-model-3-performance", 2026, 2_890_000_000, 510, 0,
                "Điện", "Tự động 1 cấp (EV)", "Sedan", "Đỏ Ultra Red", 5, 4, False, "tesla-model-3-performance",
                "Sedan thuần điện hai mô-tơ dẫn động bốn bánh AWD tăng tốc 0–100 km/h trong 3,1 giây, hệ thống giảm xóc thích ứng thế hệ mới và Track Mode V3.",
            ),
            (
                "BMW M", "BMW M4 Competition Coupé", "bmw-m4-competition-coupe", 2025, 5_650_000_000, 530, 1500,
                "Xăng", "Tự động 8 cấp ZF", "Coupe", "Vàng Sao Paulo", 4, 2, False, "bmw-m3-competition",
                "Coupé hai cửa hiệu năng cao trang bị hệ dẫn động M xDrive có thể chuyển sang cầu sau thuần túy 2WD cùng hệ thống kiểm soát độ trượt 10 cấp độ.",
            ),
            (
                "Audi Sport", "Audi RS e-tron GT", "audi-rs-etron-gt", 2026, 5_990_000_000, 637, 0,
                "Điện", "Tự động 1 cấp (EV)", "Sedan", "Xám Kemora", 4, 2, False, "audi-r8-v10",
                "Grand Tourer thuần điện kiến trúc 800V sạc siêu nhanh DC 270 kW, khung gầm treo khí nén 3 buồng và âm thanh thể thao e-tron Sport Sound.",
            ),
            (
                "Porsche", "Porsche 911 GT3 Touring", "porsche-911-gt3-touring", 2025, 13_400_000_000, 510, 450,
                "Xăng", "Số sàn 6 cấp", "Coupe", "Xanh Shark Blue", 2, 1, False, "porsche-911-carrera",
                "Phiên bản GT3 tinh tế lược bỏ cánh gió cố định, sử dụng động cơ 4.0L hút khí tự nhiên vòng tua 9.000 vòng/phút kết hợp hộp số sàn GT 6 cấp thuần khiết.",
            ),
        ]

        model_materials_map = {
            "porsche-911-carrera": ["EXT_Carpaint_Inst"],
            "lamborghini-huracan-evo": ["EXT_Paint"],
            "mercedes-amg-gt": ["body"],
            "audi-r8-v10": ["body"],
            "range-rover-autobiography": ["Car_Body"],
            "bmw-m3-competition": [
                "e92_paint",
                "e92_plastic_exterior_glossy",
                "e92_plastic_exterior",
                "e92_plastic_exterior.001",
            ],
            "tesla-model-3-performance": ["carpaint"],
        }

        created_cars: list[Car] = []
        shot_files = [
            ("hero-1280w.webp", "Góc chụp chính diện Studio"),
            ("exterior-1-1280w.webp", "Ngoại thất góc nghiêng"),
            ("interior-1280w.webp", "Khoang nội thất cao cấp"),
            ("wheel-1280w.webp", "Mâm hợp kim & Phanh hiệu suất cao"),
        ]

        for (
            b_name, name, slug, year, price, hp, mileage,
            fuel, trans, body, color, seats, stock, featured, asset_dir, desc
        ) in cars_seed:
            thumb_url = f"/static/img/cars/{asset_dir}/hero-1280w.webp"
            model_3d_url = f"/static/models/{asset_dir}.glb"
            car = Car(
                brand_id=brand_map[b_name].id,
                name=name,
                slug=slug,
                year=year,
                price=price,
                horsepower=hp,
                mileage=mileage,
                fuel_type=fuel,
                transmission=trans,
                body_type=body,
                exterior_color=color,
                seats=seats,
                stock=stock,
                is_featured=featured,
                thumbnail_url=thumb_url,
                model_3d_url=model_3d_url,
                body_material_names=model_materials_map.get(asset_dir, ["body"]),
                description=desc,
            )
            db.session.add(car)
            db.session.flush()

            for idx, (fname, caption) in enumerate(shot_files):
                db.session.add(
                    CarImage(
                        car_id=car.id,
                        image_url=f"/static/img/cars/{asset_dir}/{fname}",
                        caption=caption,
                        sort_order=idx,
                    )
                )
            created_cars.append(car)

        # 4. Tạo quan hệ n-n Yêu thích mẫu
        user1.favorite_cars.extend([created_cars[0], created_cars[1], created_cars[4]])
        user2.favorite_cars.extend([created_cars[2], created_cars[5]])

        # 5. Tạo 4 đơn đặt cọc mẫu ở các trạng thái khác nhau (phục vụ biểu đồ Dashboard)
        orders_seed = [
            Order(
                order_code="LUX-20261120-A101",
                user_id=user1.id,
                car_id=created_cars[0].id,
                total_price=created_cars[0].price,
                deposit_amount=int(created_cars[0].price * 0.05),
                payment_method="bank_qr",
                payment_status="paid",
                status="confirmed",
                customer_phone="0909888777",
                note="Yêu cầu phủ gốm Ceramic trước khi giao xe tại Quận 1.",
            ),
            Order(
                order_code="LUX-20261121-B202",
                user_id=user2.id,
                car_id=created_cars[4].id,
                total_price=created_cars[4].price,
                deposit_amount=int(created_cars[4].price * 0.05),
                payment_method="bank_qr",
                payment_status="paid",
                status="completed",
                customer_phone="0912345678",
                note="Giao xe tận nhà tại Thảo Điền, TP. Thủ Đức.",
            ),
            Order(
                order_code="LUX-20261123-C303",
                user_id=user1.id,
                car_id=created_cars[2].id,
                total_price=created_cars[2].price,
                deposit_amount=int(created_cars[2].price * 0.05),
                payment_method="showroom",
                payment_status="unpaid",
                status="pending",
                customer_phone="0909888777",
                note="Hẹn cuối tuần ghé showroom ký hợp đồng đặt cọc.",
            ),
            Order(
                order_code="LUX-20261118-D404",
                user_id=user2.id,
                car_id=created_cars[5].id,
                total_price=created_cars[5].price,
                deposit_amount=int(created_cars[5].price * 0.05),
                payment_method="bank_qr",
                payment_status="unpaid",
                status="cancelled",
                customer_phone="0912345678",
                note="Đổi sang phiên bản SUV Range Rover.",
            ),
        ]
        db.session.add_all(orders_seed)

        # 6. Tạo 2 lịch hẹn lái thử mẫu
        db.session.add_all(
            [
                TestDrive(
                    user_id=user1.id,
                    car_id=created_cars[1].id,
                    preferred_date=date.today() + timedelta(days=3),
                    time_slot="09:00 - 11:00",
                    phone="0909888777",
                    status="confirmed",
                    note="Trải nghiệm thực tế Huracán EVO.",
                ),
                TestDrive(
                    user_id=user2.id,
                    car_id=created_cars[3].id,
                    preferred_date=date.today() + timedelta(days=5),
                    time_slot="14:00 - 16:00",
                    phone="0912345678",
                    status="pending",
                    note="Lái thử cung đường đại lộ.",
                ),
            ]
        )

        db.session.commit()
        print("Khởi tạo dữ liệu mẫu thành công: 3 User, 7 Hãng xe, 14 Xe sang, 4 Đơn đặt cọc, 2 Lịch lái thử.")


if __name__ == "__main__":
    seed_database()
