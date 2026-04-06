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

# ---------------------------------------------------------------------------
# 1. Weather Tool — OpenWeatherMap Current Weather API
#    Docs: https://openweathermap.org/current
#    Free: 1,000 calls/ngày — không cần thẻ tín dụng
# ---------------------------------------------------------------------------

# Map tên thành phố tiếng Việt sang tên API hiểu được
_VN_CITY_MAP = {
    "đà nẵng": "Da Nang,VN", "hà nội": "Hanoi,VN",
    "hồ chí minh": "Ho Chi Minh City,VN", "hội an": "Hoi An,VN",
    "nha trang": "Nha Trang,VN", "phú quốc": "Phu Quoc,VN",
    "sapa": "Sa Pa,VN", "đà lạt": "Da Lat,VN",
    "huế": "Hue,VN", "cần thơ": "Can Tho,VN",
}

def weather_tool(location: str, date: str = "hôm nay") -> dict:
    """
    Lấy thông tin thời tiết hiện tại tại một địa điểm.
    Args:
        location: Tên thành phố (vd: "Đà Nẵng")
        date: Mô tả ngày (label, API trả về thời tiết hiện tại)
    Returns:
        dict: condition, temp_c, feels_like_c, humidity, wind_speed_ms, rain_1h_mm
    """
    if not OPENWEATHER_API_KEY:
        return {"status": "error", "message": "Thiếu OPENWEATHER_API_KEY trong .env"}

    query = _VN_CITY_MAP.get(location.lower().strip(), location)
    data = _get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": query, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "vi"},
    )
    if isinstance(data, dict) and data.get("status") == "error":
        return data
    if data.get("cod") != 200:
        return {"status": "error", "message": data.get("message", f"Không tìm thấy '{location}'")}

    return {
        "status": "success",
        "location":      location,
        "date":          date,
        "condition":     data["weather"][0].get("description", ""),
        "temp_c":        round(data["main"]["temp"], 1),
        "feels_like_c":  round(data["main"]["feels_like"], 1),
        "humidity":      data["main"]["humidity"],
        "wind_speed_ms": data.get("wind", {}).get("speed", 0),
        "rain_1h_mm":    data.get("rain", {}).get("1h", 0),
        "source":        "OpenWeatherMap",
    }


# ---------------------------------------------------------------------------
# 2. Attraction Search Tool — Foursquare Places Search API
#    Docs: https://docs.foursquare.com/reference/places-search
#    Free: 1,000 calls/ngày — không cần thẻ tín dụng
# ---------------------------------------------------------------------------

# Sở thích → Foursquare Category ID
_INTEREST_TO_CAT = {
    "biển":    "16032",  # Beach
    "núi":     "16026",  # Mountain
    "leo núi": "16026",
    "bảo tàng":"10027",  # Museum
    "văn hóa": "10027",
    "lịch sử": "10027",
    "chùa":    "12046",  # Temple / Place of Worship
    "công viên":"16019", # Park
    "di sản":  "10027",
    "cáp treo":"16000",  # Outdoors & Recreation (generic)
}
_DEFAULT_ATTRACTION_CAT = "16000,10000"  # Outdoors + Arts & Entertainment

def attraction_search_tool(location: str, interests: list[str] = None, max_results: int = 5) -> dict:
    """
    Tìm địa điểm tham quan qua Foursquare Places Search.
    Args:
        location: Tên thành phố (vd: "Đà Nẵng")
        interests: Sở thích (vd: ["biển", "leo núi"])
        max_results: Số kết quả tối đa (1-10)
    Returns:
        dict: danh sách attractions với name, type, address, rating
    """
    if not FOURSQUARE_API_KEY:
        return {"status": "error", "message": "Thiếu FOURSQUARE_API_KEY trong .env"}

    coords = _geocode(location)
    if not coords:
        return {"status": "error", "message": f"Không geocode được '{location}'. Kiểm tra OPENWEATHER_API_KEY."}
    lat, lon = coords

    # Chọn category khớp nhất với interests
    cat = _DEFAULT_ATTRACTION_CAT
    if interests:
        for interest in interests:
            c = _INTEREST_TO_CAT.get(interest.lower())
            if c:
                cat = c
                break

    data = _get(
        "https://api.foursquare.com/v3/places/search",
        params={
            "ll": f"{lat},{lon}",
            "categories": cat,
            "limit": min(max_results, 10),
            "sort": "RATING",
            "fields": "name,location,categories,rating,description",
        },
        headers=_fsq_headers(),
    )
    if isinstance(data, dict) and data.get("status") == "error":
        return data

    results = []
    for place in data.get("results", []):
        cats = [c["name"] for c in place.get("categories", [])]
        addr = place.get("location", {})
        results.append({
            "name":        place.get("name"),
            "type":        cats[0] if cats else "Địa điểm",
            "address":     addr.get("formatted_address", addr.get("address", "")),
            "rating":      place.get("rating"),
            "description": place.get("description", ""),
        })

    return {
        "status": "success",
        "location":    location,
        "interests":   interests,
        "attractions": results[:max_results],
        "total_found": len(results),
        "source":      "Foursquare",
    }


