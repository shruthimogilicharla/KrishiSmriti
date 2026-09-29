"""Agronomy rules that must NOT be left to the LLM.

1. Resistance guard: if a chemical failed on this plot, block it AND every other
   product with the same mode of action (IRAC for insecticides, FRAC for fungicides).
   Pests become resistant to the mode of action, not the brand name.
2. Banned / restricted product check (India, Central Insecticides Board).
3. Proven-success recall: surface what already worked on this plot.

The table is a demo reference. In production it is loaded from the CIB&RC
registration list + IRAC/FRAC MoA databases and reviewed by an agronomist.
"""
import re

# name -> (class, MoA group, is_organic)
PRODUCTS = {
    # Insecticides (IRAC)
    "imidacloprid": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "thiamethoxam": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "acetamiprid": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "clothianidin": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "dinotefuran": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "thiacloprid": ("insecticide", "IRAC 4A (neonicotinoid)", False),
    "acephate": ("insecticide", "IRAC 1B (organophosphate)", False),
    "profenofos": ("insecticide", "IRAC 1B (organophosphate)", False),
    "chlorpyrifos": ("insecticide", "IRAC 1B (organophosphate)", False),
    "monocrotophos": ("insecticide", "IRAC 1B (organophosphate)", False),
    "cypermethrin": ("insecticide", "IRAC 3A (pyrethroid)", False),
    "lambda-cyhalothrin": ("insecticide", "IRAC 3A (pyrethroid)", False),
    "fipronil": ("insecticide", "IRAC 2B (phenylpyrazole)", False),
    "emamectin benzoate": ("insecticide", "IRAC 6 (avermectin)", False),
    "spinosad": ("insecticide", "IRAC 5 (spinosyn)", False),
    "pyriproxyfen": ("insecticide", "IRAC 7C (juvenile hormone mimic)", False),
    "diafenthiuron": ("insecticide", "IRAC 12A", False),
    "buprofezin": ("insecticide", "IRAC 16", False),
    "spiromesifen": ("insecticide", "IRAC 23 (tetronic acid)", False),
    "flonicamid": ("insecticide", "IRAC 29", False),
    "chlorantraniliprole": ("insecticide", "IRAC 28 (diamide)", False),
    "cyantraniliprole": ("insecticide", "IRAC 28 (diamide)", False),
    # Fungicides (FRAC)
    "mancozeb": ("fungicide", "FRAC M03", False),
    "copper oxychloride": ("fungicide", "FRAC M01", False),
    "carbendazim": ("fungicide", "FRAC 1", False),
    "tebuconazole": ("fungicide", "FRAC 3 (triazole)", False),
    "hexaconazole": ("fungicide", "FRAC 3 (triazole)", False),
    "propiconazole": ("fungicide", "FRAC 3 (triazole)", False),
    "azoxystrobin": ("fungicide", "FRAC 11 (strobilurin)", False),
    "metalaxyl": ("fungicide", "FRAC 4", False),
    "tricyclazole": ("fungicide", "FRAC 16.1", False),
    # Organic / biological
    "neem oil": ("bio-insecticide", "Botanical (azadirachtin)", True),
    "nske": ("bio-insecticide", "Botanical (neem seed kernel extract)", True),
    "verticillium lecanii": ("bio-insecticide", "Entomopathogenic fungus", True),
    "beauveria bassiana": ("bio-insecticide", "Entomopathogenic fungus", True),
    "trichoderma viride": ("bio-fungicide", "Biocontrol fungus", True),
    "pseudomonas fluorescens": ("bio-fungicide", "Biocontrol bacteria", True),
    "yellow sticky traps": ("trap", "Physical", True),
    "pheromone traps": ("trap", "Physical (pheromone)", True),
    "blue sticky traps": ("trap", "Physical", True),
    "cartap hydrochloride": ("insecticide", "IRAC 14 (nereistoxin analogue)", False),
}

