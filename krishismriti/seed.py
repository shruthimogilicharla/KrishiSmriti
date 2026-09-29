"""Demo data: 8 farmers in 4 villages and 4 languages, built around the Plot-14 pitch story."""
from datetime import date, timedelta

PLOTS = [
    # id, farmer, village, district, state, crop label, crop key, acres, lat, lon, lang, sown, phone
    ("PLOT-14", "Ramaiah", "Kondapur", "Guntur", "Andhra Pradesh", "Cotton", "cotton", 2.5, 16.30, 80.45, "te", 100, "+919800000014"),
    ("PLOT-7", "Lakshmi", "Kondapur", "Guntur", "Andhra Pradesh", "Chilli", "chilli", 1.5, 16.31, 80.46, "te", 72, "+919800000007"),
    ("PLOT-9", "Srinivas Rao", "Kondapur", "Guntur", "Andhra Pradesh", "Cotton", "cotton", 3.0, 16.29, 80.44, "te", 96, "+919800000009"),
    ("PLOT-11", "Venkata Reddy", "Kondapur", "Guntur", "Andhra Pradesh", "Chilli", "chilli", 2.0, 16.32, 80.43, "te", 65, "+919800000011"),
    ("PLOT-22", "Suresh Yadav", "Rampur", "Varanasi", "Uttar Pradesh", "Paddy", "paddy", 3.0, 25.32, 82.97, "hi", 88, "+919800000022"),
    ("PLOT-23", "Kamla Devi", "Rampur", "Varanasi", "Uttar Pradesh", "Paddy", "paddy", 1.2, 25.33, 82.98, "hi", 84, "+919800000023"),
    ("PLOT-31", "Murugan", "Papanasam", "Thanjavur", "Tamil Nadu", "Paddy", "paddy", 2.2, 10.93, 79.27, "ta", 55, "+919800000031"),
    ("PLOT-41", "Joseph Mathew", "Kuttanad", "Alappuzha", "Kerala", "Paddy", "paddy", 1.8, 9.43, 76.41, "ml", 47, "+919800000041"),
]