# ---------------------------------------------------------------------------
# 3. Restaurant Search Tool — Foursquare Places Search API
#    Cùng API key với attraction_search_tool
# ---------------------------------------------------------------------------

# Loại ẩm thực → Foursquare Category ID
_CUISINE_TO_CAT = {
    "hải sản":   "13029",  # Seafood Restaurant
    "seafood":   "13029",
    "việt nam":  "13236",  # Vietnamese Restaurant
    "việt":      "13236",
    "đặc sản":   "13236",
    "bbq":       "13049",  # BBQ Joint
    "lẩu":       "13062",  # Hot Pot
    "pizza":     "13064",  # Pizza Place
    "âu":        "13009",  # American / European
    "cà phê":    "13032",  # Coffee Shop
    "cafe":      "13032",
    "chay":      "13072",  # Vegetarian / Vegan
}
_DEFAULT_FOOD_CAT = "13065"  # Restaurant (generic)

def restaurant_search_tool(location: str, cuisine: str = None,
                            budget_per_person_vnd: int = None, max_results: int = 3) -> dict:
    """
    Tìm nhà hàng qua Foursquare Places Search.
    Args:
        location: Tên thành phố
        cuisine: Loại ẩm thực (vd: "Hải sản", "Việt Nam", "BBQ")
        budget_per_person_vnd: Ngân sách tối đa/người (VNĐ)
        max_results: Số kết quả (1-10)
    Returns:
        dict: danh sách nhà hàng với name, cuisine, address, rating, price_level
    """
    if not FOURSQUARE_API_KEY:
        return {"error": "Thiếu FOURSQUARE_API_KEY trong .env"}

    coords = _geocode(location)
    if not coords:
        return {"error": f"Không geocode được '{location}'"}
    lat, lon = coords

    cat = _CUISINE_TO_CAT.get(cuisine.lower(), _DEFAULT_FOOD_CAT) if cuisine else _DEFAULT_FOOD_CAT

    data = _get(
        "https://api.foursquare.com/v3/places/search",
        params={
            "ll": f"{lat},{lon}",
            "categories": cat,
            "limit": min(max_results * 2, 10),
            "sort": "RATING",
            "fields": "name,location,categories,rating,price,hours,tel",
        },
        headers=_fsq_headers(),
    )
    if isinstance(data, dict) and "error" in data:
        return data

    # Foursquare price: 1=rẻ(<100k), 2=vừa(100-300k), 3=cao(300-700k), 4=rất cao(>700k)
    price_cap = None
    if budget_per_person_vnd:
        if budget_per_person_vnd < 100_000:   price_cap = 1
        elif budget_per_person_vnd < 300_000: price_cap = 2
        elif budget_per_person_vnd < 700_000: price_cap = 3
        else:                                  price_cap = 4

    results = []
    for place in data.get("results", []):
        price_level = place.get("price")
        if price_cap and price_level and price_level > price_cap:
            continue
        cats = [c["name"] for c in place.get("categories", [])]
        addr = place.get("location", {})
        results.append({
            "name":        place.get("name"),
            "cuisine":     cats[0] if cats else (cuisine or "Nhà hàng"),
            "address":     addr.get("formatted_address", ""),
            "rating":      place.get("rating"),
            "price_level": price_level,
            "open_now":    place.get("hours", {}).get("open_now"),
            "phone":       place.get("tel", ""),
        })

    return {
        "location":       location,
        "cuisine_filter": cuisine,
        "restaurants":    results[:max_results],
        "source":         "Foursquare",
    }


