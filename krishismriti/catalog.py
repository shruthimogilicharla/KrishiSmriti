"""Buy cards: what to buy, natural or chemical, approximate price, and where to buy it.

Prices are APPROXIMATE retail ranges (2025-26) to help the farmer budget. Urea and DAP have
government-fixed MRPs. Links open a search on real Indian agri-input stores, so they keep working
when individual product pages change. In production this becomes a live partner feed
(BigHaat / AgroStar / DeHaat / IFFCO Bazar) with real stock and price, plus the nearest
registered dealer.
"""
from urllib.parse import quote_plus

# key -> display info. kind: "natural" (organic / bio / physical) or "chemical"
CATALOG = {
    # ---- natural / bio ----
    "neem oil": {"name": "Neem oil (Azadirachtin 1500 ppm)", "kind": "natural", "pack": "1 litre", "price": "₹450–650",
                 "brands": "Multineem, Nimbecidine, local neem oil", "q": "neem oil azadirachtin 1500 ppm"},
    "yellow sticky traps": {"name": "Yellow sticky traps", "kind": "natural", "pack": "Pack of 20", "price": "₹300–450",
                            "brands": "Any brand", "q": "yellow sticky trap"},
    "blue sticky traps": {"name": "Blue sticky traps", "kind": "natural", "pack": "Pack of 20", "price": "₹300–450",
                          "brands": "Any brand", "q": "blue sticky trap"},
    "pheromone traps": {"name": "Pheromone trap + lure", "kind": "natural", "pack": "Set of 5", "price": "₹400–600",
                        "brands": "Pink bollworm / fruit borer lure", "q": "pheromone trap lure"},
    "verticillium lecanii": {"name": "Verticillium lecanii (bio-pesticide)", "kind": "natural", "pack": "1 kg", "price": "₹250–400",
                             "brands": "Any registered brand", "q": "verticillium lecanii"},
    "beauveria bassiana": {"name": "Beauveria bassiana (bio-pesticide)", "kind": "natural", "pack": "1 kg", "price": "₹250–400",
                           "brands": "Any registered brand", "q": "beauveria bassiana"},
    "trichoderma viride": {"name": "Trichoderma viride (bio-fungicide)", "kind": "natural", "pack": "1 kg", "price": "₹150–300",
                           "brands": "Any registered brand", "q": "trichoderma viride"},
    "pseudomonas fluorescens": {"name": "Pseudomonas fluorescens (bio-fungicide)", "kind": "natural", "pack": "1 kg", "price": "₹150–300",
                                "brands": "Any registered brand", "q": "pseudomonas fluorescens"},
    "vermicompost": {"name": "Vermicompost", "kind": "natural", "pack": "25 kg bag", "price": "₹250–450",
                     "brands": "Local / FPO", "q": "vermicompost"},
    "neem cake": {"name": "Neem cake (organic manure)", "kind": "natural", "pack": "25 kg bag", "price": "₹600–900",
                  "brands": "Any", "q": "neem cake fertilizer"},
    # ---- chemical: pesticides ----
    "spiromesifen": {"name": "Spiromesifen 22.9% SC", "kind": "chemical", "pack": "100 ml", "price": "₹550–750",
                     "brands": "Oberon and generics", "q": "spiromesifen 22.9 sc"},
    "spinosad": {"name": "Spinosad 45% SC", "kind": "chemical", "pack": "75 ml", "price": "₹900–1,300",
                 "brands": "Tracer and generics", "q": "spinosad 45 sc"},
    "fipronil": {"name": "Fipronil 5% SC", "kind": "chemical", "pack": "250 ml", "price": "₹300–450",
                 "brands": "Regent and generics", "q": "fipronil 5 sc"},
    "flonicamid": {"name": "Flonicamid 50% WG", "kind": "chemical", "pack": "60 g", "price": "₹450–650",
                   "brands": "Ulala and generics", "q": "flonicamid 50 wg"},
    "chlorantraniliprole": {"name": "Chlorantraniliprole 18.5% SC", "kind": "chemical", "pack": "60 ml", "price": "₹850–1,150",
                            "brands": "Coragen and generics", "q": "chlorantraniliprole 18.5 sc"},
    "emamectin benzoate": {"name": "Emamectin benzoate 5% SG", "kind": "chemical", "pack": "100 g", "price": "₹300–450",
                           "brands": "Proclaim and generics", "q": "emamectin benzoate 5 sg"},
    "hexaconazole": {"name": "Hexaconazole 5% EC", "kind": "chemical", "pack": "500 ml", "price": "₹300–450",
                     "brands": "Contaf and generics", "q": "hexaconazole 5 ec"},
    "tricyclazole": {"name": "Tricyclazole 75% WP", "kind": "chemical", "pack": "120 g", "price": "₹250–400",
                     "brands": "Beam and generics", "q": "tricyclazole 75 wp"},
    "propiconazole": {"name": "Propiconazole 25% EC", "kind": "chemical", "pack": "250 ml", "price": "₹350–500",
                      "brands": "Tilt and generics", "q": "propiconazole 25 ec"},
    # ---- chemical: fertilisers ----
    "urea": {"name": "Urea (46% N)", "kind": "chemical", "pack": "45 kg bag", "price": "₹266.50 (govt fixed MRP)",
             "brands": "IFFCO, NFL, KRIBHCO", "q": "urea fertilizer", "govt": True, "alt": ["vermicompost", "neem cake"]},
    "dap": {"name": "DAP (18-46-0)", "kind": "chemical", "pack": "50 kg bag", "price": "₹1,350 (govt fixed MRP)",
            "brands": "IFFCO, Coromandel", "q": "dap fertilizer", "govt": True, "alt": ["vermicompost"]},
    "potash": {"name": "Muriate of Potash (MOP, 60% K)", "kind": "chemical", "pack": "50 kg bag", "price": "₹1,550–1,800",
               "brands": "IPL, IFFCO", "q": "muriate of potash fertilizer", "alt": ["vermicompost"]},
    "zinc sulphate": {"name": "Zinc sulphate (21% Zn)", "kind": "chemical", "pack": "5 kg", "price": "₹300–500",
                      "brands": "Any", "q": "zinc sulphate fertilizer 21"},
    "gypsum": {"name": "Agricultural gypsum", "kind": "natural", "pack": "50 kg bag", "price": "₹300–500",
               "brands": "Any (subsidised in some states)", "q": "agricultural gypsum"},
}