def seed(mem):
    if mem.store["plots"]:
        return
    ago = lambda d: (date.today() - timedelta(days=d)).isoformat()

    for (pid, farmer, village, dist, state, crop, key, acres, lat, lon, lang, das, phone) in PLOTS:
        mem.add_plot({"id": pid, "farmer": farmer, "village": village, "district": dist, "state": state,
                      "crop": f"{crop} (Kharif 2026)", "crop_key": key, "area_acres": acres, "lat": lat, "lon": lon,
                      "lang": lang, "sown": ago(das), "phone": phone, "joined": ago(200 if pid == "PLOT-14" else 60)})

    def E(**k):
        k.setdefault("source", "seed")
        return mem.add_event(k, retain=False)

    # ---------- PLOT-14: the pitch story ----------
    E(plot_id="PLOT-14", date="2025-06-18", type="seed", product="Bt cotton hybrid (RCH-659 BG-II)", cost=1860)
    E(plot_id="PLOT-14", date="2025-12-05", type="soil_test",
      notes="Soil Health Card: pH 8.1, low nitrogen, medium phosphorus, high potassium, low zinc")
    E(plot_id="PLOT-14", date="2026-01-12", type="harvest", notes="Kharif 2025 cotton: 9 quintal per acre")
    E(plot_id="PLOT-14", date="2026-02-10", type="treatment", product="imidacloprid", target="whitefly", cost=850,
      outcome="failed", notes="Whiteflies came back in 6 days")
    E(plot_id="PLOT-14", date="2026-03-02", type="treatment", product="imidacloprid", target="whitefly", cost=850,
      outcome="failed", notes="Second spray, no effect after 5 days, leaves still sticky")
    E(plot_id="PLOT-14", date="2026-03-20", type="treatment", product="neem oil", target="whitefly", cost=320,
      outcome="worked", days_healthy=47, notes="Neem oil spray in the evening plus 20 yellow sticky traps per acre")
    E(plot_id="PLOT-14", date=ago(100), type="seed", product="Bt cotton hybrid (RCH-659 BG-II)", cost=1860)
    E(plot_id="PLOT-14", date=ago(70), type="fertilizer", product="Urea 45 kg/acre (first top-dress)", cost=540)
    E(plot_id="PLOT-14", date=ago(40), type="treatment", product="pheromone traps", target="pink bollworm", cost=450,
      outcome="worked", days_healthy=30, notes="5 traps per acre at squaring")
    E(plot_id="PLOT-14", date=ago(9), type="fertilizer", product="Zinc sulphate 10 kg/acre", cost=600,
      notes="Applied because soil card showed low zinc")
    E(plot_id="PLOT-14", date=ago(8), type="treatment", product="trichoderma viride", target="root rot patches", cost=280,
      notes="Soil drench on 12 plants near the channel")  # pending -> follow-up due
    E(plot_id="PLOT-14", date=ago(2), type="observation", target="whitefly", notes="Few whiteflies seen on lower leaves")

    # ---------- Kondapur neighbours: community memory + outbreak ----------
    E(plot_id="PLOT-7", date="2026-01-14", type="treatment", product="acetamiprid", target="whitefly", cost=700, outcome="failed", notes="No control")
    E(plot_id="PLOT-7", date="2026-01-25", type="treatment", product="verticillium lecanii", target="whitefly", cost=400,
      outcome="worked", days_healthy=35, notes="Sprayed in evening with high humidity")
    E(plot_id="PLOT-7", date=ago(4), type="observation", target="whitefly", notes="Whitefly on chilli, leaf curl starting")
    E(plot_id="PLOT-9", date="2025-09-02", type="treatment", product="thiamethoxam", target="whitefly", cost=780, outcome="failed")
    E(plot_id="PLOT-9", date="2025-09-15", type="treatment", product="spiromesifen", target="whitefly", cost=1150, outcome="worked", days_healthy=28)
    E(plot_id="PLOT-9", date=ago(5), type="observation", target="whitefly", notes="Whitefly numbers rising")
    E(plot_id="PLOT-11", date="2026-02-02", type="treatment", product="fipronil", target="thrips", cost=620, outcome="worked", days_healthy=25)
    E(plot_id="PLOT-11", date=ago(20), type="treatment", product="imidacloprid", target="whitefly", cost=850, outcome="failed",
      notes="Dealer recommended, did not work")

    E(plot_id="PLOT-11", date="2025-10-10", type="treatment", product="lambda-cyhalothrin", target="fruit borer", cost=540, outcome="failed")
    E(plot_id="PLOT-9", date="2025-10-01", type="treatment", product="profenofos", target="pink bollworm", cost=690, outcome="failed")

    # ---------- Rampur (Hindi) ----------
    E(plot_id="PLOT-22", date="2025-11-12", type="seed", product="HD-2967 wheat", cost=2400)
    E(plot_id="PLOT-22", date="2026-01-20", type="treatment", product="propiconazole", target="yellow rust", cost=900, outcome="worked", days_healthy=60)
    E(plot_id="PLOT-22", date="2026-04-10", type="harvest", notes="Wheat 18 quintal per acre")
    E(plot_id="PLOT-22", date=ago(30), type="treatment", product="cartap hydrochloride", target="stem borer", cost=760, outcome="partial")
    E(plot_id="PLOT-22", date="2025-09-05", type="treatment", product="chlorpyrifos", target="leaf folder", cost=480, outcome="failed")
    E(plot_id="PLOT-23", date="2025-08-28", type="treatment", product="chlorpyrifos", target="leaf folder", cost=450, outcome="failed")
    E(plot_id="PLOT-23", date=ago(25), type="treatment", product="chlorantraniliprole", target="stem borer", cost=1300, outcome="worked", days_healthy=24)

    # ---------- Papanasam (Tamil) & Kuttanad (Malayalam) ----------
    E(plot_id="PLOT-31", date="2026-01-05", type="treatment", product="tricyclazole", target="blast", cost=650, outcome="worked", days_healthy=40)
    E(plot_id="PLOT-31", date="2025-11-20", type="treatment", product="hexaconazole", target="sheath blight", cost=700, outcome="failed")
    E(plot_id="PLOT-31", date=ago(6), type="treatment", product="pseudomonas fluorescens", target="sheath blight", cost=300)
    E(plot_id="PLOT-41", date="2026-02-11", type="treatment", product="carbendazim", target="sheath blight", cost=500, outcome="failed")
    E(plot_id="PLOT-41", date="2026-02-24", type="treatment", product="hexaconazole", target="sheath blight", cost=720, outcome="worked", days_healthy=33)

    mem.add_saving("PLOT-14", "imidacloprid", 850, "Blocked a third imidacloprid spray (failed twice before)")
    mem.add_saving("PLOT-9", "acetamiprid", 700, "Blocked acetamiprid: same group as thiamethoxam that failed")
    mem.add_saving("PLOT-41", "carbendazim", 500, "Blocked repeat carbendazim for sheath blight")

    elders = [
        ("Kondapur", "Venkatamma (78)", "Soak crushed neem seed kernels overnight in water, filter through cloth and spray in the evening against sucking pests.", True, "te"),
        ("Kondapur", "Narayana (81)", "Plant two rows of jowar around the cotton field as a wall against whitefly drifting in from neighbouring fields.", False, "te"),
        ("Rampur", "Ram Pyari (74)", "Mix wood ash with the stored grain to keep weevils away.", False, "hi"),
        ("Papanasam", "Ponnusamy (80)", "Grow a green manure crop of daincha before paddy to make the soil soft and rich.", True, "ta"),
    ]
    for i, (v, name, text, ver, lang) in enumerate(elders):
        mem.store["elder"].append({"id": f"eld{i}", "village": v, "elder": name, "text": text, "verified": ver,
                                   "lang": lang, "date": ago(120 - i * 10)})

    mem.store["escalations"] = [{
        "id": "esc001", "plot_id": "PLOT-7", "status": "open", "created": ago(1), "lang": "te",
        "question": "Chilli leaves curling upwards and turning small. Is it virus?",
        "ai_answer": "Likely leaf curl complex spread by thrips/whitefly. Not sure if viral. Escalated.",
        "photo_note": "Upward leaf curling, small crinkled leaves, few thrips visible", "answer": None}]
    mem.save()
