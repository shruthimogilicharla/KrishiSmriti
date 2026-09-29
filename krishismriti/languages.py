"""Supported languages. `code` works for Groq Whisper (speech-to-text) and gTTS (text-to-speech)."""

LANGUAGES = {
    "te": {"name": "Telugu", "native": "తెలుగు"},
    "hi": {"name": "Hindi", "native": "हिन्दी"},
    "ta": {"name": "Tamil", "native": "தமிழ்"},
    "ml": {"name": "Malayalam", "native": "മലയാളം"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    "mr": {"name": "Marathi", "native": "मराठी"},
    "bn": {"name": "Bengali", "native": "বাংলা"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "en": {"name": "English", "native": "English"},
}


def lang_name(code: str) -> str:
    return LANGUAGES.get(code, LANGUAGES["en"])["name"]


# Short fixed phrases used by the offline demo mode and follow-up prompts.
# Only the core demo languages are hand-written; others fall back to English
# (with a Groq key the LLM writes every language itself).
PHRASES = {
    "followup": {
        "en": "{days} days ago you used {product} for {target}. Did it work?",
        "hi": "{days} दिन पहले आपने {target} के लिए {product} डाला था। क्या फायदा हुआ?",
        "te": "{days} రోజుల క్రితం {target} కోసం {product} వాడారు. పని చేసిందా?",
        "ta": "{days} நாட்களுக்கு முன் {target}க்கு {product} பயன்படுத்தினீர்கள். பலன் கிடைத்ததா?",
        "ml": "{days} ദിവസം മുമ്പ് {target}ന് {product} ഉപയോഗിച്ചു. ഫലം കിട്ടിയോ?",
    },
    "avoid": {
        "en": "Do not spray {product} again. It failed {n} times on this plot. You save ₹{cost}.",
        "hi": "{product} दोबारा मत डालिए। इस खेत में यह {n} बार फेल हुआ है। आपके ₹{cost} बचेंगे।",
        "te": "{product} మళ్ళీ కొట్టకండి. ఈ పొలంలో {n} సార్లు పని చేయలేదు. మీకు ₹{cost} మిగులుతుంది.",
        "ta": "{product} மீண்டும் தெளிக்க வேண்டாம். இந்த நிலத்தில் {n} முறை பலன் இல்லை. ₹{cost} மிச்சம்.",
        "ml": "{product} വീണ്ടും തളിക്കരുത്. ഈ പാടത്ത് {n} തവണ ഫലിച്ചില്ല. ₹{cost} ലാഭിക്കാം.",
    },
    "reuse": {
        "en": "Last time {product} worked well and the crop stayed healthy for {days} days. Use it again.",
        "hi": "पिछली बार {product} से फायदा हुआ था, फसल {days} दिन स्वस्थ रही। फिर से वही इस्तेमाल करें।",
        "te": "పోయినసారి {product} బాగా పని చేసింది, పంట {days} రోజులు ఆరోగ్యంగా ఉంది. మళ్ళీ అదే వాడండి.",
        "ta": "கடந்த முறை {product} நன்றாக வேலை செய்தது, பயிர் {days} நாட்கள் நலமாக இருந்தது. மீண்டும் அதையே பயன்படுத்துங்கள்.",
        "ml": "കഴിഞ്ഞ തവണ {product} നന്നായി ഫലിച്ചു, വിള {days} ദിവസം ആരോഗ്യത്തോടെ നിന്നു. വീണ്ടും അതുതന്നെ ഉപയോഗിക്കൂ.",
    },
    "no_spray_weather": {
        "en": "Rain or strong wind is expected in the next 24 hours. Wait before spraying.",
        "hi": "अगले 24 घंटे में बारिश या तेज हवा की संभावना है। अभी छिड़काव मत कीजिए।",
        "te": "రాబోయే 24 గంటల్లో వర్షం లేదా గాలి ఎక్కువ. ఇప్పుడు పిచికారీ చేయకండి.",
        "ta": "அடுத்த 24 மணி நேரத்தில் மழை அல்லது பலத்த காற்று வரலாம். இப்போது தெளிக்க வேண்டாம்.",
        "ml": "അടുത്ത 24 മണിക്കൂറിൽ മഴയോ ശക്തമായ കാറ്റോ ഉണ്ടാകാം. ഇപ്പോൾ തളിക്കരുത്.",
    },
    "options": {
        "en": "For {problem}, safe options for your plot are on the screen. Start with the first one.",
        "hi": "{problem} के लिए आपके खेत के सुरक्षित उपाय स्क्रीन पर हैं। पहले वाले से शुरू करें।",
        "te": "{problem} కోసం మీ పొలానికి సురక్షితమైన మార్గాలు స్క్రీన్ మీద ఉన్నాయి. మొదటిది ముందు చేయండి.",
        "ta": "{problem}க்கு உங்கள் நிலத்திற்கு பாதுகாப்பான வழிகள் திரையில் உள்ளன. முதலாவதை முதலில் செய்யுங்கள்.",
        "ml": "{problem}ന് നിങ്ങളുടെ പാടത്തിന് സുരക്ഷിതമായ വഴികൾ സ്ക്രീനിൽ ഉണ്ട്. ആദ്യത്തേത് ആദ്യം ചെയ്യൂ.",
    },
    "unknown": {
        "en": "I could not find this problem in your farm memory. Tap a picture of what you see, or send it to the expert.",
        "hi": "यह समस्या आपके खेत की याद में नहीं मिली। जो दिख रहा है उसकी तस्वीर दबाइए, या विशेषज्ञ को भेजिए।",
        "te": "ఈ సమస్య మీ పొలం జ్ఞాపకంలో దొరకలేదు. మీకు కనిపించే దాని బొమ్మను నొక్కండి, లేదా నిపుణుడికి పంపండి.",
        "ta": "இந்த பிரச்சனை உங்கள் நில நினைவில் இல்லை. நீங்கள் பார்ப்பதன் படத்தை அழுத்துங்கள், அல்லது நிபுணருக்கு அனுப்புங்கள்.",
        "ml": "ഈ പ്രശ്നം നിങ്ങളുടെ പാട ഓർമ്മയിൽ ഇല്ല. കാണുന്നതിന്റെ ചിത്രം അമർത്തൂ, അല്ലെങ്കിൽ വിദഗ്ധന് അയക്കൂ.",
    },
    "same_group": {
        "en": "{product} is the same chemical group as {failed}, which failed here. It will likely fail too.",
        "hi": "{product} उसी दवा समूह की है जिसकी {failed} यहां फेल हुई। यह भी फेल होगी।",
        "te": "{product} కూడా {failed} లాంటి మందు గుంపుదే. ఇక్కడ అది పని చేయలేదు, ఇదీ పని చేయదు.",
        "ta": "{product} என்பது {failed} போன்ற அதே மருந்து வகை. இங்கு அது பலனில்லை, இதுவும் பலனளிக்காது.",
        "ml": "{product} {failed} പോലെ ഒരേ മരുന്ന് വിഭാഗമാണ്. ഇവിടെ അത് ഫലിച്ചില്ല, ഇതും ഫലിക്കില്ല.",
    },
    "first": {"en": "First: {x}.", "hi": "सबसे पहले: {x}।", "te": "ముందుగా: {x}.", "ta": "முதலில்: {x}.", "ml": "ആദ്യം: {x}."},
    "worked_rec": {
        "en": "{product} again (worked before)", "hi": "{product} फिर से (पहले काम किया था)",
        "te": "మళ్ళీ {product} (ఇంతకు ముందు పని చేసింది)", "ta": "மீண்டும் {product} (முன்பு பலன் கொடுத்தது)",
        "ml": "വീണ്ടും {product} (മുമ്പ് ഫലിച്ചു)",
    },
    "adopt": {
        "en": "Noted. In 7 days I will ask you if it worked.", "hi": "नोट कर लिया। 7 दिन बाद पूछूंगा कि फायदा हुआ या नहीं।",
        "te": "నమోదు చేశాను. 7 రోజుల తర్వాత పని చేసిందా అని అడుగుతాను.", "ta": "பதிவு செய்தேன். 7 நாட்களில் பலன் கிடைத்ததா என்று கேட்பேன்.",
        "ml": "രേഖപ്പെടുത്തി. 7 ദിവസം കഴിഞ്ഞ് ഫലിച്ചോ എന്ന് ചോദിക്കാം.",
    },
    "greet": {
        "en": "Hello {name}", "hi": "नमस्ते {name} जी", "te": "నమస్కారం {name} గారు",
        "ta": "வணக்கம் {name}", "ml": "നമസ്കാരം {name}",
    },
    "outbreak": {
        "en": "Alert: {pest} seen on {n} farms in {village} in the last {days} days. Check your crop today.",
        "hi": "सावधान: पिछले {days} दिनों में {village} के {n} खेतों में {pest} दिखा है। आज अपनी फसल जांचिए।",
        "te": "జాగ్రత్త: గత {days} రోజుల్లో {village}లో {n} పొలాల్లో {pest} కనిపించింది. ఈరోజు మీ పంట చూడండి.",
        "ta": "எச்சரிக்கை: கடந்த {days} நாட்களில் {village}ல் {n} வயல்களில் {pest} தென்பட்டது. இன்று உங்கள் பயிரை பாருங்கள்.",
        "ml": "ജാഗ്രത: കഴിഞ്ഞ {days} ദിവസത്തിൽ {village}ൽ {n} പാടങ്ങളിൽ {pest} കണ്ടു. ഇന്ന് നിങ്ങളുടെ വിള പരിശോധിക്കൂ.",
    },
    "saved": {
        "en": "Saved to your farm memory.",
        "hi": "आपके खेत की याद में सेव हो गया।",
        "te": "మీ పొలం జ్ఞాపకంలో సేవ్ అయింది.",
        "ta": "உங்கள் நில நினைவில் சேமிக்கப்பட்டது.",
        "ml": "നിങ്ങളുടെ പാടത്തിന്റെ ഓർമ്മയിൽ സേവ് ചെയ്തു.",
    },
}


def phrase(key: str, lang: str, **kw) -> str:
    table = PHRASES[key]
    return table.get(lang, table["en"]).format(**kw)
