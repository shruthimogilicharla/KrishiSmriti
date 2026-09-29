"""Crop calendars, market prices and government schemes.

Crop calendars: simplified from state agricultural university Package of Practices.
Market prices: live from Agmarknet (data.gov.in) when DATA_GOV_API_KEY is set, otherwise a
clearly labelled SAMPLE series so the demo still shows the feature.
"""
import os
import random
from datetime import date, timedelta

import httpx

# crop key -> list of (stage name, start DAS, end DAS, icon, tasks)
CALENDAR = {
    "cotton": [
        ("Seedling", 0, 20, "🌱", ["Gap filling within 10 days", "Watch for sucking pests on young leaves"]),
        ("Vegetative", 21, 45, "🌿", ["First top-dress of nitrogen", "Check undersides of leaves for whitefly and jassids every 3 days"]),
        ("Squaring", 46, 65, "🌼", ["Install pheromone traps for pink bollworm (5 per acre)", "Second top-dress of nitrogen"]),
        ("Flowering", 66, 100, "🌸", ["Look for rosette flowers (pink bollworm)", "Avoid heavy nitrogen now", "Keep yellow sticky traps up"]),
        ("Boll development", 101, 140, "🥚", ["Open 20 green bolls per acre to check for pink bollworm", "Irrigate if soil is dry at boll formation"]),
        ("Picking", 141, 190, "☁️", ["Pick in the morning, keep kapas dry and clean", "Stop spraying 2 weeks before picking"]),
    ],
    "chilli": [
        ("Establishment", 0, 20, "🌱", ["Replace dead seedlings", "Drench Trichoderma near the roots if damping-off appears"]),
        ("Vegetative", 21, 50, "🌿", ["Watch for leaf curl (thrips, mites, whitefly)", "Put up blue and yellow sticky traps"]),
        ("Flowering", 51, 80, "🌸", ["Avoid water stress: flowers drop", "Check for flower drop and thrips"]),
        ("Fruiting", 81, 120, "🌶️", ["Watch for fruit rot and borer", "Top-dress potash"]),
        ("Harvest pickings", 121, 200, "🧺", ["Pick red ripe fruits every 10-15 days", "Dry on tarpaulin, not on bare soil (aflatoxin)"]),
    ],
    "wheat": [
        ("Germination", 0, 20, "🌱", ["Check even germination"]),
        ("Crown root (CRI)", 21, 25, "💧", ["First irrigation at 21 days is the most important one"]),
        ("Tillering", 26, 45, "🌿", ["Top-dress urea after irrigation", "Weed control before 35 days"]),
        ("Jointing", 46, 65, "🎋", ["Watch for yellow rust stripes on leaves"]),
        ("Heading & flowering", 66, 95, "🌾", ["Irrigate at flowering", "Do not irrigate in strong wind (lodging)"]),
        ("Grain filling & harvest", 96, 135, "🌾", ["Last irrigation at milk stage", "Harvest when grains are hard"]),
    ],
    "paddy": [
        ("Establishment", 0, 25, "🌱", ["Keep 2-3 cm water", "Fill gaps within 10 days"]),
        ("Tillering", 26, 55, "🌿", ["Top-dress nitrogen", "Check for stem borer dead hearts"]),
        ("Panicle initiation", 56, 80, "🎋", ["Keep 5 cm water", "Watch for blast spots on leaves"]),
        ("Flowering", 81, 105, "🌸", ["Do not let the field dry", "Watch for brown planthopper at the base"]),
        ("Maturity & harvest", 106, 140, "🌾", ["Drain field 10 days before harvest"]),
    ],
    "groundnut": [
        ("Emergence", 0, 20, "🌱", ["Check for collar rot"]),
        ("Flowering", 21, 40, "🌸", ["Apply gypsum at 40-45 days"]),
        ("Pegging", 41, 70, "🥜", ["Do not disturb soil after pegging", "Light irrigation"]),
        ("Pod development", 71, 100, "🥜", ["Watch for leaf spot and rust"]),
        ("Maturity", 101, 125, "🧺", ["Harvest when inner shell turns dark"]),
    ],
}

# Minimum Support Price, ₹/quintal (Govt of India). Verify each season.
MSP = {"cotton": (7710, "Medium staple, KMS 2025-26"), "paddy": (2369, "Common, KMS 2025-26"),
       "wheat": (2585, "RMS 2026-27"), "groundnut": (7263, "KMS 2025-26")}
