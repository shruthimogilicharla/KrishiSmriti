"""Spray-window check from Open-Meteo (free, no key). Spraying before rain washes money away."""
import time

import httpx


_cache: dict = {}


def spray_window(lat: float, lon: float) -> dict | None:
    key = (round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 900:
        return hit[1]
    out = _fetch(lat, lon)
    _cache[key] = (time.time() if out else time.time() - 600, out)  # retry sooner when it failed
    return out


def _fetch(lat, lon):
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=5, params={
            "latitude": lat, "longitude": lon, "forecast_hours": 24, "timezone": "auto",
            "hourly": "precipitation_probability,wind_speed_10m,temperature_2m,relative_humidity_2m",
        })
        h = r.json()["hourly"]
        rain = max(h["precipitation_probability"] or [0])
        wind = max(h["wind_speed_10m"] or [0])
        temp = max(h["temperature_2m"] or [0])
        hum = round(sum(h["relative_humidity_2m"]) / len(h["relative_humidity_2m"]))
        ok = rain < 40 and wind < 15
        return {"ok_to_spray": ok, "max_rain_prob": rain, "max_wind_kmh": wind, "max_temp_c": temp,
                "avg_humidity": hum,
                "advice": "Good window: spray early morning or evening." if ok else
                          f"Hold spraying: rain chance {rain}% / wind {wind} km/h in next 24h."}
    except Exception as e:
        print("[weather] unavailable:", e)
        return None
