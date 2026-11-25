"""Dịch vụ gọi API tỷ giá ngoại tệ trực tuyến sử dụng urllib.request (CLO3)."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from flask import current_app

_RATE_CACHE: dict = {"data": None, "expires_at": 0.0}
_CACHE_TTL_SECONDS = 1800  # Lưu đệm 30 phút tránh gọi mạng lặp lại mỗi lượt tải trang


def clear_rate_cache() -> None:
    """Xóa bộ nhớ đệm tỷ giá (dùng trong kiểm thử pytest)."""
    _RATE_CACHE["data"] = None
    _RATE_CACHE["expires_at"] = 0.0


def get_exchange_rates(force_refresh: bool = False) -> dict:
    """Lấy tỷ giá USD/VND và EUR/VND qua urllib; hỗ trợ API key biến môi trường và fallback an toàn."""
    now = time.time()
    if not force_refresh and _RATE_CACHE["data"] and now < _RATE_CACHE["expires_at"]:
        return _RATE_CACHE["data"]

    api_key = current_app.config.get("EXCHANGE_API_KEY", "").strip()
    timeout = current_app.config.get("EXCHANGE_API_TIMEOUT", 5)
    fallback_usd = float(current_app.config.get("EXCHANGE_FALLBACK_USD_VND", 25450.0))
    fallback_eur = float(current_app.config.get("EXCHANGE_FALLBACK_EUR_VND", 27100.0))

    if api_key:
        endpoint = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
        provider_mode = "ExchangeRate-API (API Key)"
    else:
        endpoint = "https://open.er-api.com/v6/latest/USD"
        provider_mode = "ExchangeRate-API (Open Free)"

    try:
        req = Request(
            endpoint,
            headers={
                "User-Agent": "LuxAutoShowroom/1.0 (Flask CLO3 Network Client)",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8")
            payload = json.loads(raw_body)

        rates = payload.get("rates") or payload.get("conversion_rates") or {}
        usd_to_vnd = float(rates.get("VND", 0))
        usd_to_eur = float(rates.get("EUR", 0))
        if usd_to_vnd <= 0:
            raise ValueError("Dữ liệu JSON không chứa tỷ giá VND hợp lệ.")

        eur_to_vnd = round(usd_to_vnd / usd_to_eur, 2) if usd_to_eur > 0 else fallback_eur
        result = {
            "usd_to_vnd": round(usd_to_vnd, 2),
            "eur_to_vnd": eur_to_vnd,
            "source": "live",
            "provider": provider_mode,
            "updated_at": payload.get("time_last_update_utc", "Trực tuyến"),
        }
        _RATE_CACHE["data"] = result
        _RATE_CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
        return result

    except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
        current_app.logger.warning("Không thể kết nối API tỷ giá (%s), chuyển sang mức dự phòng.", exc)
        fallback_data = {
            "usd_to_vnd": fallback_usd,
            "eur_to_vnd": fallback_eur,
            "source": "fallback",
            "provider": "Tỷ giá tham chiếu nội bộ (Offline Fallback)",
            "updated_at": "Dự phòng ngoại tuyến",
        }
        # Cache ngắn 60 giây khi mất mạng để các trang tiếp theo phản hồi tức thì
        _RATE_CACHE["data"] = fallback_data
        _RATE_CACHE["expires_at"] = now + 60
        return fallback_data


def convert_vnd(amount_vnd: int | float, rates: dict | None = None) -> dict:
    """Quy đổi giá xe VNĐ sang USD và EUR dựa trên tỷ giá hiện hành."""
    rate_info = rates or get_exchange_rates()
    usd_rate = rate_info["usd_to_vnd"]
    eur_rate = rate_info["eur_to_vnd"]
    return {
        "vnd": int(amount_vnd or 0),
        "usd": round(float(amount_vnd or 0) / usd_rate, 2) if usd_rate else 0.0,
        "eur": round(float(amount_vnd or 0) / eur_rate, 2) if eur_rate else 0.0,
        "usd_to_vnd": usd_rate,
        "eur_to_vnd": eur_rate,
        "source": rate_info["source"],
    }