ALIASES = {
    "confidor": "imidacloprid", "imida": "imidacloprid", "इमिडाक्लोप्रिड": "imidacloprid",
    "ఇమిడాక్లోప్రిడ్": "imidacloprid", "actara": "thiamethoxam", "neem": "neem oil",
    "వేప నూనె": "neem oil", "वेप": "neem oil", "नीम": "neem oil", "வேப்ப எண்ணெய்": "neem oil",
    "വേപ്പെണ്ണ": "neem oil", "sticky trap": "yellow sticky traps", "coragen": "chlorantraniliprole",
    "oberon": "spiromesifen", "ulala": "flonicamid", "polo": "diafenthiuron",
}

# Banned or restricted in India (subset, demo). Source: CIB&RC banned/restricted list.
BANNED = {
    "endosulfan": "Banned in India (Supreme Court order, 2011).",
    "methyl parathion": "Banned in India (2018 order).",
    "monocrotophos": "Banned for use on vegetables in India.",
    "carbaryl": "Banned in India (2018 order).",
}


def normalise(name: str) -> str:
    n = (name or "").strip().lower()
    return ALIASES.get(n, n)


def moa(name: str):
    p = PRODUCTS.get(normalise(name))
    return p[1] if p else None


def find_products(text: str) -> list[str]:
    """Pull known product names out of free text (any language that uses the alias table)."""
    t = (text or "").lower()
    found = set()
    for key in list(PRODUCTS) + list(BANNED):
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            found.add(key)
    for alias, key in ALIASES.items():
        if alias in t:
            found.add(key)
    return sorted(found)


def resistance_guard(events: list[dict], target: str | None = None) -> dict:
    """Return products/MoA groups to avoid and treatments that already worked on this plot."""
    tgt = (target or "").lower()
    fails, wins = {}, {}
    for e in events:
        if e.get("type") != "treatment":
            continue
        if tgt and tgt not in (e.get("target") or "").lower():
            continue
        prod = normalise(e.get("product", ""))
        if e.get("outcome") == "failed":
            f = fails.setdefault(prod, {"product": prod, "count": 0, "wasted": 0, "moa": moa(prod), "dates": [],
                                        "target": e.get("target")})
            f["count"] += 1
            f["wasted"] += int(e.get("cost") or 0)
            f["dates"].append(e.get("date"))
        elif e.get("outcome") == "worked":
            w = wins.setdefault(prod, {"product": prod, "count": 0, "best_days": 0, "cost": int(e.get("cost") or 0), "moa": moa(prod),
                                       "target": e.get("target")})
            w["count"] += 1
            w["best_days"] = max(w["best_days"], int(e.get("days_healthy") or 0))
    blocked_groups = {f["moa"] for f in fails.values() if f["moa"] and "Botanical" not in f["moa"]}
    same_group = sorted(
        p for p, (_, g, _) in PRODUCTS.items() if g in blocked_groups and p not in fails
    )
    return {
        "avoid": sorted(fails.values(), key=lambda x: -x["count"]),
        "avoid_same_moa": same_group,
        "blocked_groups": sorted(blocked_groups),
        "proven": sorted(wins.values(), key=lambda x: -x["best_days"]),
    }


def check_mentions(text: str, guard: dict) -> list[dict]:
    """Warnings for any product the farmer mentions that is banned or already failed."""
    warnings = []
    failed = {f["product"]: f for f in guard["avoid"]}
    for p in find_products(text):
        if p in BANNED:
            warnings.append({"level": "danger", "product": p, "reason": BANNED[p]})
        elif p in failed:
            f = failed[p]
            warnings.append({"level": "danger", "product": p,
                             "reason": f"Failed {f['count']}x on this plot (₹{f['wasted']} wasted)."})
        elif p in guard["avoid_same_moa"]:
            warnings.append({"level": "warn", "product": p,
                             "reason": f"Same mode of action ({moa(p)}) as a product that already failed here. Pests resist the group, not the brand."})
    return warnings