# ---------------------------------------------------------------------------
# 4. Distance Tool — Haversine + OpenWeatherMap Geocoding
#    Không cần API riêng, dùng lại OPENWEATHER_API_KEY để geocode
# ---------------------------------------------------------------------------
def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return round(2 * R * math.asin(math.sqrt(a)), 1)

def distance_tool(origin: str, destination: str, mode: str = "car") -> dict:
    """
    Tính khoảng cách và thời gian di chuyển giữa 2 địa điểm.
    Args:
        origin: Địa điểm xuất phát (vd: "Đà Nẵng")
        destination: Địa điểm đến (vd: "Hội An")
        mode: "car" | "motorbike" | "walking"
    Returns:
        dict: distance_km, duration_minutes, mode
    """
    o = _geocode(origin)
    d = _geocode(destination)
    if not o:
        return {"error": f"Không geocode được '{origin}'"}
    if not d:
        return {"error": f"Không geocode được '{destination}'"}

    dist     = _haversine(*o, *d)
    speeds   = {"car": 40, "motorbike": 30, "walking": 5}
    duration = round((dist / speeds.get(mode, 40)) * 60)

    return {
        "origin":           origin,
        "destination":      destination,
        "distance_km":      dist,
        "duration_minutes": duration,
        "mode":             mode,
        "note":             "Khoảng cách đường chim bay — thực tế dài hơn ~20-30%",
    }


# ---------------------------------------------------------------------------
# 5. Cost Calculator — Python thuần, không cần API
# ---------------------------------------------------------------------------
def cost_calculator_tool(num_days: int, accommodation_per_night_vnd: int = 500_000,
                          meals_per_day_vnd: int = 300_000, transport_total_vnd: int = 200_000,
                          attraction_fees_vnd: int = 0, other_vnd: int = 0) -> dict:
    """
    Ước tính tổng chi phí chuyến đi.
    Args:
        num_days: Số ngày
        accommodation_per_night_vnd: Khách sạn/đêm (VNĐ)
        meals_per_day_vnd: Ăn uống/ngày (VNĐ)
        transport_total_vnd: Đi lại tổng cộng (VNĐ)
        attraction_fees_vnd: Vé tham quan tổng (VNĐ)
        other_vnd: Chi phí khác (VNĐ)
    Returns:
        dict: bảng phân tích chi phí và tổng
    """
    accommodation = accommodation_per_night_vnd * num_days
    meals         = meals_per_day_vnd * num_days
    total         = accommodation + meals + transport_total_vnd + attraction_fees_vnd + other_vnd

    return {
        "num_days": num_days,
        "breakdown": {
            "accommodation": f"{accommodation:,} VNĐ",
            "meals":         f"{meals:,} VNĐ",
            "transport":     f"{transport_total_vnd:,} VNĐ",
            "attractions":   f"{attraction_fees_vnd:,} VNĐ",
            "other":         f"{other_vnd:,} VNĐ",
        },
        "total_vnd":         total,
        "total_million_vnd": round(total / 1_000_000, 2),
        "daily_average_vnd": round(total / num_days),
    }


# ---------------------------------------------------------------------------
# Tool Registry — discovered by the ReAct agent
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "weather_tool": {
        "fn": weather_tool,
        "description": (
            "Lấy thời tiết hiện tại qua OpenWeatherMap. "
            "Args: location (str), date (str, MM/DD/YYYY hoặc 'hôm nay')"
        ),
    },
    "attraction_search_tool": {
        "fn": attraction_search_tool,
        "description": (
            "Tìm địa điểm tham quan qua Foursquare. "
            "Args: location (str), interests (list[str]), max_results (int)"
        ),
    },
    "restaurant_search_tool": {
        "fn": restaurant_search_tool,
        "description": (
            "Tìm nhà hàng theo ẩm thực và ngân sách qua Foursquare. "
            "Args: location (str), cuisine (str), budget_per_person_vnd (int), max_results (int)"
        ),
    },
    "distance_tool": {
        "fn": distance_tool,
        "description": (
            "Tính khoảng cách và thời gian di chuyển (Haversine + geocode). "
            "Args: origin (str), destination (str), mode (str: car|motorbike|walking)"
        ),
    },
    "cost_calculator_tool": {
        "fn": cost_calculator_tool,
        "description": (
            "Ước tính tổng chi phí chuyến đi. "
            "Args: num_days (int), accommodation_per_night_vnd (int), meals_per_day_vnd (int), "
            "transport_total_vnd (int), attraction_fees_vnd (int), other_vnd (int)"
        ),
    },
}