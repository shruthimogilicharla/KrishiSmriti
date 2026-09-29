"""Groq LLM calls. Every function has an offline fallback so the demo never dies on stage."""
import json
import os
import re
from datetime import date

from agronomy import PRODUCTS, find_products, normalise
from languages import lang_name, phrase

_client = None


def groq_client():
    global _client
    if _client is None and os.getenv("GROQ_API_KEY"):
        from groq import Groq
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30, max_retries=1)
    return _client


def _chat_json(system: str, user, model=None, temperature=0.2) -> dict:
    client = groq_client()
    r = client.chat.completions.create(
        timeout=30,
        model=model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return json.loads(r.choices[0].message.content)


ADVISOR_SYSTEM = """You are KrishiSmriti, a farm advisor for small Indian farmers, many of whom cannot read.
You have this plot's memory (its "medical chart"). Rules:
1. NEVER recommend a product listed under HARD_BLOCK, or any product in the same mode-of-action group. Say clearly not to use it and how much money it wasted.
2. If a treatment WORKED on this plot before for the same problem, recommend it first and say how long it kept the crop healthy.
3. Prefer integrated pest management: traps, botanicals, bio-agents first; chemicals only with a DIFFERENT mode of action.
4. If weather says do not spray, tell them to wait.
5. Never give a dose you are not sure of: say "use the dose on the label or ask the KVK".
6. If unsure of the diagnosis or the problem is serious, set escalate_to_expert true.
7. The "speak" field is read aloud to the farmer in {lang}. Write it ONLY in {lang} script, simple village words, max 70 words, no English jargon, no symbols except ₹.
Return JSON: {{"diagnosis": str, "confidence": "low|medium|high", "do_not_use": [{{"product": str, "reason": str}}],
"recommend": [{{"action": str, "why": str, "est_cost_inr": int, "organic": bool}}], "safety": str,
"escalate_to_expert": bool, "followup_days": int, "speak": str, "english_summary": str}}"""


def advise(question, lang, plot, guard, plot_memories, village_memories, weather, image_note=None, problem=None) -> dict:
    hard_block = [f"{a['product']} ({a['moa']}) failed {a['count']}x, ₹{a['wasted']} wasted" for a in guard["avoid"]]
    ctx = {
        "today": date.today().isoformat(),
        "plot": plot,
        "HARD_BLOCK": hard_block,
        "also_block_same_mode_of_action": guard["avoid_same_moa"],
        "worked_before_on_this_plot": guard["proven"],
        "mode_of_action_groups_failing_in_village": guard.get("village_resistance", []),
        "plot_memory": plot_memories,
        "village_memory_neighbours_and_elders": village_memories,
        "weather_next_24h": weather,
        "photo_observation": image_note,
        "farmer_question": question,
    }
    if groq_client():
        try:
            out = _chat_json(ADVISOR_SYSTEM.format(lang=lang_name(lang)), json.dumps(ctx, ensure_ascii=False))
            out["mode"] = "groq"
            return enforce_guard(out, guard)
        except Exception as e:
            print("[llm] advise failed, using offline rules:", e)
    return offline_advice(lang, guard, weather, problem, question)


def enforce_guard(out: dict, guard: dict) -> dict:
    """Memory beats the model: strip any recommendation the LLM made that memory says has failed."""
    blocked = {a["product"] for a in guard["avoid"]} | set(guard["avoid_same_moa"])
    kept, removed = [], []
    for rec in out.get("recommend", []):
        hits = [p for p in find_products(rec.get("action", "")) if p in blocked]
        (removed if hits else kept).append(rec)
    out["recommend"] = kept
    if removed:
        out["guard_removed"] = removed
    return out


def offline_advice(lang, guard, weather, problem=None, question="") -> dict:
    from agronomy import PROBLEMS, safe_options
    parts, recs, dnu = [], [], []
    if not problem and not find_products(question):
        return {"diagnosis": "Not recognised offline", "confidence": "low", "do_not_use": [], "recommend": [],
                "safety": "", "escalate_to_expert": False, "followup_days": 7, "speak": phrase("unknown", lang),
                "problem": None, "english_summary": "Offline mode could not match the question.", "mode": "offline"}
    targets = PROBLEMS[problem]["targets"] if problem else None
    def rel(x):
        tg = (x.get("target") or "").lower()
        return not targets or (tg != "" and any(t in tg or tg in t for t in targets))
    avoid = [a for a in guard["avoid"] if rel(a)]
    proven = [p for p in guard["proven"] if rel(p)]
    for a in avoid:
        dnu.append({"product": a["product"], "reason": f"Failed {a['count']}x on this plot, ₹{a['wasted']} wasted"})
        parts.append(phrase("avoid", lang, product=a["product"].title(), n=a["count"], cost=a["wasted"] // max(a["count"], 1)))
    for p in proven[:1]:
        recs.append({"action": phrase("worked_rec", lang, product=p["product"].title()), "product": p["product"],
                     "target": p.get("target"), "why": f"Kept crop healthy {p['best_days']} days on this plot",
                     "est_cost_inr": p["cost"], "organic": PRODUCTS.get(p["product"], ("", "", False))[2]})
        parts.append(phrase("reuse", lang, product=p["product"].title(), days=p["best_days"]))
    if problem:
        seen = {r["product"] for r in recs}
        recs += [o for o in safe_options(problem, guard, lang) if not o["product"] or o["product"] not in seen]
        name = PROBLEMS[problem]["names"].get(lang, PROBLEMS[problem]["names"]["en"])
        parts.append(phrase("options", lang, problem=name))
        if recs and not proven:
            parts.append(phrase("first", lang, x=recs[0]["action"]))
    if weather and not weather["ok_to_spray"]:
        parts.append(phrase("no_spray_weather", lang))
    if not parts:
        parts.append(phrase("unknown", lang))
    speak = " ".join(parts)
    return {"diagnosis": "Matched against plot memory (offline rules mode)", "confidence": "medium",
            "do_not_use": dnu, "recommend": recs, "safety": "Wear gloves and mask. Follow the label dose.",
            "escalate_to_expert": not recs and not problem, "followup_days": 7, "speak": speak, "problem": problem,
            "english_summary": "Offline mode: advice built only from this plot's memory.", "mode": "offline"}


EXTRACT_SYSTEM = """Extract one farm record from a farmer's spoken note (may be in any Indian language or mixed).
Today is {today}. Convert relative dates ("yesterday", "last week") to ISO dates.
Product names: return the generic chemical/bio name in English lowercase if you can (e.g. "confidor" -> "imidacloprid", "vepa nune" -> "neem oil").
Return JSON: {{"type": "treatment|seed|fertilizer|soil_test|observation|harvest", "product": str|null, "target": str|null (pest/disease in English),
"cost": int|null (rupees), "date": "YYYY-MM-DD", "outcome": "pending|worked|failed|partial", "days_healthy": int|null,
"notes": str (short English summary), "confirm": str (one short sentence in {lang} repeating what was saved)}}"""


def extract_event(text: str, lang: str) -> dict:
    if groq_client():
        try:
            return _chat_json(EXTRACT_SYSTEM.format(today=date.today().isoformat(), lang=lang_name(lang)), text, temperature=0)
        except Exception as e:
            print("[llm] extract failed:", e)
    prods = find_products(text)
    cost = re.search(r"(?:₹|rs\.?|rupees?)\s*(\d{2,6})|(\d{2,6})\s*(?:₹|rs|rupees)", text.lower())
    t = text.lower()
    outcome = "failed" if any(w in t for w in ["failed", "no use", "didn't work", "not work"]) else \
              "worked" if any(w in t for w in ["worked", "fixed", "cured"]) else "pending"
    return {"type": "treatment" if prods else "observation", "product": normalise(prods[0]) if prods else None,
            "target": next((p for p in ["whitefly", "aphid", "thrips", "bollworm", "rust", "blight", "mites"] if p in t), None),
            "cost": int(next(g for g in cost.groups() if g)) if cost else None, "date": date.today().isoformat(),
            "outcome": outcome, "days_healthy": None, "notes": text[:200], "confirm": phrase("saved", lang)}


def describe_photo(image_b64: str, mime: str) -> str | None:
    client = groq_client()
    if not client:
        return None
    try:
        r = client.chat.completions.create(
            model=os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"),
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "You are a plant pathologist. Describe the crop, visible symptoms and the most likely "
                                         "pest or disease (top 2 with confidence). Max 60 words."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
            ]}],
            temperature=0.1,
        )
        return r.choices[0].message.content
    except Exception as e:
        print("[llm] vision failed:", e)
        return None