BASE_PRICE = {"cotton": 7450, "chilli": 13200, "wheat": 2650, "paddy": 2300, "groundnut": 6900}
AGMARK_NAME = {"cotton": "Cotton", "chilli": "Dry Chillies", "wheat": "Wheat", "paddy": "Paddy(Dhan)(Common)",
               "groundnut": "Groundnut"}


def crop_stage(crop_key: str, sown: str | None) -> dict | None:
    if not sown or crop_key not in CALENDAR:
        return None
    das = (date.today() - date.fromisoformat(sown)).days
    stages = CALENDAR[crop_key]
    cur_i = next((i for i, s in enumerate(stages) if s[1] <= das <= s[2]), len(stages) - 1)
    name, start, end, icon, tasks = stages[cur_i]
    nxt = stages[cur_i + 1] if cur_i + 1 < len(stages) else None
    return {"das": das, "stage": name, "icon": icon, "tasks": tasks, "progress": min(100, round(das / stages[-1][2] * 100)),
            "stages": [{"name": s[0], "icon": s[3], "start": s[1], "end": s[2], "current": i == cur_i} for i, s in enumerate(stages)],
            "next": {"name": nxt[0], "in_days": max(0, nxt[1] - das)} if nxt else None}


def market(crop_key: str, district: str, state: str) -> dict:
    key = os.getenv("DATA_GOV_API_KEY")
    if key and crop_key in AGMARK_NAME:
        try:
            r = httpx.get("https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070", timeout=6, params={
                "api-key": key, "format": "json", "limit": 50,
                "filters[state]": state, "filters[commodity]": AGMARK_NAME[crop_key]})
            recs = r.json().get("records", [])
            if recs:
                rows = [{"market": x["market"], "date": x["arrival_date"], "modal": int(float(x["modal_price"])),
                         "min": int(float(x["min_price"])), "max": int(float(x["max_price"]))} for x in recs]
                return {"crop": crop_key, "source": "Agmarknet (live)", "sample": False, "today": rows[0]["modal"],
                        "markets": rows[:6], "series": [], "msp": MSP.get(crop_key)}
        except Exception as e:
            print("[market] live fetch failed:", e)
    # sample series: deterministic random walk so it looks the same every reload
    base = BASE_PRICE.get(crop_key, 3000)
    rnd = random.Random(crop_key + district)
    series, p = [], base * 0.95
    for i in range(30, -1, -1):
        p = p * (1 + rnd.uniform(-0.012, 0.016))
        series.append({"date": (date.today() - timedelta(days=i)).isoformat(), "modal": round(p / 10) * 10})
    today = series[-1]["modal"]
    week = series[-8]["modal"]
    return {"crop": crop_key, "source": "SAMPLE data (set DATA_GOV_API_KEY for live Agmarknet prices)", "sample": True,
            "today": today, "change_7d_pct": round((today - week) / week * 100, 1), "series": series,
            "markets": [{"market": f"{district} APMC", "modal": today}, {"market": "Nearest eNAM mandi", "modal": round(today * 1.02 / 10) * 10}],
            "msp": MSP.get(crop_key)}


SCHEMES = [
    {"id": "pmkisan", "name": "PM-KISAN", "icon": "💰", "what": "₹6,000 a year in three instalments to land-holding farmer families.",
     "who": "Farmers with land records in their name. e-KYC and Aadhaar-linked bank account needed.", "where": "pmkisan.gov.in or CSC centre"},
    {"id": "pmfby", "name": "PM Fasal Bima Yojana (crop insurance)", "icon": "🛡️",
     "what": "Crop loss insurance. Farmer premium is 2% for kharif, 1.5% for rabi, 5% for commercial/horticulture crops.",
     "who": "All farmers growing notified crops. Enrol before the season cut-off (usually 31 July kharif, 31 December rabi).",
     "where": "Bank, CSC, or pmfby.gov.in. Your KrishiSmriti plot record can support a claim."},
    {"id": "kcc", "name": "Kisan Credit Card", "icon": "💳", "what": "Low-interest crop loan with interest subvention for prompt repayment.",
     "who": "Owner farmers, tenant farmers, sharecroppers.", "where": "Any bank branch"},
    {"id": "shc", "name": "Soil Health Card", "icon": "🧪", "what": "Free soil test with nutrient and fertiliser advice.",
     "who": "All farmers.", "where": "Agriculture office / soilhealth.dac.gov.in"},
    {"id": "kusum", "name": "PM-KUSUM (solar pump)", "icon": "☀️", "what": "Subsidy for solar irrigation pumps.",
     "who": "Individual farmers, FPOs, panchayats.", "where": "State renewable energy agency"},
]
