import os
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Brand, Car, CarColor, CarImage, Order, TestDriveRequest, User

app = create_app()


def _write_svg_assets(static_dir: str) -> None:
    brands_dir = os.path.join(static_dir, 'img', 'brands')
    cars_dir = os.path.join(static_dir, 'img', 'cars')
    os.makedirs(brands_dir, exist_ok=True)
    os.makedirs(cars_dir, exist_ok=True)

    brand_icons = {
        'aurelia': '#e07a2b',
        'korsen': '#38bdf8',
        'valkyr': '#34d399',
        'bellini': '#f43f5e',
        'takumi': '#f59e0b',
        'default': '#94a3b8',
    }
    for key, accent in brand_icons.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" fill="none">
  <rect width="64" height="64" rx="14" fill="#13161d"/>
  <circle cx="32" cy="32" r="18" stroke="{accent}" stroke-width="2.5"/>
  <circle cx="32" cy="32" r="5" fill="{accent}"/>
</svg>'''
        with open(os.path.join(brands_dir, f'{key}.svg'), 'w', encoding='utf-8') as f:
            f.write(svg)


def _write_car_svg(cars_dir: str, slug: str, accent_hex: str, body_type: str) -> str:
    is_suv = body_type.lower() == 'suv'
    roof_y = 148 if is_suv else 164
    body_path = (
        f'M120 265 L145 210 L235 {roof_y} L490 {roof_y} L595 208 L675 225 L685 268 Z'
        if is_suv
        else f'M115 265 L165 215 L270 {roof_y} L465 {roof_y} L575 210 L680 228 L688 268 Z'
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500" fill="none">
  <defs>
    <radialGradient id="bg-{slug}" cx="50%" cy="48%" r="55%">
      <stop offset="0%" stop-color="#1e2430"/>
      <stop offset="100%" stop-color="#0b0d10"/>
    </radialGradient>
    <linearGradient id="paint-{slug}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent_hex}"/>
      <stop offset="100%" stop-color="#161a22"/>
    </linearGradient>
  </defs>
  <rect width="800" height="500" fill="url(#bg-{slug})"/>
  <ellipse cx="400" cy="312" rx="310" ry="26" fill="#050608" opacity="0.85"/>
  <path d="{body_path}" fill="url(#paint-{slug})" stroke="rgba(255,255,255,0.22)" stroke-width="2"/>
  <path d="M275 {roof_y + 10} L455 {roof_y + 10} L535 206 L210 206 Z" fill="#0d1118" opacity="0.88"/>
  <rect x="655" y="232" width="26" height="8" rx="4" fill="#f8fafc"/>
  <rect x="120" y="234" width="22" height="7" rx="3" fill="#e11d48"/>
  <circle cx="235" cy="272" r="44" fill="#0f1217" stroke="#64748b" stroke-width="5"/>
  <circle cx="235" cy="272" r="22" fill="#1e293b" stroke="{accent_hex}" stroke-width="2"/>
  <circle cx="565" cy="272" r="44" fill="#0f1217" stroke="#64748b" stroke-width="5"/>
  <circle cx="565" cy="272" r="22" fill="#1e293b" stroke="{accent_hex}" stroke-width="2"/>
</svg>'''
    filename = f'{slug}.svg'
    with open(os.path.join(cars_dir, filename), 'w', encoding='utf-8') as f:
        f.write(svg)
    return f'/static/img/cars/{filename}'