def plot_report(plot, events, lang) -> str:
    """Season summary in plain language (fallback when Hindsight reflect is not available)."""
    if groq_client():
        try:
            out = _chat_json(
                f"Summarise this farm plot's history for the farmer in {lang_name(lang)}: what worked, what failed, money wasted, "
                f"and 3 things to do next season. Max 90 words. Return JSON {{\"summary\": str}}",
                json.dumps({"plot": plot, "events": events}, ensure_ascii=False))
            return out["summary"]
        except Exception as e:
            print("[llm] report failed:", e)
    worked = [e for e in events if e.get("outcome") == "worked"]
    failed = [e for e in events if e.get("outcome") == "failed"]
    return (f"{len(events)} records. Worked: {', '.join(sorted({e['product'] for e in worked})) or 'none'}. "
            f"Failed: {', '.join(sorted({e['product'] for e in failed})) or 'none'} "
            f"(₹{sum(int(e.get('cost') or 0) for e in failed)} wasted).")


def translate(text: str, lang: str) -> str:
    """Plain-language translation for read-aloud. Returns the input unchanged when offline or English."""
    if lang == "en" or not groq_client():
        return text
    try:
        out = _chat_json(f"Translate for a farmer who cannot read, into simple spoken {lang_name(lang)} in {lang_name(lang)} script. "
                         "Keep product names and numbers. Return JSON {\"text\": str}", text, temperature=0)
        return out["text"]
    except Exception as e:
        print("[llm] translate failed:", e)
        return text


BILL_SYSTEM = """You read photos of Indian agri-input shop bills or a farmer's handwritten notebook.
Extract every pesticide, fungicide, fertiliser or seed line. Map brand names to generic names in English lowercase
(e.g. Confidor -> imidacloprid, Coragen -> chlorantraniliprole). Return JSON:
{"items": [{"type": "treatment|fertilizer|seed", "product": str, "brand": str|null, "quantity": str|null,
"cost": int|null, "date": "YYYY-MM-DD"|null}], "shop": str|null}"""


def scan_bill(image_b64: str, mime: str) -> dict:
    client = groq_client()
    if not client:
        raise RuntimeError("Bill scanning needs GROQ_API_KEY.")
    r = client.chat.completions.create(
        model=os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"),
        messages=[{"role": "system", "content": BILL_SYSTEM}, {"role": "user", "content": [
            {"type": "text", "text": "Extract the items from this bill or notebook page."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}],
        response_format={"type": "json_object"}, temperature=0)
    return json.loads(r.choices[0].message.content)