# ---------------------------------------------------------------------------
# Offline problem knowledge (works with no API key). Integrated Pest Management:
# non-chemical first, then chemicals from DIFFERENT groups. Doses: follow the label / KVK.
# ---------------------------------------------------------------------------
PROBLEMS = {
    "whitefly": {
        "names": {"en": "Whitefly", "te": "తెల్ల దోమ", "hi": "सफेद मक्खी", "ta": "வெள்ளை ஈ", "ml": "വെള്ളീച്ച"},
        "keys": ["whitefly", "white fly", "తెల్లదోమ", "తెల్ల దోమ", "సఫేద్", "सफेद मक्खी", "safed makhi", "வெள்ளை ஈ", "வெள்ளைஈ",
                 "വെള്ളീച്ച", "ಬಿಳಿ ನೊಣ", "पांढरी माशी"],
        "targets": ["whitefly"],
        "options": [
            {"text": "Put 20 yellow sticky traps per acre at crop height", "product": "yellow sticky traps", "cost": 400},
            {"text": "Spray neem oil (or home-made neem seed extract) in the evening", "product": "neem oil", "cost": 320},
            {"text": "In humid weather spray Verticillium lecanii (bio-pesticide)", "product": "verticillium lecanii", "cost": 400},
            {"text": "Only if very heavy: spiromesifen (IRAC 23) or pyriproxyfen (IRAC 7C). Follow the label dose", "product": "spiromesifen", "cost": 1150},
        ]},
    "thrips": {
        "names": {"en": "Thrips", "te": "తామర పురుగు", "hi": "थ्रिप्स", "ta": "இலைப்பேன்", "ml": "ഇലപ്പേൻ"},
        "keys": ["thrips", "తామర", "థ్రిప్స్", "थ्रिप्स", "इलपेन", "இலைப்பேன்", "ഇലപ്പേൻ"],
        "targets": ["thrips"],
        "options": [
            {"text": "Put blue sticky traps, 20 per acre", "product": "blue sticky traps", "cost": 400},
            {"text": "Spray neem oil in the evening", "product": "neem oil", "cost": 320},
            {"text": "If still spreading: spinosad (IRAC 5) or fipronil (IRAC 2B). Follow the label dose", "product": "spinosad", "cost": 900},
        ]},
    "aphids": {
        "names": {"en": "Aphids", "te": "పేను బంక", "hi": "माहू / चेपा", "ta": "அசுவினி", "ml": "മുഞ്ഞ"},
        "keys": ["aphid", "పేను", "माहू", "चेपा", "அசுவினி", "മുഞ്ഞ"],
        "targets": ["aphid"],
        "options": [
            {"text": "Spray neem oil; spare ladybird beetles, they eat aphids", "product": "neem oil", "cost": 320},
            {"text": "If heavy: flonicamid (IRAC 29). Follow the label dose", "product": "flonicamid", "cost": 800},
        ]},
    "borer": {
        "names": {"en": "Worm / borer", "te": "పురుగు / కాయతొలుచు పురుగు", "hi": "सुंडी / छेदक", "ta": "புழு / துளைப்பான்", "ml": "പുഴു / തുരപ്പൻ"},
        "keys": ["bollworm", "borer", "caterpillar", "worm", "larva", "పురుగు", "కాయతొలుచు", "గులాబీ రంగు", "सुंडी", "इल्ली", "छेदक",
                 "புழு", "துளைப்பான்", "പുഴു", "തുരപ്പൻ"],
        "targets": ["bollworm", "borer", "fruit borer", "stem borer", "pink bollworm", "leaf folder"],
        "options": [
            {"text": "Set pheromone traps, 5 per acre, and check them every 3 days", "product": "pheromone traps", "cost": 450},
            {"text": "Pick and destroy damaged bolls, fruits or dead hearts", "product": None, "cost": 0},
            {"text": "If more than 10% damage: emamectin benzoate (IRAC 6) or chlorantraniliprole (IRAC 28). Follow the label dose", "product": "chlorantraniliprole", "cost": 1300},
        ]},
    "leafcurl": {
        "names": {"en": "Leaf curl", "te": "ఆకు ముడత", "hi": "पत्ती मरोड़", "ta": "இலை சுருட்டை", "ml": "ഇല ചുരുളൽ"},
        "keys": ["leaf curl", "curl", "ముడత", "मरोड़", "मोड़", "சுருட்டை", "ചുരുള"],
        "targets": ["leaf curl"],
        "options": [
            {"text": "Pull out and bury badly curled plants early: virus has no cure", "product": None, "cost": 0},
            {"text": "Control the insects that spread it (whitefly, thrips) with sticky traps and neem oil", "product": "neem oil", "cost": 320},
            {"text": "Ask the KVK to confirm with a photo", "product": None, "cost": 0},
        ]},
    "yellow": {
        "names": {"en": "Yellow leaves", "te": "ఆకులు పసుపు", "hi": "पीली पत्तियां", "ta": "மஞ்சள் இலைகள்", "ml": "മഞ്ഞ ഇലകൾ"},
        "keys": ["yellow", "పసుపు", "पीला", "पीली", "மஞ்சள்", "മഞ്ഞ"],
        "targets": ["yellow"],
        "options": [
            {"text": "Check your Soil Health Card: low nitrogen or zinc are the usual causes", "product": None, "cost": 0},
            {"text": "Drain standing water: waterlogged roots turn leaves yellow", "product": None, "cost": 0},
            {"text": "Top-dress urea or zinc sulphate as your soil card says", "product": "urea", "cost": 600, "buy": ["urea", "zinc sulphate"]},
        ]},
    "spots": {
        "names": {"en": "Spots / fungus", "te": "మచ్చలు / తెగులు", "hi": "धब्बे / झुलसा", "ta": "புள்ளி / பூஞ்சை நோய்", "ml": "പുള്ളി / കുമിൾ രോഗം"},
        "keys": ["yellow rust", "sheath blight", "spot", "blast", "blight", "rust", "fungus", "మచ్చ", "తెగులు", "అగ్గి", "धब्बा", "धब्बे", "झुलसा", "रतुआ",
                 "புள்ளி", "குலை நோய்", "பூஞ்சை", "പുള്ളി", "ബ്ലാസ്റ്റ്", "കുമിൾ"],
        "targets": ["blast", "blight", "sheath blight", "rust", "yellow rust", "leaf spot"],
        "options": [
            {"text": "Remove and burn badly infected leaves; do not add extra urea now", "product": None, "cost": 0},
            {"text": "Spray Pseudomonas fluorescens (bio-fungicide)", "product": "pseudomonas fluorescens", "cost": 300},
            {"text": "Paddy blast: tricyclazole. Sheath blight: hexaconazole. Wheat rust: propiconazole. Follow the label dose", "product": "hexaconazole", "cost": 700},
        ]},
    "wilt": {
        "names": {"en": "Wilting / root rot", "te": "వాడిపోవడం / వేరు కుళ్ళు", "hi": "मुरझाना / जड़ सड़न", "ta": "வாடல் / வேர் அழுகல்", "ml": "വാട്ടം / വേരുചീയൽ"},
        "keys": ["wilt", "rot", "dying", "వాడి", "కుళ్ళు", "ఎండిపో", "मुरझा", "सड़", "வாடல்", "அழுகல்", "വാട്ടം", "ചീയൽ"],
        "targets": ["root rot", "wilt", "root rot patches"],
        "options": [
            {"text": "Drench Trichoderma viride mixed with compost at the root zone", "product": "trichoderma viride", "cost": 280},
            {"text": "Improve drainage; do not over-water", "product": None, "cost": 0},
        ]},
}