ALIASES = {"urea": "urea", "యూరియా": "urea", "यूरिया": "urea", "யூரியா": "urea", "യൂറിയ": "urea",
           "dap": "dap", "potash": "potash", "mop": "potash", "zinc sulphate": "zinc sulphate", "zinc": "zinc sulphate",
           "జింక్": "zinc sulphate", "जिंक": "zinc sulphate", "gypsum": "gypsum", "neem oil": "neem oil", "neem": "neem oil",
           "sticky trap": "yellow sticky traps", "blue sticky": "blue sticky traps", "yellow sticky": "yellow sticky traps",
           "pheromone": "pheromone traps", "vermicompost": "vermicompost", "neem cake": "neem cake",
           "emamectin": "emamectin benzoate", "tricyclazole": "tricyclazole", "propiconazole": "propiconazole"}


def find(text: str) -> list[str]:
    t = (text or "").lower()
    keys = [k for k in CATALOG if k in t]
    keys += [v for a, v in ALIASES.items() if a in t]
    out = []
    for k in keys:  # keep order, drop duplicates and "neem oil" when only "neem cake" was meant
        if k not in out and not (k == "neem oil" and "neem cake" in t and "neem oil" not in t):
            out.append(k)
    return out


def buy(key: str, district: str = "", with_alt=True) -> dict | None:
    c = CATALOG.get(key)
    if not c:
        return None
    q = quote_plus(c["q"])
    near = quote_plus(f"{'fertilizer' if key in ('urea', 'dap', 'potash', 'zinc sulphate', 'gypsum') else 'pesticide'} shop near {district}".strip())
    card = {"key": key, **{k: v for k, v in c.items() if k not in ("q", "alt")},
            "links": [
                {"label": "BigHaat", "url": f"https://www.bighaat.com/search?q={q}"},
                {"label": "Amazon", "url": f"https://www.amazon.in/s?k={q}"},
                {"label": "Shop near me", "url": f"https://www.google.com/maps/search/{near}"},
            ]}
    if with_alt and c.get("alt"):
        card["natural_alternatives"] = [buy(a, district, with_alt=False) for a in c["alt"]]
    return card


def cards_for(texts, district="", limit=4) -> list[dict]:
    seen, out = set(), []
    for t in texts:
        for k in find(t):
            if k not in seen:
                seen.add(k)
                out.append(buy(k, district))
    return out[:limit]
