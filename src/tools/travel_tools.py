import math
import os
import requests
from typing import Any
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
FOURSQUARE_API_KEY  = os.getenv("FOURSQUARE_API_KEY", "")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _get(url: str, params: dict = None, headers: dict = None) -> dict | list:
    """Gọi GET request, trả về JSON hoặc dict chứa 'error'."""
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError:
        return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Không thể kết nối. Kiểm tra lại mạng."}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timeout sau 10 giây."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _geocode(place: str) -> tuple[float, float] | None:
    """Dùng OpenWeatherMap Geocoding API để lấy tọa độ (miễn phí, cùng key)."""
    if not OPENWEATHER_API_KEY:
        return None
    data = _get(
        "http://api.openweathermap.org/geo/1.0/direct",
        params={"q": f"{place},VN", "limit": 1, "appid": OPENWEATHER_API_KEY},
    )
    if isinstance(data, list) and data:
        return data[0]["lat"], data[0]["lon"]
    return None


def _fsq_headers() -> dict:
    return {"Authorization": FOURSQUARE_API_KEY, "Accept": "application/json"}