def detect_problem(text: str) -> str | None:
    t = (text or "").lower()
    best, rank = None, (10 ** 9, 0)
    for key, p in PROBLEMS.items():
        for k in p["keys"]:
            i = t.find(k.lower())
            if i != -1 and (i, -len(k)) < rank:
                best, rank = key, (i, -len(k))
    return best


def safe_options(problem: str, guard: dict, lang: str = "en") -> list[dict]:
    """IPM options for the problem minus anything memory has blocked on this plot, in the farmer's language."""
    blocked = {a["product"] for a in guard["avoid"]} | set(guard["avoid_same_moa"])
    out = []
    for i, o in enumerate(PROBLEMS[problem]["options"]):
        if o["product"] in blocked:
            continue
        info = PRODUCTS.get(o["product"] or "", ("", "", True))
        if o["product"] and o["product"] not in PRODUCTS:  # fertilisers etc: use the shop catalogue
            from catalog import CATALOG
            info = ("", "", CATALOG.get(o["product"], {}).get("kind") == "natural")
        local = OPTION_TR.get(f"{problem}:{i}", {}).get(lang)
        out.append({"action": local or o["text"], "english": o["text"], "product": o["product"],
                    "buy_keys": o.get("buy") or ([o["product"]] if o["product"] else []),
                    "target": PROBLEMS[problem]["targets"][0],
                    "why": "Safe option for this plot" + (f" · {info[1]}" if info[1] else ""),
                    "est_cost_inr": o["cost"], "organic": info[2]})
    return out


