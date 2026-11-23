"""Unified Real-World Car Catalog Builder: Sketchfab 3D .glb + Wikimedia/Pexels/Unsplash/Openverse Photos.

Usage:
    python scripts/build_catalog.py --cars 12
    python scripts/build_catalog.py --cars 12 --resume
    python scripts/build_catalog.py --only-models
    python scripts/build_catalog.py --only-images
    python scripts/build_catalog.py --car porsche-911-carrera
    python scripts/build_catalog.py --dry-run
    python scripts/build_catalog.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.extensions import db
from app.models import AssetFetchLog, Brand, Car, CarColor, CarImage, CarModel
from scripts.inspect_glb import inspect_glb, validate_car_glb
from scripts.optimize_images import compute_dhash, compute_laplacian_variance, optimize_image

load_dotenv(ROOT_DIR / '.env')

STATIC_DIR = ROOT_DIR / 'app' / 'static'
MODELS_DIR = STATIC_DIR / 'models'
CARS_IMG_DIR = STATIC_DIR / 'img' / 'cars'
BRANDS_IMG_DIR = STATIC_DIR / 'img' / 'brands'
HDRI_DIR = STATIC_DIR / 'hdri'
ASSETS_JSON_PATH = STATIC_DIR / 'ASSETS.json'

USER_AGENT = 'SolvangWebLab/2.0 (https://solvang.example; educational-automotive-showroom)'

REJECT_3D_KEYWORDS = (
    'low-poly', 'lowpoly', 'low poly', 'cartoon', 'stylized', 'voxel', 'pixel',
    'lego', 'toy', 'rc ', 'miniature', 'wreck', 'destroyed', 'rusty', 'burnt',
    'cyberpunk', 'sci-fi', 'scifi', 'concept', 'wheel only', 'rim only', 'tire only',
    'engine only', 'interior only', 'garage', 'diorama', 'pack', 'blockbench',
    'minecraft', 'roblox', ' Simpson', 'anime', 'chibi', 'flying', 'hover',
)

REJECT_IMG_REGEX = re.compile(
    r'\b(selfie|portrait|face closeup|license plate|number plate|3d render|cgi|forza|'
    r'gran turismo|assetto corsa|need for speed|gta|screenshot|watermark|toy car|'
    r'scale model|diecast|hot wheels|lego|wreck|accident|crash|damaged)\b',
    re.IGNORECASE,
)

ALLOWED_SKETCHFAB_LICENSES = {
    'cc0': ('CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'),
    'by': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
    'by-sa': ('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
}

ALLOWED_COMMONS_LICENSES = {
    'cc0': ('CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'),
    'cc-zero': ('CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'),
    'public domain': ('Public Domain', 'https://creativecommons.org/publicdomain/mark/1.0/'),
    'pd': ('Public Domain', 'https://creativecommons.org/publicdomain/mark/1.0/'),
    'cc-by-sa': ('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
    'cc by-sa': ('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
    'cc-by': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
    'cc by': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
}

# Candidate pool of real-world vehicles across Coupe, Sedan, SUV, Roadster, Touring/Hatchback
REAL_CAR_CANDIDATES: list[dict[str, Any]] = [
    {
        'brand': 'Porsche', 'name': 'Porsche 911 Carrera', 'slug': 'porsche-911-carrera',
        'query_3d': 'Porsche 911', 'wiki_query': 'Porsche 911',
        'year': 2023, 'price': 8900000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 4, 'featured': True,
        'description': 'Biểu tượng xe thể thao Đức với động cơ Boxer 6 xi-lanh đặt sau, khung gầm cân bằng chính xác và hộp số ly hợp kép PDK phản hồi tức thì.',
        'colors': [('Đỏ Guards Red', '#C8102E'), ('Bạc GT Silver', '#9EA3A8'), ('Đen Jet Black', '#141619'), ('Vàng Racing Yellow', '#F5C400')],
    },
    {
        'brand': 'BMW', 'name': 'BMW M3 Competition', 'slug': 'bmw-m3-competition',
        'query_3d': 'BMW M3', 'wiki_query': 'BMW M3',
        'year': 2023, 'price': 4950000000, 'body_type': 'Sedan', 'fuel_type': 'Xăng',
        'transmission': 'Tự động 8 cấp', 'seats': 5, 'featured': True,
        'description': 'Sedan hiệu năng cao trang bị động cơ S58 3.0L I6 M TwinPower Turbo 510 mã lực, hệ dẫn động M xDrive và vi sai chủ động.',
        'colors': [('Xanh Isle of Man', '#1B4D3E'), ('Xám Brooklyn Grey', '#6E737B'), ('Đen Sapphire', '#111317'), ('Xanh Yas Marina', '#1D63B8')],
    },
    {
        'brand': 'Audi', 'name': 'Audi R8 V10 Performance', 'slug': 'audi-r8-v10',
        'query_3d': 'Audi R8', 'wiki_query': 'Audi R8',
        'year': 2022, 'price': 11200000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 2, 'featured': True,
        'description': 'Siêu xe động cơ đặt giữa V10 5.2L hút khí tự nhiên sản sinh 620 mã lực, hệ dẫn động bốn bánh toàn thời gian quattro và khung gầm Audi Space Frame.',
        'colors': [('Xanh Ascari Blue', '#1E3A8A'), ('Xám Suzuka Grey', '#D1D5DB'), ('Đỏ Tango Red', '#B91C1C'), ('Đen Mythos', '#16181D')],
    },
    {
        'brand': 'Mercedes-Benz', 'name': 'Mercedes-AMG GT', 'slug': 'mercedes-amg-gt',
        'query_3d': 'Mercedes AMG GT', 'wiki_query': 'Mercedes-AMG GT',
        'year': 2023, 'price': 8650000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 2, 'featured': True,
        'description': 'Grand Tourer nắp ca-pô dài đặc trưng với động cơ V8 4.0L Biturbo lắp ráp thủ công theo triết lý One Man, One Engine tại Affalterbach.',
        'colors': [('Vàng Solarbeam', '#D97706'), ('Xám Selenite Magno', '#4B5563'), ('Đen Obsidian', '#121417'), ('Bạc Iridium', '#9CA3AF')],
    },
    {
        'brand': 'Lamborghini', 'name': 'Lamborghini Huracán EVO', 'slug': 'lamborghini-huracan-evo',
        'query_3d': 'Lamborghini Huracan', 'wiki_query': 'Lamborghini Huracán',
        'year': 2023, 'price': 18500000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 2, 'featured': True,
        'description': 'Siêu xe Ý động cơ V10 5.2L hút khí tự nhiên 640 mã lực, hệ thống điều khiển khí động học chủ động và đánh lái bánh sau LDVI.',
        'colors': [('Cam Arancio Xanto', '#EA580C'), ('Xanh Verde Mantis', '#65A30D'), ('Vàng Giallo Inti', '#EAB308'), ('Đen Nero Noctis', '#141518')],
    },
    {
        'brand': 'Nissan', 'name': 'Nissan GT-R Nismo', 'slug': 'nissan-gt-r-nismo',
        'query_3d': 'Nissan GTR', 'wiki_query': 'Nissan GT-R',
        'year': 2023, 'price': 7800000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 4, 'featured': True,
        'description': 'Huyền thoại tốc độ Nhật Bản với động cơ VR38DETT V6 3.8L tăng áp kép chế tác thủ công oleh Takumi và hệ dẫn động ATTESA E-TS AWD.',
        'colors': [('Trắng Pearl White', '#F3F4F6'), ('Xám Stealth Grey', '#475569'), ('Xanh Bayside Blue', '#1D4ED8'), ('Đen Super Black', '#111318')],
    },
    {
        'brand': 'Toyota', 'name': 'Toyota GR Supra', 'slug': 'toyota-gr-supra',
        'query_3d': 'Toyota Supra', 'wiki_query': 'Toyota Supra',
        'year': 2023, 'price': 3950000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Tự động 8 cấp', 'seats': 2, 'featured': False,
        'description': 'Coupé thể thao cầu sau phát triển bởi Gazoo Racing với tỷ lệ phân bổ trọng lượng 50:50 hoàn hảo và động cơ 3.0L tăng áp 6 xi-lanh thẳng hàng.',
        'colors': [('Đỏ Renaissance Red', '#DC2626'), ('Vàng Nitro Yellow', '#EAB308'), ('Xám Turbulence Grey', '#4B5563'), ('Đen Nocturnal', '#14161A')],
    },
    {
        'brand': 'Ford', 'name': 'Ford Mustang GT', 'slug': 'ford-mustang-gt',
        'query_3d': 'Ford Mustang', 'wiki_query': 'Ford Mustang',
        'year': 2023, 'price': 3450000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Tự động 8 cấp', 'seats': 4, 'featured': False,
        'description': 'Biểu tượng cơ bắp Mỹ trang bị động cơ Coyote V8 5.0L hút khí tự nhiên, hệ thống ống xả van chủ động và phanh Brembo hiệu năng cao.',
        'colors': [('Xanh Grabber Blue', '#2563EB'), ('Đỏ Race Red', '#DC2626'), ('Đen Shadow Black', '#121316'), ('Xám Dark Matter', '#374151')],
    },
    {
        'brand': 'Mazda', 'name': 'Mazda RX-7 FD3S', 'slug': 'mazda-rx-7-fd3s',
        'query_3d': 'Mazda RX7', 'wiki_query': 'Mazda RX-7',
        'year': 2002, 'price': 2850000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Số sàn 6 cấp', 'seats': 2, 'featured': False,
        'description': 'Tuyệt tác động cơ xoay Rotary 13B-REW tăng áp kép tuần tự với thiết kế thân xe khí động học vượt thời gian và trọng lượng siêu nhẹ.',
        'colors': [('Vàng Competition Yellow', '#F59E0B'), ('Đỏ Vintage Red', '#B91C1C'), ('Xanh Innocent Blue', '#1E40AF'), ('Đen Brilliant Black', '#141416')],
    },
    {
        'brand': 'Land Rover', 'name': 'Range Rover Autobiography', 'slug': 'range-rover-autobiography',
        'query_3d': 'Range Rover', 'wiki_query': 'Range Rover',
        'year': 2023, 'price': 11800000000, 'body_type': 'SUV', 'fuel_type': 'Hybrid',
        'transmission': 'Tự động 8 cấp', 'seats': 5, 'featured': False,
        'description': 'SUV hạng sang đầu bảng kết hợp hệ thống treo khí nén điện tử chủ động, dẫn động bốn bánh Terrain Response 2 và khoang nội thất thượng hạng.',
        'colors': [('Xanh British Racing Green', '#14532D'), ('Đen Santorini Black', '#141619'), ('Bạc Hakuba Silver', '#94A3B8'), ('Đồng Charente Grey', '#57534E')],
    },
    {
        'brand': 'Tesla', 'name': 'Tesla Model 3 Performance', 'slug': 'tesla-model-3-performance',
        'query_3d': 'Tesla Model 3', 'wiki_query': 'Tesla Model 3',
        'year': 2024, 'price': 2150000000, 'body_type': 'Sedan', 'fuel_type': 'Điện',
        'transmission': 'Tự động 1 cấp', 'seats': 5, 'featured': False,
        'description': 'Sedan thuần điện dẫn động hai mô-tơ Dual Motor AWD với khả năng tăng tốc 0–100 km/h trong 3,1 giây và hệ thống treo thích ứng.',
        'colors': [('Đỏ Ultra Red', '#B91C1C'), ('Trắng Pearl Multi-Coat', '#F8FAFC'), ('Xám Stealth Grey', '#334155'), ('Xanh Deep Blue', '#1E3A8A')],
    },
    {
        'brand': 'Volkswagen', 'name': 'Volkswagen Golf GTI', 'slug': 'volkswagen-golf-gti',
        'query_3d': 'Volkswagen Golf', 'wiki_query': 'Volkswagen Golf',
        'year': 2023, 'price': 1890000000, 'body_type': 'Touring', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 5, 'featured': False,
        'description': 'Chuẩn mực Hot Hatch châu Âu với động cơ 2.0L TSI tăng áp, hộp số ly hợp kép DSG và khóa vi sai cầu trước điều khiển điện tử VAQ.',
        'colors': [('Đỏ Kings Red', '#B91C1C'), ('Trắng Pure White', '#F1F5F9'), ('Xám Moonstone Grey', '#64748B'), ('Đen Deep Black', '#111317')],
    },
    {
        'brand': 'Subaru', 'name': 'Subaru WRX STI', 'slug': 'subaru-wrx-sti',
        'query_3d': 'Subaru Impreza WRX', 'wiki_query': 'Subaru Impreza WRX',
        'year': 2021, 'price': 2450000000, 'body_type': 'Sedan', 'fuel_type': 'Xăng',
        'transmission': 'Số sàn 6 cấp', 'seats': 5, 'featured': False,
        'description': 'Sedan thể thao thừa hưởng DNA đường đua WRC với động cơ Boxer tăng áp và hệ dẫn động bốn bánh đối xứng Symmetrical AWD.',
        'colors': [('Xanh World Rally Blue', '#1D4ED8'), ('Trắng Crystal White', '#F8FAFC'), ('Xám Magnetite Grey', '#475569'), ('Đỏ Pure Red', '#DC2626')],
    },
    {
        'brand': 'Honda', 'name': 'Honda Civic Type R', 'slug': 'honda-civic-type-r',
        'query_3d': 'Honda Civic', 'wiki_query': 'Honda Civic Type R',
        'year': 2023, 'price': 2399000000, 'body_type': 'Touring', 'fuel_type': 'Xăng',
        'transmission': 'Số sàn 6 cấp', 'seats': 4, 'featured': False,
        'description': 'Mẫu xe hiệu năng cao trang bị động cơ 2.0L VTEC Turbo 315 mã lực, hộp số sàn 6 cấp tích hợp Rev-Match và khí động học đường đua.',
        'colors': [('Trắng Championship White', '#F8FAFC'), ('Đỏ Rallye Red', '#DC2626'), ('Xanh Boost Blue', '#2563EB'), ('Đen Crystal Black', '#141619')],
    },
    {
        'brand': 'Mazda', 'name': 'Mazda MX-5 Miata Roadster', 'slug': 'mazda-mx-5-roadster',
        'query_3d': 'Mazda MX5 Miata', 'wiki_query': 'Mazda MX-5',
        'year': 2023, 'price': 1650000000, 'body_type': 'Roadster', 'fuel_type': 'Xăng',
        'transmission': 'Số sàn 6 cấp', 'seats': 2, 'featured': False,
        'description': 'Roadster hai chỗ mui trần thuần khiết theo triết lý Jinba Ittai — nhân mã hợp nhất, trọng lượng nhẹ chỉ hơn 1 tấn và dẫn động cầu sau.',
        'colors': [('Đỏ Soul Red Crystal', '#991B1B'), ('Xám Machine Grey', '#4B5563'), ('Trắng Snowflake White', '#F1F5F9'), ('Đen Jet Black', '#141619')],
    },
    {
        'brand': 'Mercedes-Benz', 'name': 'Mercedes-AMG G 63', 'slug': 'mercedes-amg-g63',
        'query_3d': 'Mercedes G63 AMG', 'wiki_query': 'Mercedes-Benz G-Class',
        'year': 2023, 'price': 11750000000, 'body_type': 'SUV', 'fuel_type': 'Xăng',
        'transmission': 'Tự động 8 cấp', 'seats': 5, 'featured': False,
        'description': 'SUV địa hình hạng sang biểu tượng với khung gầm rời, ba khóa vi sai 100% và động cơ V8 4.0L Biturbo 585 mã lực.',
        'colors': [('Đen Night Black Magno', '#141619'), ('Trắng Polar White', '#F8FAFC'), ('Xanh Emerald Green', '#064E3B'), ('Xám Monza Grey', '#52525B')],
    },
    {
        'brand': 'Chevrolet', 'name': 'Chevrolet Corvette Stingray', 'slug': 'chevrolet-corvette-stingray',
        'query_3d': 'Chevrolet Corvette', 'wiki_query': 'Chevrolet Corvette',
        'year': 2023, 'price': 6200000000, 'body_type': 'Roadster', 'fuel_type': 'Xăng',
        'transmission': 'Ly hợp kép 7 cấp', 'seats': 2, 'featured': False,
        'description': 'Siêu xe Mỹ động cơ V8 6.2L LT2 hút khí tự nhiên đặt giữa với thiết kế mui xếp cứng thể thao và khả năng bứt tốc 0–100 km/h trong 2,9 giây.',
        'colors': [('Đỏ Torch Red', '#DC2626'), ('Xanh Rapid Blue', '#2563EB'), ('Vàng Accelerate Yellow', '#EAB308'), ('Đen Carbon Flash', '#141619')],
    },
    {
        'brand': 'Ferrari', 'name': 'Ferrari F40', 'slug': 'ferrari-f40',
        'query_3d': 'Ferrari F40', 'wiki_query': 'Ferrari F40',
        'year': 1992, 'price': 32000000000, 'body_type': 'Coupe', 'fuel_type': 'Xăng',
        'transmission': 'Số sàn 6 cấp', 'seats': 2, 'featured': False,
        'description': 'Huyền thoại Maranello kỷ niệm 40 năm Ferrari với thân vỏ Kevlar/sợi carbon và động cơ V8 2.9L tăng áp kép thuần cơ khí.',
        'colors': [('Đỏ Rosso Corsa', '#D40000'), ('Vàng Giallo Modena', '#F5C400'), ('Đen Nero', '#141619')],
    },
]


def _hamming_distance(h1: str, h2: str) -> int:
    return bin(int(h1, 16) ^ int(h2, 16)).count('1')


def _request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    retries: int = 3,
) -> requests.Response | None:
    merged = {'User-Agent': USER_AGENT}
    if headers:
        merged.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.request(method, url, headers=merged, params=params, timeout=timeout)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f'  [RateLimit] 429 from {url}, sleeping {wait}s...')
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                time.sleep(1.5 * (attempt + 1))
                continue
            return resp
        except requests.RequestException as exc:
            if attempt == retries - 1:
                print(f'  [NetError] {url}: {exc}')
            time.sleep(1.5 * (attempt + 1))
    return None


def _log_fetch(car_slug: str | None, asset_type: str, source_name: str, query: str, status: str, message: str) -> None:
    db.session.add(AssetFetchLog(
        car_slug=car_slug,
        asset_type=asset_type,
        source_name=source_name,
        query=(query or '')[:250],
        status=status,
        message=(message or '')[:1000],
    ))
    db.session.commit()


def _ensure_brand_logo(brand_name: str) -> str:
    BRANDS_IMG_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', brand_name.lower()).strip('-')
    out = BRANDS_IMG_DIR / f'{slug}.svg'
    if not out.exists():
        initials = ''.join(w[0].upper() for w in brand_name.split()[:2]) or 'SV'
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" fill="none">
  <rect width="64" height="64" rx="14" fill="#13161d"/>
  <circle cx="32" cy="32" r="22" stroke="#e07a2b" stroke-width="2"/>
  <text x="32" y="37" text-anchor="middle" fill="#f4f5f7" font-family="sans-serif" font-size="15" font-weight="700">{initials}</text>
</svg>'''
        out.write_text(svg, encoding='utf-8')
    return f'/static/img/brands/{slug}.svg'


def _clean_html(raw: str) -> str:
    if not raw:
        return ''
    text = re.sub(r'<[^>]+>', ' ', raw)
    return ' '.join(text.split()).strip()


def _normalize_commons_license(raw_lic: str) -> tuple[str, str] | None:
    low = (raw_lic or '').strip().lower()
    if not low:
        return None
    if 'cc0' in low or 'cc-zero' in low:
        return ALLOWED_COMMONS_LICENSES['cc0']
    if 'public domain' in low or low == 'pd':
        return ALLOWED_COMMONS_LICENSES['public domain']
    if 'cc-by-sa' in low or 'cc by-sa' in low:
        return ALLOWED_COMMONS_LICENSES['cc-by-sa']
    if 'cc-by' in low or 'cc by' in low:
        return ALLOWED_COMMONS_LICENSES['cc-by']
    return None


class CatalogBuilder:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.sketchfab_token = os.environ.get('SKETCHFAB_TOKEN', '').strip()
        self.pexels_key = os.environ.get('PEXELS_API_KEY', '').strip()
        self.unsplash_key = os.environ.get('UNSPLASH_ACCESS_KEY', '').strip()
        self.store_blob = os.environ.get('STORE_IMAGES_IN_DB', 'false').lower() in ('1', 'true', 'yes')

        self.used_model_uids: set[str] = set()
        self.used_model_sha256: set[str] = set()
        self.used_img_source_ids: set[str] = set()
        self.used_img_sha256: set[str] = set()
        self.used_img_phashes: list[str] = []

        self.rejected_models: list[str] = []
        self.rejected_images: list[str] = []

        if not self.sketchfab_token:
            print('[CRITICAL WARN] SKETCHFAB_TOKEN chưa được thiết lập trong .env!')
            print('  Hướng dẫn: Đăng nhập https://sketchfab.com -> Settings -> Password & API -> copy API Token vào .env')
        if not self.pexels_key:
            print('[WARN] PEXELS_API_KEY trống -> bỏ qua nguồn Pexels, ưu tiên Wikimedia Commons.')
        if not self.unsplash_key:
            print('[WARN] UNSPLASH_ACCESS_KEY trống -> bỏ qua nguồn Unsplash, ưu tiên Wikimedia Commons.')

    def audit_and_remove_ferrari_glb(self) -> None:
        ferrari_path = MODELS_DIR / 'ferrari.glb'
        if not ferrari_path.exists():
            return
        try:
            info = inspect_glb(ferrari_path)
            asset_meta = info.get('asset', {})
        except Exception:
            asset_meta = {}

        has_license = bool(asset_meta.get('copyright') or (asset_meta.get('extras') or {}).get('license'))
        if not has_license:
            msg = (
                f"Loại bỏ ferrari.glb: header asset={asset_meta} không chứa copyright/license; "
                "URL gốc Sketchfab 57bf6cc56931426e87494f554df1dab6 đã 404 (MIT của repo three.js chỉ áp dụng cho mã nguồn)."
            )
            print(f'[AUDIT] {msg}')
            if not self.args.dry_run:
                ferrari_path.unlink(missing_ok=True)
                _log_fetch(None, 'model', 'mrdoob/three.js', 'ferrari.glb', 'rejected', msg)

    def find_and_download_sketchfab_model(self, cand: dict[str, Any]) -> dict[str, Any] | None:
        slug = cand['slug']
        existing_glb = MODELS_DIR / f'{slug}.glb'

        if self.args.resume and existing_glb.exists():
            ok, reason, info = validate_car_glb(existing_glb, min_Input_polys=20000)
            if ok:
                raw = existing_glb.read_bytes()
                sha = hashlib.sha256(raw).hexdigest()
                if sha not in self.used_model_sha256:
                    self.used_model_sha256.add(sha)
                    db_m = CarModel.query.filter_by(file_path=f'/static/models/{slug}.glb').first()
                    return {
                        'file_path': f'/static/models/{slug}.glb',
                        'file_size': len(raw),
                        'sha256': sha,
                        'poly_count': info['poly_count'],
                        'source_name': 'Sketchfab',
                        'source_url': db_m.source_url if db_m else f'https://sketchfab.com/search?q={cand["query_3d"]}',
                        'author': db_m.author if db_m else 'Sketchfab Creator',
                        'license': db_m.license if db_m else 'CC BY 4.0',
                        'license_url': db_m.license_url if db_m else 'https://creativecommons.org/licenses/by/4.0/',
                        'body_material_names': info['body_material_names'],
                        'body_detection_method': info['body_detection_method'],
                    }

        if not self.sketchfab_token:
            return None

        headers = {'Authorization': f'Token {self.sketchfab_token}'}
        resp = _request_with_retry(
            'GET',
            'https://api.sketchfab.com/v3/search',
            headers=headers,
            params={
                'type': 'models',
                'q': cand['query_3d'],
                'downloadable': 'true',
                'archives_flavours': 'false',
                'count': 24,
            },
        )
        time.sleep(0.35)
        if not resp or resp.status_code != 200:
            return None

        results = resp.json().get('results', [])
        for item in results:
            uid = item.get('uid')
            name = item.get('name') or ''
            if not uid or uid in self.used_model_uids:
                continue

            tags_str = ' '.join((t.get('name') or '') for t in (item.get('tags') or []))
            combined_text = f'{name} {tags_str}'.lower()

            # 1. Realism text filter
            bad_kw = next((kw for kw in REJECT_3D_KEYWORDS if kw in combined_text), None)
            if bad_kw:
                reason = f"{slug}: loại '{name}' ({uid}) vì chứa từ khóa '{bad_kw}'"
                self.rejected_models.append(reason)
                if not self.args.dry_run:
                    _log_fetch(slug, 'model', 'Sketchfab', cand['query_3d'], 'rejected', reason)
                continue

            # 2. Face/triangle count check (30,000 <= poly_count <= 500,000)
            faces = item.get('faceCount') or 0
            if not (30000 <= faces <= 500000):
                reason = f"{slug}: loại '{name}' ({uid}) vì poly_count={faces:,} nằm ngoài [30k..500k]"
                self.rejected_models.append(reason)
                if not self.args.dry_run:
                    _log_fetch(slug, 'model', 'Sketchfab', cand['query_3d'], 'rejected', reason)
                continue

            # 3. Check GLB archive size <= 40MB
            glb_archive = (item.get('archives') or {}).get('glb') or {}
            glb_size = glb_archive.get('size') or 0
            if glb_size <= 0 or glb_size > 40 * 1024 * 1024:
                reason = f"{slug}: loại '{name}' ({uid}) vì dung lượng GLB {glb_size / 1048576:.1f}MB (> 40MB hoặc không có GLB)"
                self.rejected_models.append(reason)
                continue

            # 4. Fetch full model detail to verify license (CC0 / CC-BY / CC-BY-SA)
            detail_resp = _request_with_retry('GET', f'https://api.sketchfab.com/v3/models/{uid}', headers=headers)
            time.sleep(0.25)
            if not detail_resp or detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            lic_obj = detail.get('license') or {}
            lic_slug = (lic_obj.get('slug') or '').lower()
            if lic_slug not in ALLOWED_SKETCHFAB_LICENSES:
                reason = f"{slug}: loại '{name}' ({uid}) vì license='{lic_slug}' không thuộc CC0/CC-BY/CC-BY-SA"
                self.rejected_models.append(reason)
                if not self.args.dry_run:
                    _log_fetch(slug, 'model', 'Sketchfab', cand['query_3d'], 'rejected', reason)
                continue

            lic_label, lic_url = ALLOWED_SKETCHFAB_LICENSES[lic_slug]
            author = (detail.get('user') or {}).get('displayName') or (detail.get('user') or {}).get('username') or 'Sketchfab Creator'
            source_url = detail.get('viewerUrl') or f'https://sketchfab.com/3d-models/{uid}'

            if self.args.dry_run:
                print(f"  [DRY-RUN] Sẽ tải model '{name}' ({faces:,} faces, {glb_size/1048576:.1f}MB, {lic_label}) cho {slug}")
                self.used_model_uids.add(uid)
                return {
                    'file_path': f'/static/models/{slug}.glb',
                    'file_size': glb_size,
                    'sha256': uid,
                    'poly_count': faces,
                    'source_name': 'Sketchfab',
                    'source_url': source_url,
                    'author': author,
                    'license': lic_label,
                    'license_url': lic_url,
                    'body_material_names': ['Body'],
                    'body_detection_method': 'dry_run',
                }

            # 5. Request temporary download URL & download .glb
            dl_meta_resp = _request_with_retry('GET', f'https://api.sketchfab.com/v3/models/{uid}/download', headers=headers)
            time.sleep(0.3)
            if not dl_meta_resp or dl_meta_resp.status_code != 200:
                continue
            glb_dl_info = (dl_meta_resp.json().get('glb') or {})
            dl_url = glb_dl_info.get('url')
            if not dl_url:
                continue

            print(f"  -> Đang tải GLB '{name}' ({faces:,} tris, {glb_size/1048576:.1f}MB, {lic_label}) cho {slug}...")
            dl_resp = _request_with_retry('GET', dl_url, timeout=90)
            if not dl_resp or dl_resp.status_code != 200 or not dl_resp.content:
                continue

            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            tmp_glb = MODELS_DIR / f'{slug}.tmp.glb'
            tmp_glb.write_bytes(dl_resp.content)

            # 6. Validate GLB magic bytes, materials >= 3, bounding box proportions
            ok, v_reason, info = validate_car_glb(tmp_glb, min_Input_polys=20000)
            if not ok:
                tmp_glb.unlink(missing_ok=True)
                reason = f"{slug}: loại '{name}' ({uid}) sau kiểm định GLB -> {v_reason}"
                print(f'     [REJECT] {reason}')
                self.rejected_models.append(reason)
                _log_fetch(slug, 'model', 'Sketchfab', cand['query_3d'], 'rejected', reason)
                continue

            sha = hashlib.sha256(dl_resp.content).hexdigest()
            if sha in self.used_model_sha256:
                tmp_glb.unlink(missing_ok=True)
                continue

            final_glb = MODELS_DIR / f'{slug}.glb'
            tmp_glb.replace(final_glb)
            self.used_model_uids.add(uid)
            self.used_model_sha256.add(sha)

            actual_polys = info['poly_count'] or faces
            _log_fetch(
                slug, 'model', 'Sketchfab', cand['query_3d'], 'downloaded',
                f"Downloaded {name} ({uid}), polys={actual_polys}, mats={info['material_count']}, body={info['body_material_names']} ({info['body_detection_method']})"
            )
            print(f"     [OK] {final_glb.name}: {actual_polys:,} tris, L/W={info['lw_ratio']}, body_mats={info['body_material_names']}")
            return {
                'file_path': f'/static/models/{slug}.glb',
                'file_size': len(dl_resp.content),
                'sha256': sha,
                'poly_count': actual_polys,
                'source_name': 'Sketchfab',
                'source_url': source_url,
                'author': author[:155],
                'license': lic_label,
                'license_url': lic_url,
                'body_material_names': info['body_material_names'],
                'body_detection_method': info['body_detection_method'],
            }

        return None

    def _parse_wikimedia_pages(self, pages: dict[str, Any], min_width: int, match_level: str, shot_type: str) -> list[dict[str, Any]]:
        out = []
        for page_id, page in pages.items():
            sid = f'Wikimedia Commons:{page_id}'
            if sid in self.used_img_source_ids:
                continue
            infos = page.get('imageinfo') or []
            if not infos:
                continue
            info = infos[0]
            w, h = info.get('width') or 0, info.get('height') or 0
            if w < min_width or w <= h:
                continue
            url = (info.get('thumburl') if w > 2400 and info.get('thumburl') else info.get('url')) or ''
            clean_url_path = url.split('?')[0].lower()
            if not clean_url_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            meta = info.get('extmetadata') or {}
            raw_lic = (meta.get('LicenseShortName') or {}).get('value', '')
            parsed_lic = _normalize_commons_license(raw_lic)
            if not parsed_lic:
                self.rejected_images.append(f"Wikimedia:{page.get('title')} (license='{raw_lic}')")
                continue
            desc = _clean_html((meta.get('ImageDescription') or {}).get('value', '')) + ' ' + (page.get('title') or '')
            m_bad = REJECT_IMG_REGEX.search(desc)
            if m_bad:
                self.rejected_images.append(f"Wikimedia:{page.get('title')} (keyword='{m_bad.group(0)}')")
                continue
            author = _clean_html((meta.get('Artist') or {}).get('value', '')) or 'Wikimedia Contributor'
            out.append({
                'source_name': 'Wikimedia Commons',
                'source_id': str(page_id),
                'download_url': url,
                'source_url': info.get('descriptionurl') or url,
                'author': author[:155],
                'license': parsed_lic[0],
                'license_url': parsed_lic[1],
                'shot_type': shot_type,
                'match_level': match_level,
                'caption': desc[:240],
            })
        return out

    def _search_wikimedia_category(self, category_name: str, min_width: int, match_level: str, shot_type: str, limit: int = 45) -> list[dict[str, Any]]:
        cat_title = category_name if category_name.startswith('Category:') else f'Category:{category_name}'
        resp = _request_with_retry(
            'GET',
            'https://commons.wikimedia.org/w/api.php',
            params={
                'action': 'query',
                'format': 'json',
                'generator': 'categorymembers',
                'gcmtitle': cat_title,
                'gcmtype': 'file',
                'gcmlimit': limit,
                'prop': 'imageinfo',
                'iiprop': 'url|size|extmetadata',
                'iiurlwidth': 2400,
            },
        )
        time.sleep(0.2)
        if not resp or resp.status_code != 200:
            return []
        pages = (resp.json().get('query') or {}).get('pages') or {}
        return self._parse_wikimedia_pages(pages, min_width, match_level, shot_type)

    def _search_wikimedia(self, query: str, min_width: int, match_level: str, shot_type: str, limit: int = 30) -> list[dict[str, Any]]:
        resp = _request_with_retry(
            'GET',
            'https://commons.wikimedia.org/w/api.php',
            params={
                'action': 'query',
                'format': 'json',
                'generator': 'search',
                'gsrnamespace': 6,
                'gsrsearch': f'{query} filetype:bitmap',
                'gsrlimit': limit,
                'prop': 'imageinfo',
                'iiprop': 'url|size|extmetadata',
                'iiurlwidth': 2400,
            },
        )
        time.sleep(0.2)
        if not resp or resp.status_code != 200:
            return []
        pages = (resp.json().get('query') or {}).get('pages') or {}
        return self._parse_wikimedia_pages(pages, min_width, match_level, shot_type)

    def _search_openverse(self, query: str, min_width: int, match_level: str, shot_type: str) -> list[dict[str, Any]]:
        resp = _request_with_retry(
            'GET',
            'https://api.openverse.org/v1/images/',
            params={'q': query, 'license': 'cc0,pdm,by', 'aspect_ratio': 'wide', 'page_size': 15},
        )
        time.sleep(0.3)
        if not resp or resp.status_code != 200:
            return []
        out = []
        for p in resp.json().get('results', []):
            sid = f"Openverse:{p.get('id')}"
            if sid in self.used_img_source_ids:
                continue
            w, h = p.get('width') or 0, p.get('height') or 0
            if w < min_width or w <= h:
                continue
            title = f"{p.get('title') or ''} {' '.join((t.get('name') or '') for t in (p.get('tags') or []))}"
            if REJECT_IMG_REGEX.search(title):
                continue
            lic_code = (p.get('license') or 'by').upper()
            out.append({
                'source_name': 'Openverse',
                'source_id': str(p['id']),
                'download_url': p.get('url'),
                'source_url': p.get('foreign_landing_url') or p.get('url', ''),
                'author': (p.get('creator') or 'Openverse Contributor')[:155],
                'license': f'CC {lic_code}' if lic_code in ('BY', 'BY-SA') else lic_code,
                'license_url': p.get('license_url') or 'https://creativecommons.org/licenses/by/4.0/',
                'shot_type': shot_type,
                'match_level': match_level,
                'caption': (p.get('title') or '')[:240],
            })
        return out

    def fetch_images_for_car(self, car: Car, wiki_query: str, brand_name: str, body_type: str) -> list[dict[str, Any]]:
        car_dir = CARS_IMG_DIR / car.slug
        if self.args.resume and len(car.active_images) >= 5:
            for img in car.active_images:
                if img.sha256:
                    self.used_img_sha256.add(img.sha256)
                if img.phash:
                    self.used_img_phashes.append(img.phash)
            print(f'  [Resume] {car.slug} đã có {len(car.active_images)} ảnh hợp lệ.')
            return []

        if self.args.dry_run:
            print(f'  [DRY-RUN] Sẽ tìm 6-7 ảnh (Category:{wiki_query} + góc chụp đa dạng) cho {car.slug}')
            return []

        existing_imgs = list(car.active_images)
        if self.args.resume and existing_imgs:
            for img in existing_imgs:
                if img.sha256:
                    self.used_img_sha256.add(img.sha256)
                if img.phash:
                    self.used_img_phashes.append(img.phash)
                if img.source_name and img.source_id:
                    self.used_img_source_ids.add(f'{img.source_name}:{img.source_id}')
        else:
            CarImage.query.filter_by(car_id=car.id).delete(synchronize_session=False)
            db.session.flush()
            existing_imgs = []

        # Pre-fetch exact category pool from Wikimedia Commons Category:<wiki_query>
        cat_pool = self._search_wikimedia_category(wiki_query, 1600, 'exact', 'exterior', limit=45)

        shot_plan = [
            ('hero', 'hero', True, 2000, [
                (f'{wiki_query} front', 'exact'),
                (f'{wiki_query}', 'exact'),
                (f'{brand_name} {body_type}', 'similar'),
            ]),
            ('exterior-1', 'exterior', False, 1600, [
                (f'{wiki_query} rear', 'exact'),
                (f'{wiki_query} back', 'exact'),
                (f'{wiki_query}', 'exact'),
            ]),
            ('exterior-2', 'exterior', False, 1600, [
                (f'{wiki_query} side', 'exact'),
                (f'{wiki_query}', 'exact'),
            ]),
            ('exterior-3', 'exterior', False, 1600, [
                (f'{wiki_query} coupe', 'exact'),
                (f'{wiki_query} sedan', 'exact'),
                (f'{wiki_query}', 'exact'),
            ]),
            ('interior', 'interior', False, 1600, [
                (f'{wiki_query} interior', 'exact'),
                (f'{brand_name} interior', 'similar'),
                (f'{wiki_query}', 'exact'),
            ]),
            ('wheel', 'wheel', False, 1600, [
                (f'{wiki_query} wheel', 'exact'),
                (f'{wiki_query} headlight', 'exact'),
                (f'{wiki_query}', 'exact'),
            ]),
            ('detail', 'detail', False, 1600, [
                (f'{wiki_query} engine', 'exact'),
                (f'{wiki_query}', 'exact'),
                (f'{brand_name} {body_type}', 'similar'),
            ]),
        ]

        saved_records: list[dict[str, Any]] = [{'local_path': img.image_url} for img in existing_imgs]
        existing_stems = {Path(img.image_url).stem for img in existing_imgs}
        sort_idx = len(existing_imgs)

        for stem, shot_type, is_hero, min_w, queries in shot_plan:
            if stem in existing_stems or (is_hero and any(img.is_hero for img in existing_imgs)):
                continue
            secured = False
            # 1. Try specific angle/shot queries first for diversity
            for q_str, m_level in queries:
                candidates = self._search_wikimedia(q_str, min_w, m_level, shot_type)
                if not candidates:
                    candidates = self._search_openverse(q_str, min_w, m_level, shot_type)
                for cand in candidates:
                    rec = self._download_and_verify_image(car, car_dir, stem, cand, is_hero, min_w, sort_idx)
                    if rec:
                        saved_records.append(rec)
                        sort_idx += 1
                        secured = True
                        break
                if secured:
                    break

            # 2. Fallback to exact Wikimedia Category:<wiki_query> pool
            if not secured:
                for cand in list(cat_pool):
                    sid = f"{cand['source_name']}:{cand['source_id']}"
                    if sid in self.used_img_source_ids:
                        continue
                    cand_copy = dict(cand, shot_type=shot_type)
                    rec = self._download_and_verify_image(car, car_dir, stem, cand_copy, is_hero, min_w, sort_idx)
                    if rec:
                        saved_records.append(rec)
                        sort_idx += 1
                        break

        # 3. Backfill if < 6 images secured so every car always has >= 6 images
        if len(saved_records) < 6:
            backfill_queries = [
                (f'{wiki_query} car', 'exact'),
                (f'{brand_name} {wiki_query}', 'exact'),
                (f'Land Rover {wiki_query}' if 'Range Rover' in wiki_query else f'{wiki_query} automobile', 'exact'),
                (f'{brand_name} {body_type}', 'similar'),
                (f'{brand_name} automobile', 'similar'),
            ]
            pool: list[dict[str, Any]] = []
            for bq, ml in backfill_queries:
                pool.extend(self._search_wikimedia(bq, 1600, ml, 'exterior', limit=45))
                if len(pool) >= 25:
                    break
            for cand in pool:
                if len(saved_records) >= 6:
                    break
                is_first = (len(saved_records) == 0)
                stem = 'hero' if is_first else f'extra-{len(saved_records)}'
                rec = self._download_and_verify_image(car, car_dir, stem, cand, is_first, 1600, sort_idx)
                if rec:
                    saved_records.append(rec)
                    sort_idx += 1

        return saved_records

    def _download_and_verify_image(
        self,
        car: Car,
        car_dir: Path,
        stem: str,
        cand: dict[str, Any],
        is_hero: bool,
        min_w: int,
        sort_order: int,
    ) -> dict[str, Any] | None:
        sid = f"{cand['source_name']}:{cand['source_id']}"
        if sid in self.used_img_source_ids:
            return None

        time.sleep(0.8)
        resp = _request_with_retry('GET', cand['download_url'], timeout=35)
        if not resp or resp.status_code != 200 or not resp.content:
            return None
        self.used_img_source_ids.add(sid)

        raw_sha = hashlib.sha256(resp.content).hexdigest()
        if raw_sha in self.used_img_sha256:
            self.rejected_images.append(f"{car.slug}:{stem} trùng sha256 ({cand['source_id']})")
            return None

        try:
            with Image.open(io.BytesIO(resp.content)) as im:
                im.verify()
            with Image.open(io.BytesIO(resp.content)) as im:
                rgb = im.convert('RGB')
                w, h = rgb.size
                if w < min_w or w <= h:
                    return None
                blur_var = compute_laplacian_variance(rgb)
                if blur_var < 18.0:
                    reason = f"{car.slug}:{stem} ảnh bị mờ (Laplacian variance={blur_var:.1f} < 18.0)"
                    self.rejected_images.append(reason)
                    _log_fetch(car.slug, 'image', cand['source_name'], cand['download_url'], 'rejected', reason)
                    return None
                phash = compute_dhash(rgb)
        except Exception as exc:
            self.rejected_images.append(f"{car.slug}:{stem} lỗi Pillow ({exc})")
            return None

        if any(_hamming_distance(phash, existing) <= 4 for existing in self.used_img_phashes):
            self.rejected_images.append(f"{car.slug}:{stem} trùng perceptual hash ({phash})")
            return None

        car_dir.mkdir(parents=True, exist_ok=True)
        raw_tmp = car_dir / f'{stem}.raw'
        raw_tmp.write_bytes(resp.content)
        try:
            opt = optimize_image(raw_tmp, car_dir, stem, return_thumb_bytes=self.store_blob)
        finally:
            raw_tmp.unlink(missing_ok=True)

        self.used_img_sha256.add(raw_sha)
        self.used_img_phashes.append(phash)

        web_url = f"/static/img/cars/{car.slug}/{opt['webp']}"
        if is_hero:
            car.thumbnail = f"/static/img/cars/{car.slug}/{opt['thumb']}"

        img_row = CarImage(
            car_id=car.id,
            image_url=web_url,
            license=cand['license'],
            author=cand['author'],
            source_url=cand['source_url'],
            sha256=raw_sha,
            phash=phash,
            width=w,
            height=h,
            file_size=opt['file_size'],
            is_hero=is_hero,
            is_active=True,
            sort_order=sort_order,
            shot_type=cand['shot_type'],
            caption=cand.get('caption'),
            match_level=cand['match_level'],
            source_name=cand['source_name'],
            source_id=cand['source_id'],
            image_blob=opt['thumb_bytes'] if self.store_blob else None,
        )
        db.session.add(img_row)
        db.session.commit()

        _log_fetch(
            car.slug, 'image', cand['source_name'], cand['shot_type'], 'downloaded',
            f"{web_url} ({w}x{h}, blur={opt['blur_variance']}, match={cand['match_level']}, lic={cand['license']})"
        )
        return {
            'local_path': web_url,
            'sha256': raw_sha,
            'phash': phash,
            'width': w,
            'height': h,
            'shot_type': cand['shot_type'],
            'match_level': cand['match_level'],
            'source_name': cand['source_name'],
            'source_id': cand['source_id'],
            'source_url': cand['source_url'],
            'author': cand['author'],
            'license': cand['license'],
            'license_url': cand['license_url'],
            'downloaded_at': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        }

    def sync_assets_json(self) -> None:
        if self.args.dry_run:
            return
        hdris = []
        if ASSETS_JSON_PATH.exists():
            try:
                old = json.loads(ASSETS_JSON_PATH.read_text(encoding='utf-8'))
                hdris = old.get('hdris', [])
            except Exception:
                pass

        if not hdris:
            for hfile in sorted(HDRI_DIR.glob('*.hdr')):
                hid = hfile.stem.replace('_2k', '')
                hdris.append({
                    'local_path': f'/static/hdri/{hfile.name}',
                    'source_id': hid,
                    'source_name': 'Poly Haven',
                    'source_url': f'https://polyhaven.com/a/{hid}',
                    'author': 'Poly Haven',
                    'license': 'CC0 1.0',
                    'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
                    'downloaded_at': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                })

        models_list = [
            {
                'local_path': m.file_path,
                'car_slug': m.car.slug if m.car else '',
                'poly_count': m.poly_count,
                'file_size': m.file_size,
                'sha256': m.sha256,
                'source_name': m.source_name,
                'source_url': m.source_url,
                'author': m.author,
                'license': m.license,
                'license_url': m.license_url,
                'body_material_names': m.body_material_names,
                'downloaded_at': m.fetched_at.strftime('%Y-%m-%d') if m.fetched_at else '',
            }
            for m in CarModel.query.filter_by(is_active=True).order_by(CarModel.id.asc()).all()
        ]

        images_list = [
            {
                'local_path': img.image_url,
                'car_slug': img.car.slug if img.car else '',
                'shot_type': img.shot_type,
                'match_level': img.match_level,
                'width': img.width,
                'height': img.height,
                'sha256': img.sha256,
                'phash': img.phash,
                'source_name': img.source_name,
                'source_url': img.source_url,
                'author': img.author,
                'license': img.license,
                'downloaded_at': img.fetched_at.strftime('%Y-%m-%d') if img.fetched_at else '',
            }
            for img in CarImage.query.filter_by(is_active=True).order_by(CarImage.id.asc()).all()
        ]

        payload = {
            'models': models_list,
            'images': images_list,
            'videos': [],
            'hdris': hdris,
        }
        ASSETS_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def verify_catalog() -> int:
    app = create_app()
    errors: list[str] = []
    with app.app_context():
        cars = Car.query.order_by(Car.id.asc()).all()
        if not cars:
            print('[FAIL] Không có xe nào trong cơ sở dữ liệu.')
            return 1

        print('\n' + '=' * 118)
        print(f"{'SLUG XE':<28} | {'MODEL 3D (.GLB)':<28} | {'TRIS / SIZE':<18} | {'LICENSE MODEL':<14} | {'ẢNH (EXACT/SIM)'}")
        print('-' * 118)

        for car in cars:
            am = car.active_model
            model_str = 'MISSING'
            tris_str = '0 / 0MB'
            lic_str = '—'

            if not am:
                errors.append(f'{car.slug}: thiếu bản ghi active trong car_models')
            else:
                disk_glb = STATIC_DIR / am.file_path.lstrip('/').replace('static/', '', 1)
                model_str = Path(am.file_path).name[:28]
                tris_str = f"{am.poly_count:,} / {am.file_size / 1048576:.1f}M"
                lic_str = am.license[:14]
                if not disk_glb.exists():
                    errors.append(f'{car.slug}: file model không tồn tại trên đĩa ({disk_glb})')
                else:
                    ok, reason, _ = validate_car_glb(disk_glb, min_Input_polys=20000)
                    if not ok:
                        errors.append(f'{car.slug}: file .glb không đạt chuẩn ({reason})')
                if not am.author or not am.license or not am.source_url:
                    errors.append(f'{car.slug}: model 3D thiếu author/license/source_url')

            imgs = car.active_images
            exact_cnt = sum(1 for i in imgs if i.match_level == 'exact')
            sim_cnt = sum(1 for i in imgs if i.match_level != 'exact')
            img_summary = f'{len(imgs)} ({exact_cnt} exact / {sim_cnt} sim)'

            if len(imgs) < 5:
                errors.append(f'{car.slug}: chỉ có {len(imgs)} ảnh (< 5 ảnh tối thiểu)')

            for img in imgs:
                disk_img = STATIC_DIR / img.image_url.lstrip('/').replace('static/', '', 1)
                if not disk_img.exists():
                    errors.append(f'{car.slug}: thiếu file ảnh trên đĩa ({img.image_url})')
                if not img.author or not img.license or not img.source_url:
                    errors.append(f'{car.slug}: ảnh {img.image_url} thiếu author/license/source_url')

            print(f'{car.slug:<28} | {model_str:<28} | {tris_str:<18} | {lic_str:<14} | {img_summary}')

        print('=' * 118)

    if errors:
        print(f'\n[FAIL] Phát hiện {len(errors)} lỗi khi kiểm tra catalog:')
        for e in errors:
            print('  -', e)
        return 1

    print('\n[OK] XÁC NHẬN ĐẠT CHUẨN: Mọi xe đều có model .glb thật mở được + >= 5 ảnh chụp thật + đầy đủ tác giả & giấy phép!')
    return 0


def run_build(args: argparse.Namespace) -> int:
    if args.verify:
        return verify_catalog()

    app = create_app()
    with app.app_context():
        builder = CatalogBuilder(args)
        builder.audit_and_remove_ferrari_glb()

        target_count = args.cars
        existing_cars = Car.query.order_by(Car.id.asc()).all()

        # Filter candidates if --car <slug> specified
        candidates = REAL_CAR_CANDIDATES
        if args.car:
            candidates = [c for c in REAL_CAR_CANDIDATES if c['slug'] == args.car]
            if not candidates:
                print(f"[ERR] Không tìm thấy cấu hình ứng viên cho slug '{args.car}'.")
                return 1
            target_count = len(candidates)

        secured_cars: list[tuple[Car, dict[str, Any], dict[str, Any] | None]] = []

        # Step 1 & 2: Find real 3D model first, then upsert Brand & Car
        for cand in candidates:
            if len(secured_cars) >= target_count:
                break

            model_meta = None
            if not args.only_images:
                print(f"\n[1/2] Tìm model 3D tả thực cho {cand['name']} ({cand['body_type']})...")
                model_meta = builder.find_and_download_sketchfab_model(cand)
                if not model_meta:
                    print(f"  [SKIP] Không tìm được model .glb đạt chuẩn cho {cand['name']}, chuyển sang mẫu xe thật tiếp theo.")
                    continue
            else:
                # --only-images: look up already migrated car
                car_obj = Car.query.filter_by(slug=cand['slug']).first()
                if not car_obj:
                    continue
                secured_cars.append((car_obj, cand, None))
                continue

            if args.dry_run:
                secured_cars.append((None, cand, model_meta))  # type: ignore[arg-type]
                continue

            # Upsert real Brand
            brand = Brand.query.filter_by(name=cand['brand']).first()
            if not brand:
                brand = Brand(name=cand['brand'], logo=_ensure_brand_logo(cand['brand']))
                db.session.add(brand)
                db.session.flush()

            # Upsert Car or reuse existing fictional slot (preserving foreign keys on orders/favorites/test_drives)
            car = Car.query.filter_by(slug=cand['slug']).first()
            if not car:
                slot_idx = len(secured_cars)
                if slot_idx < len(existing_cars) and existing_cars[slot_idx].slug not in [c['slug'] for c in REAL_CAR_CANDIDATES]:
                    car = existing_cars[slot_idx]
                    old_slug = car.slug
                    print(f"  [DB] Ánh xạ an toàn bản ghi xe #{car.id} ('{old_slug}' -> '{cand['slug']}') giữ nguyên khóa ngoại.")
                else:
                    car = Car(brand_id=brand.id, name=cand['name'], slug=cand['slug'], year=cand['year'],
                              price=cand['price'], fuel_type=cand['fuel_type'], transmission=cand['transmission'],
                              body_type=cand['body_type'], description=cand['description'], thumbnail='/static/img/brands/default.svg')
                    db.session.add(car)

            car.brand_id = brand.id
            car.name = cand['name']
            car.slug = cand['slug']
            car.year = cand['year']
            car.price = cand['price']
            car.fuel_type = cand['fuel_type']
            car.transmission = cand['transmission']
            car.body_type = cand['body_type']
            car.seats = cand['seats']
            car.is_featured = cand['featured']
            car.description = cand['description']
            car.model_url = model_meta['file_path']
            car.body_material_names = model_meta['body_material_names']
            car.model_scale = 1.0
            car.model_offset_y = 0.0
            db.session.flush()

            # Sync CarColors
            CarColor.query.filter_by(car_id=car.id).delete(synchronize_session=False)
            for cname, chex in cand['colors']:
                db.session.add(CarColor(car_id=car.id, color_name=cname, hex_code=chex))

            # Upsert CarModel row (single source of truth)
            for old_cm in car.models_3d:
                old_cm.is_active = False
            cm = CarModel.query.filter_by(car_id=car.id, sha256=model_meta['sha256']).first()
            if not cm:
                cm = CarModel(car_id=car.id, sha256=model_meta['sha256'], file_path=model_meta['file_path'],
                              source_name=model_meta['source_name'], source_url=model_meta['source_url'],
                              author=model_meta['author'], license=model_meta['license'])
                db.session.add(cm)
            cm.file_path = model_meta['file_path']
            cm.file_format = 'glb'
            cm.file_size = model_meta['file_size']
            cm.poly_count = model_meta['poly_count']
            cm.source_name = model_meta['source_name']
            cm.source_url = model_meta['source_url']
            cm.author = model_meta['author']
            cm.license = model_meta['license']
            cm.license_url = model_meta['license_url']
            cm.body_material_names = model_meta['body_material_names']
            cm.scale = 1.0
            cm.offset_y = 0.0
            cm.is_active = True
            db.session.commit()

            secured_cars.append((car, cand, model_meta))

        if not args.dry_run and not args.car and not args.only_images:
            # Remove any leftover fictional cars or empty fictional brands
            secured_ids = {c.id for c, _, _ in secured_cars if c}
            for leftover in Car.query.all():
                if leftover.id not in secured_ids:
                    db.session.delete(leftover)
            db.session.commit()
            for b in Brand.query.all():
                if not b.cars:
                    db.session.delete(b)
            db.session.commit()

        # Step 3: Fetch real matching photographs for each secured car
        if not args.only_models:
            for car, cand, _ in secured_cars:
                if args.dry_run:
                    builder.fetch_images_for_car(None, cand['wiki_query'], cand['brand'], cand['body_type'])  # type: ignore[arg-type]
                    continue
                print(f"\n[2/2] Tìm bộ ảnh chụp thật cho {car.name} ({car.slug})...")
                imgs = builder.fetch_images_for_car(car, cand['wiki_query'], cand['brand'], cand['body_type'])
                if imgs:
                    print(f"  [OK] Đã tải & tối ưu {len(imgs)} ảnh cho {car.name}.")

        builder.sync_assets_json()

        print('\n=== THỐNG KÊ BỘ LỌC KIỂM ĐỊNH ===')
        print(f'- Số xe hoàn tất: {len(secured_cars)}')
        print(f'- Số model 3D bị loại bởi bộ lọc: {len(builder.rejected_models)}')
        for rm in builder.rejected_models[:12]:
            print('   *', rm)
        print(f'- Số ảnh bị loại bởi bộ lọc (mờ/trùng/sai license/từ khóa): {len(builder.rejected_images)}')
        for ri in builder.rejected_images[:12]:
            print('   *', ri)

    if not args.dry_run and not args.only_models:
        return verify_catalog()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Build real-world car catalog with Sketchfab GLBs and real photos.')
    parser.add_argument('--cars', type=int, default=12, help='Target number of real cars (default: 12)')
    parser.add_argument('--dry-run', action='store_true', help='Query APIs and print plan without downloading or modifying DB')
    parser.add_argument('--only-models', action='store_true', help='Only fetch and validate 3D .glb models')
    parser.add_argument('--only-images', action='store_true', help='Only fetch and optimize real photographs')
    parser.add_argument('--resume', action='store_true', help='Skip assets already downloaded and verified in cache/DB')
    parser.add_argument('--car', type=str, default='', help='Process only a specific car slug')
    parser.add_argument('--verify', action='store_true', help='Verify all DB cars have valid .glb and >= 5 licensed images')
    args = parser.parse_args()
    return run_build(args)


if __name__ == '__main__':
    raise SystemExit(main())