def run_seed():
    with app.app_context():
        _write_svg_assets(app.static_folder)
        cars_dir = os.path.join(app.static_folder, 'img', 'cars')

        if User.query.first():
            print('Dữ liệu đã tồn tại. Bỏ qua bước seed.')
            return

        # 1. Users: 1 admin + 2 users
        admin = User(full_name='Quản trị Solvang', email='admin@example.com', phone='0901000001', role='admin')
        admin.set_password('Admin@123456')

        user1 = User(full_name='Trần Minh Khôi', email='minh.tran@example.com', phone='0902000002', role='user')
        user1.set_password('User@123456')

        user2 = User(full_name='Nguyễn Thảo Linh', email='linh.nguyen@example.com', phone='0903000003', role='user')
        user2.set_password('User@123456')

        db.session.add_all([admin, user1, user2])
        db.session.flush()

        # 2. 5 Fictional Brands
        brands_data = [
            ('Aurelia', '/static/img/brands/aurelia.svg'),
            ('Korsen', '/static/img/brands/korsen.svg'),
            ('Valkyr', '/static/img/brands/valkyr.svg'),
            ('Bellini', '/static/img/brands/bellini.svg'),
            ('Takumi', '/static/img/brands/takumi.svg'),
        ]
        brand_map = {}
        for name, logo in brands_data:
            b = Brand(name=name, logo=logo)
            db.session.add(b)
            brand_map[name] = b
        db.session.flush()

        # 3. 12 Fictional Cars (each 3-5 colors)
        cars_seed = [
            ('Aurelia', 'Aurelia GT-R9', 'aurelia-gt-r9', 2026, 4850000000, 0, 'Hybrid', 'Ly hợp kép 7 cấp', 'Coupe', 2, 3, True,
             'Coupé hai cửa khung gầm sợi carbon, hệ truyền động Hybrid V6 tăng áp kép cho khả năng tăng tốc 0–100 km/h trong 2,9 giây.',
             [('Cam Copper', '#E07A2B'), ('Đen Obsidian', '#161A22'), ('Bạc Titan', '#8D99AE'), ('Xanh Nord', '#1D3557')]),
            ('Aurelia', 'Aurelia Strada S', 'aurelia-strada-s', 2025, 3690000000, 1200, 'Xăng', 'Tự động 8 cấp', 'Sedan', 4, 4, True,
             'Sedan thể thao cân bằng giữa sự êm ái đường trường và phản hồi vô-lăng sắc bén trên đường đèo.',
             [('Xám Graphite', '#4B5563'), ('Trắng Ngọc', '#E5E7EB'), ('Đỏ Crimson', '#B91C1C')]),
            ('Aurelia', 'Aurelia Aperta', 'aurelia-aperta', 2026, 5420000000, 0, 'Xăng', 'Ly hợp kép 7 cấp', 'Roadster', 2, 2, False,
             'Phiên bản mui trần thiết kế khí động học với hệ thống ống xả titan nguyên khối.',
             [('Vàng Amber', '#D97706'), ('Đen Matte', '#18181B'), ('Xanh Midnight', '#1E3A5F'), ('Bạc Satin', '#9CA3AF')]),
            ('Korsen', 'Korsen E-Zero', 'korsen-e-zero', 2026, 4200000000, 0, 'Điện', 'Tự động 1 cấp', 'Coupe', 4, 5, True,
             'Xe điện thuần túy kiến trúc 800V, phạm vi di chuyển 680 km và sạc nhanh 10–80% trong 18 phút.',
             [('Xanh Glacier', '#38BDF8'), ('Đen Carbon', '#111827'), ('Trắng Arctic', '#F3F4F6'), ('Cam Racing', '#EA580C')]),
            ('Korsen', 'Korsen Volt Touring', 'korsen-volt-touring', 2025, 3450000000, 500, 'Điện', 'Tự động 1 cấp', 'Touring', 5, 4, True,
             'Mẫu touring thuần điện khoang hành lý rộng rãi, dẫn động bốn bánh toàn thời gian hai mô-tơ.',
             [('Xanh Deep Sea', '#0F4C81'), ('Xám Slate', '#475569'), ('Bạc Mercury', '#CBD5E1')]),
            ('Korsen', 'Korsen Apex EV', 'korsen-apex-ev', 2026, 6100000000, 0, 'Điện', 'Tự động 1 cấp', 'Sedan', 4, 2, False,
             'Sedan điện hiệu năng cao với ba mô-tơ độc lập và hệ thống treo khí nén chủ động.',
             [('Đen Onyx', '#0F172A'), ('Đồng Bronze', '#B45309'), ('Trắng Pearl', '#E2E8F0')]),
            ('Valkyr', 'Valkyr Nordik X7', 'valkyr-nordik-x7', 2026, 4590000000, 0, 'Hybrid', 'Tự động 8 cấp', 'SUV', 7, 4, True,
             'SUV hiệu năng cao thiết kế Bắc Âu với hệ dẫn động bốn bánh thông minh và nội thất da tự nhiên.',
             [('Xanh Forest', '#1E463A'), ('Xám Storm', '#374151'), ('Đen Basalt', '#171717'), ('Cát Desert', '#A88B68')]),
            ('Valkyr', 'Valkyr Fjell E', 'valkyr-fjell-e', 2025, 3890000000, 2400, 'Điện', 'Tự động 1 cấp', 'SUV', 5, 3, False,
             'SUV điện cỡ trung với khoảng sáng gầm 220 mm và khả năng lội nước 700 mm.',
             [('Xanh Pine', '#14532D'), ('Bạc Frost', '#94A3B8'), ('Đen Obsidian', '#18181B')]),
            ('Bellini', 'Bellini Corsa V8', 'bellini-corsa-v8', 2026, 6950000000, 0, 'Xăng', 'Ly hợp kép 7 cấp', 'Coupe', 2, 2, True,
             'Siêu xe động cơ đặt giữa V8 hút khí tự nhiên vòng tua 9.000 vòng/phút, chế tác thủ công tại Ý.',
             [('Đỏ Rosso', '#DC2626'), ('Vàng Modena', '#EAB308'), ('Đen Nero', '#111317'), ('Trắng Bianco', '#F1F5F9')]),
            ('Bellini', 'Bellini Vento Spider', 'bellini-vento-spider', 2025, 7250000000, 300, 'Xăng', 'Ly hợp kép 7 cấp', 'Roadster', 2, 1, False,
             'Roadster mui xếp cứng điện tử chỉ mất 11 giây đóng mở ngay cả khi xe đang chạy.',
             [('Cam Solar', '#EA580C'), ('Đỏ Rubino', '#991B1B'), ('Xám Grigio', '#52525B')]),
            ('Takumi', 'Takumi Kaze GT', 'takumi-kaze-gt', 2026, 2980000000, 0, 'Hybrid', 'Tự động 8 cấp', 'Sedan', 5, 6, False,
             'Sedan hybrid tiết kiệm nhiên liệu nhưng vẫn giữ độ bốc tức thì nhờ mô-tơ điện hỗ trợ mô-men xoắn.',
             [('Xám Gunmetal', '#3F3F46'), ('Trắng Silk', '#F8FAFC'), ('Xanh Indigo', '#1E3A8A')]),
            ('Takumi', 'Takumi Sora Coupe', 'takumi-sora-coupe', 2025, 2650000000, 1800, 'Xăng', 'Số sàn 6 cấp', 'Coupe', 4, 3, False,
             'Coupé cầu sau hộp số sàn 6 cấp thuần khiết dành cho người yêu cảm giác lái cơ khí.',
             [('Xanh Cobalt', '#2563EB'), ('Đen Jet', '#141414'), ('Bạc Metallic', '#A1A1AA'), ('Đỏ Ruby', '#BE123C')]),
        ]

        created_cars = []
        default_model = '/static/models/ferrari.glb' if os.path.exists(os.path.join(app.static_folder, 'models', 'ferrari.glb')) else None
        for brand_name, name, slug, year, price, mileage, fuel, trans, body, seats, stock, featured, desc, colors in cars_seed:
            hero_webp = os.path.join(cars_dir, slug, 'hero-thumb.webp')
            thumb = f'/static/img/cars/{slug}/hero-thumb.webp' if os.path.exists(hero_webp) else '/static/img/cars/aurelia-gt-r9/hero-thumb.webp'
            slug_glb = os.path.join(app.static_folder, 'models', f'{slug}.glb')
            model_url = f'/static/models/{slug}.glb' if os.path.exists(slug_glb) else default_model
            car = Car(
                brand_id=brand_map[brand_name].id,
                name=name,
                slug=slug,
                year=year,
                price=price,
                mileage=mileage,
                fuel_type=fuel,
                transmission=trans,
                body_type=body,
                seats=seats,
                stock=stock,
                is_featured=featured,
                description=desc,
                model_url=model_url,
                body_material_names=['Body_Color'] if model_url else None,
                model_scale=1.0,
                model_offset_y=0.0,
                thumbnail=thumb,
            )
            db.session.add(car)
            db.session.flush()

            for cname, chex in colors:
                db.session.add(CarColor(car_id=car.id, color_name=cname, hex_code=chex))

            db.session.add(CarImage(car_id=car.id, image_url=thumb))
            created_cars.append(car)

        db.session.flush()

        # 4. Sample orders & test drives
        first_color = CarColor.query.filter_by(car_id=created_cars[0].id).first()
        second_color = CarColor.query.filter_by(car_id=created_cars[3].id).first()

        db.session.add_all([
            Order(user_id=user1.id, car_id=created_cars[0].id, color_id=first_color.id if first_color else None,
                  status='confirmed', note='Giao xe tại showroom Quận 1.'),
            Order(user_id=user2.id, car_id=created_cars[3].id, color_id=second_color.id if second_color else None,
                  status='pending', note='Cần tư vấn gói sạc tại nhà.'),
            TestDriveRequest(user_id=user1.id, car_id=created_cars[8].id,
                             preferred_date=date.today() + timedelta(days=3), status='confirmed'),
        ])

        db.session.commit()
        print('Seed thành công: 1 admin, 2 user, 5 hãng, 12 xe, màu sơn và đơn hàng mẫu.')


if __name__ == '__main__':
    run_seed()