# Farmer-language text for each option (offline mode). Key: (problem, option index)
OPTION_TR = {
 "whitefly:0": {
  "te": "ఎకరానికి 20 పసుపు జిగురు అట్టలు పంట ఎత్తులో పెట్టండి",
  "hi": "एक एकड़ में 20 पीले चिपचिपे ट्रैप फसल की ऊंचाई पर लगाएं",
  "ta": "ஏக்கருக்கு 20 மஞ்சள் ஒட்டும் பொறிகளை பயிர் உயரத்தில் வையுங்கள்",
  "ml": "ഏക്കറിന് 20 മഞ്ഞ പശക്കെണികൾ വിളയുടെ ഉയരത്തിൽ വയ്ക്കൂ"
 },
 "whitefly:1": {
  "te": "సాయంత్రం వేప నూనె (లేదా ఇంట్లో చేసిన వేప గింజల కషాయం) పిచికారీ చేయండి",
  "hi": "शाम को नीम का तेल (या घर का बना नीम बीज अर्क) छिड़कें",
  "ta": "மாலையில் வேப்ப எண்ணெய் (அல்லது வீட்டில் செய்த வேப்பங்கொட்டை கரைசல்) தெளியுங்கள்",
  "ml": "വൈകുന്നേരം വേപ്പെണ്ണ (അല്ലെങ്കിൽ വീട്ടിലുണ്ടാക്കിയ വേപ്പിൻകുരു സത്ത്) തളിക്കൂ"
 },
 "whitefly:2": {
  "te": "తేమ వాతావరణంలో వెర్టిసిలియం లెకాని (జీవ మందు) పిచికారీ చేయండి",
  "hi": "नमी वाले मौसम में वर्टिसिलियम लेकानी (जैविक दवा) छिड़कें",
  "ta": "ஈரப்பதமான காலநிலையில் வெர்டிசிலியம் லெகானி (உயிர் மருந்து) தெளியுங்கள்",
  "ml": "ഈർപ്പമുള്ള കാലാവസ്ഥയിൽ വെർട്ടിസിലിയം ലെക്കാനി (ജൈവ മരുന്ന്) തളിക്കൂ"
 },
 "whitefly:3": {
  "te": "చాలా ఎక్కువగా ఉంటేనే: స్పైరోమెసిఫెన్ లేదా పైరిప్రాక్సిఫెన్. లేబుల్ మోతాదు పాటించండి",
  "hi": "बहुत ज्यादा हो तभी: स्पाइरोमेसिफेन या पाइरिप्रॉक्सीफेन। लेबल की मात्रा ही डालें",
  "ta": "மிக அதிகமாக இருந்தால் மட்டும்: ஸ்பைரோமெசிஃபென் அல்லது பைரிப்ராக்ஸிஃபென். லேபிள் அளவை பின்பற்றுங்கள்",
  "ml": "വളരെ കൂടുതലാണെങ്കിൽ മാത്രം: സ്പൈറോമെസിഫെൻ അല്ലെങ്കിൽ പൈറിപ്രോക്സിഫെൻ. ലേബലിലെ അളവ് പാലിക്കൂ"
 },
 "thrips:0": {
  "te": "ఎకరానికి 20 నీలి జిగురు అట్టలు పెట్టండి",
  "hi": "एक एकड़ में 20 नीले चिपचिपे ट्रैप लगाएं",
  "ta": "ஏக்கருக்கு 20 நீல ஒட்டும் பொறிகள் வையுங்கள்",
  "ml": "ഏക്കറിന് 20 നീല പശക്കെണികൾ വയ്ക്കൂ"
 },
 "thrips:1": {
  "te": "సాయంత్రం వేప నూనె పిచికారీ చేయండి",
  "hi": "शाम को नीम का तेल छिड़कें",
  "ta": "மாலையில் வேப்ப எண்ணெய் தெளியுங்கள்",
  "ml": "വൈകുന്നേരം വേപ്പെണ്ണ തളിക്കൂ"
 },
 "thrips:2": {
  "te": "ఇంకా పెరిగితే: స్పినోసాడ్ లేదా ఫిప్రోనిల్. లేబుల్ మోతాదు పాటించండి",
  "hi": "फिर भी बढ़े तो: स्पिनोसैड या फिप्रोनिल। लेबल की मात्रा ही डालें",
  "ta": "இன்னும் பரவினால்: ஸ்பினோசாட் அல்லது ஃபிப்ரோனில். லேபிள் அளவை பின்பற்றுங்கள்",
  "ml": "ഇനിയും പടർന്നാൽ: സ്പിനോസാഡ് അല്ലെങ്കിൽ ഫിപ്രോനിൽ. ലേബലിലെ അളവ് പാലിക്കൂ"
 },
 "aphids:0": {
  "te": "వేప నూనె పిచికారీ చేయండి; అక్షింతల పురుగులను చంపకండి, అవి పేనును తింటాయి",
  "hi": "नीम का तेल छिड़कें; लेडीबर्ड कीड़ों को न मारें, वे माहू खाते हैं",
  "ta": "வேப்ப எண்ணெய் தெளியுங்கள்; பொறி வண்டுகளை கொல்லாதீர்கள், அவை அசுவினியை தின்னும்",
  "ml": "വേപ്പെണ്ണ തളിക്കൂ; ലേഡിബേർഡ് വണ്ടുകളെ കൊല്ലരുത്, അവ മുഞ്ഞയെ തിന്നും"
 },
 "aphids:1": {
  "te": "ఎక్కువగా ఉంటే: ఫ్లోనికామిడ్. లేబుల్ మోతాదు పాటించండి",
  "hi": "ज्यादा हो तो: फ्लोनिकामिड। लेबल की मात्रा ही डालें",
  "ta": "அதிகமாக இருந்தால்: ஃப்ளோனிகாமிட். லேபிள் அளவை பின்பற்றுங்கள்",
  "ml": "കൂടുതലാണെങ്കിൽ: ഫ്ലോണികാമിഡ്. ലേബലിലെ അളവ് പാലിക്കൂ"
 },
 "borer:0": {
  "te": "ఎకరానికి 5 లింగాకర్షణ బుట్టలు పెట్టి, 3 రోజులకోసారి చూడండి",
  "hi": "एक एकड़ में 5 फेरोमोन ट्रैप लगाएं, हर 3 दिन में देखें",
  "ta": "ஏக்கருக்கு 5 இனக்கவர்ச்சி பொறிகள் வைத்து, 3 நாளுக்கு ஒருமுறை பாருங்கள்",
  "ml": "ഏക്കറിന് 5 ഫെറോമോൺ കെണികൾ വച്ച്, 3 ദിവസത്തിലൊരിക്കൽ നോക്കൂ"
 },
 "borer:1": {
  "te": "పాడైన కాయలు, పండ్లు, ఎండిన మొవ్వలు తీసి నాశనం చేయండి",
  "hi": "खराब टिंडे, फल और सूखी गोभ तोड़कर नष्ट करें",
  "ta": "சேதமான காய்கள், பழங்கள், காய்ந்த குருத்துகளை பறித்து அழியுங்கள்",
  "ml": "കേടായ കായ്കൾ, പഴങ്ങൾ, ഉണങ്ങിയ നാമ്പുകൾ പറിച്ച് നശിപ്പിക്കൂ"
 },
 "borer:2": {
  "te": "10% కంటే ఎక్కువ నష్టం ఉంటే: ఎమామెక్టిన్ బెంజోయేట్ లేదా క్లోరాంట్రానిలిప్రోల్. లేబుల్ మోతాదు పాటించండి",
  "hi": "10% से ज्यादा नुकसान हो तो: इमामेक्टिन बेंजोएट या क्लोरेंट्रानिलिप्रोल। लेबल की मात्रा ही डालें",
  "ta": "10%க்கு மேல் சேதம் இருந்தால்: எமாமெக்டின் பென்சோயேட் அல்லது குளோரான்ட்ரானிலிப்ரோல். லேபிள் அளவை பின்பற்றுங்கள்",
  "ml": "10%ൽ കൂടുതൽ നാശമുണ്ടെങ്കിൽ: ഇമാമെക്ടിൻ ബെൻസോയേറ്റ് അല്ലെങ്കിൽ ക്ലോറാൻട്രാനിലിപ്രോൾ. ലേബലിലെ അളവ് പാലിക്കൂ"
 },
 "leafcurl:0": {
  "te": "బాగా ముడుచుకున్న మొక్కలను త్వరగా పీకి పూడ్చండి: వైరస్‌కు మందు లేదు",
  "hi": "ज्यादा मुड़े पौधे जल्दी उखाड़कर गाड़ दें: वायरस की कोई दवा नहीं",
  "ta": "அதிகம் சுருண்ட செடிகளை உடனே பிடுங்கி புதையுங்கள்: வைரசுக்கு மருந்து இல்லை",
  "ml": "കൂടുതൽ ചുരുണ്ട ചെടികൾ വേഗം പിഴുത് കുഴിച്ചിടൂ: വൈറസിന് മരുന്നില്ല"
 },
 "leafcurl:1": {
  "te": "దీన్ని వ్యాపింపజేసే తెల్ల దోమ, తామర పురుగులను జిగురు అట్టలు, వేప నూనెతో అదుపు చేయండి",
  "hi": "इसे फैलाने वाली सफेद मक्खी और थ्रिप्स को ट्रैप और नीम तेल से रोकें",
  "ta": "இதை பரப்பும் வெள்ளை ஈ, இலைப்பேனை ஒட்டும் பொறி, வேப்ப எண்ணெய் மூலம் கட்டுப்படுத்துங்கள்",
  "ml": "ഇത് പരത്തുന്ന വെള്ളീച്ച, ഇലപ്പേൻ എന്നിവയെ പശക്കെണിയും വേപ്പെണ്ണയും കൊണ്ട് നിയന്ത്രിക്കൂ"
 },
 "leafcurl:2": {
  "te": "ఫోటోతో KVK నిపుణుడిని అడగండి",
  "hi": "फोटो के साथ KVK विशेषज्ञ से पूछें",
  "ta": "புகைப்படத்துடன் KVK நிபுணரிடம் கேளுங்கள்",
  "ml": "ഫോട്ടോയോടൊപ്പം KVK വിദഗ്ധനോട് ചോദിക്കൂ"
 },
 "yellow:0": {
  "te": "మీ సాయిల్ హెల్త్ కార్డ్ చూడండి: నత్రజని లేదా జింక్ తక్కువ ఉండొచ్చు",
  "hi": "मृदा स्वास्थ्य कार्ड देखें: नाइट्रोजन या जिंक कम हो सकता है",
  "ta": "மண் வள அட்டையை பாருங்கள்: தழைச்சத்து அல்லது துத்தநாகம் குறைவாக இருக்கலாம்",
  "ml": "മണ്ണ് ആരോഗ്യ കാർഡ് നോക്കൂ: നൈട്രജനോ സിങ്കോ കുറവായിരിക്കാം"
 },
 "yellow:1": {
  "te": "నిలిచిన నీటిని తీసేయండి: వేర్లు మునిగితే ఆకులు పసుపు అవుతాయి",
  "hi": "खड़ा पानी निकालें: जड़ें डूबने से पत्ते पीले होते हैं",
  "ta": "தேங்கிய நீரை வடியுங்கள்: வேர் மூழ்கினால் இலை மஞ்சளாகும்",
  "ml": "കെട്ടിനിൽക്കുന്ന വെള്ളം ഒഴുക്കിക്കളയൂ: വേര് മുങ്ങിയാൽ ഇല മഞ്ഞളിക്കും"
 },
 "yellow:2": {
  "te": "సాయిల్ కార్డ్ ప్రకారం యూరియా లేదా జింక్ సల్ఫేట్ వేయండి",
  "hi": "कार्ड के अनुसार यूरिया या जिंक सल्फेट डालें",
  "ta": "அட்டையின்படி யூரியா அல்லது துத்தநாக சல்பேட் இடுங்கள்",
  "ml": "കാർഡ് പ്രകാരം യൂറിയയോ സിങ്ക് സൾഫേറ്റോ ഇടൂ"
 },
 "spots:0": {
  "te": "బాగా తెగులు వచ్చిన ఆకులు తీసి కాల్చండి; ఇప్పుడు యూరియా ఎక్కువ వేయకండి",
  "hi": "ज्यादा बीमार पत्ते तोड़कर जला दें; अभी ज्यादा यूरिया न डालें",
  "ta": "நோய் அதிகமான இலைகளை பறித்து எரியுங்கள்; இப்போது யூரியா அதிகம் இடாதீர்கள்",
  "ml": "രോഗം കൂടിയ ഇലകൾ പറിച്ച് കത്തിക്കൂ; ഇപ്പോൾ യൂറിയ കൂടുതൽ ഇടരുത്"
 },
 "spots:1": {
  "te": "సూడోమోనాస్ ఫ్లోరెసెన్స్ (జీవ మందు) పిచికారీ చేయండి",
  "hi": "स्यूडोमोनास फ्लोरेसेंस (जैविक दवा) छिड़कें",
  "ta": "சூடோமோனாஸ் ஃப்ளோரசன்ஸ் (உயிர் மருந்து) தெளியுங்கள்",
  "ml": "സ്യൂഡോമോണാസ് ഫ്ലൂറസൻസ് (ജൈവ മരുന്ന്) തളിക്കൂ"
 },
 "spots:2": {
  "te": "వరి అగ్గి తెగులు: ట్రైసైక్లజోల్. కాండం కుళ్ళు: హెక్సాకొనజోల్. గోధుమ తుప్పు: ప్రొపికొనజోల్. లేబుల్ మోతాదు పాటించండి",
  "hi": "धान झोंका: ट्राइसाइक्लाज़ोल। शीथ ब्लाइट: हेक्साकोनाज़ोल। गेहूं रतुआ: प्रोपिकोनाज़ोल। लेबल की मात्रा ही डालें",
  "ta": "நெல் குலை நோய்: ட்ரைசைக்ளசோல். இலையுறை கருகல்: ஹெக்ஸாகொனசோல். கோதுமை துரு: ப்ரோபிகொனசோல். லேபிள் அளவை பின்பற்றுங்கள்",
  "ml": "നെല്ലിലെ ബ്ലാസ്റ്റ്: ട്രൈസൈക്ലസോൾ. പോളരോഗം: ഹെക്സാകൊണസോൾ. ഗോതമ്പ് തുരുമ്പ്: പ്രൊപികൊണസോൾ. ലേബലിലെ അളവ് പാലിക്കൂ"
 },
 "wilt:0": {
  "te": "ట్రైకోడెర్మా విరిడిని ఎరువులో కలిపి వేర్ల దగ్గర పోయండి",
  "hi": "ट्राइकोडर्मा विरिडी को खाद में मिलाकर जड़ों में डालें",
  "ta": "ட்ரைக்கோடெர்மா விரிடியை உரத்தில் கலந்து வேர் பகுதியில் ஊற்றுங்கள்",
  "ml": "ട്രൈക്കോഡെർമ വിരിഡി കമ്പോസ്റ്റിൽ കലർത്തി വേരിനടുത്ത് ഒഴിക്കൂ"
 },
 "wilt:1": {
  "te": "నీరు బయటకు పోయేలా చేయండి; ఎక్కువ నీరు పెట్టకండి",
  "hi": "पानी निकलने का रास्ता बनाएं; ज्यादा पानी न दें",
  "ta": "நீர் வடிய வழி செய்யுங்கள்; அதிகம் நீர் பாய்ச்சாதீர்கள்",
  "ml": "വെള്ളം ഒഴുകിപ്പോകാൻ വഴിയൊരുക്കൂ; കൂടുതൽ നനയ്ക്കരുത്"
 }
}
