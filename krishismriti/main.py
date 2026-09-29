"""KrishiSmriti: every farm plot gets its own memory.
Run:  uvicorn main:app --reload   (or double-click run.bat on Windows)
Farmer app:        http://localhost:8000
Field-agent desk:  http://localhost:8000/agent
Plot passport:     http://localhost:8000/passport/PLOT-14
"""
import base64
import os
import uuid
from collections import defaultdict
from datetime import date
from xml.sax.saxutils import escape as xesc

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import llm
import voice
from agronomy import PROBLEMS, check_mentions, detect_problem, find_products, moa, resistance_guard
from catalog import cards_for
from crops import SCHEMES, crop_stage, market
from languages import LANGUAGES, phrase
from memory import FarmMemory
from seed import seed
from weather import spray_window

BASE = os.path.dirname(__file__)
MEDIA = os.path.join(BASE, "data", "media")
os.makedirs(MEDIA, exist_ok=True)

app = FastAPI(title="KrishiSmriti")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
app.mount("/media", StaticFiles(directory=MEDIA), name="media")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))
mem = FarmMemory()
seed(mem)
mem.seed_hindsight()


def _plot_or_404(pid):
    p = mem.plot(pid)
    if not p:
        raise HTTPException(404, f"Plot {pid} not found")
    return p


async def _input_text(text, audio, lang):
    if audio is not None and audio.filename:
        data = await audio.read()
        if data:
            try:
                return voice.transcribe(data, audio.filename, lang), True
            except Exception as e:
                if not text:
                    raise HTTPException(400, str(e))
    if not text:
        raise HTTPException(400, "Speak or type something")
    return text, False


# ======================= pages =======================
@app.get("/", response_class=HTMLResponse)
async def ui(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/agent", response_class=HTMLResponse)
async def agent_ui(request: Request):
    return templates.TemplateResponse(request, "agent.html", {})


@app.get("/passport/{pid}", response_class=HTMLResponse)
async def passport(request: Request, pid: str):
    """Printable plot record: for crop insurance claims, bank loans, dealers and export buyers."""
    p = _plot_or_404(pid)
    ev = mem.events(pid)
    qr = None
    try:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.make(str(request.url), image_factory=qrcode.image.svg.SvgPathImage).to_string().decode()
    except Exception:
        pass
    return templates.TemplateResponse(request, "passport.html", {
        "p": p, "events": ev, "guard": resistance_guard(ev), "qr": qr, "today": date.today().isoformat(),
        "stage": crop_stage(p.get("crop_key"), p.get("sown")), "moa": moa,
        "spent": sum(int(e.get("cost") or 0) for e in ev)})


# ======================= core API =======================
@app.get("/api/status")
def status():
    return {"memory": mem.backend, "llm": "groq" if llm.groq_client() else "offline-rules", "languages": LANGUAGES,
            "server_voice": bool(llm.groq_client())}


@app.get("/api/plots")
def plots():
    return mem.plots()


@app.post("/api/plots")
def add_plot(plot: dict):
    for k in ("id", "farmer", "village", "crop"):
        if not plot.get(k):
            raise HTTPException(400, f"{k} required")
    plot.setdefault("joined", date.today().isoformat())
    return mem.add_plot(plot)


def _ledger(pid):
    ev = mem.events(pid)
    savings = [s for s in mem.store["savings"] if s["plot_id"] == pid.upper()]
    return {"total_spent": sum(int(e.get("cost") or 0) for e in ev),
            "wasted_on_failures": sum(int(e.get("cost") or 0) for e in ev if e.get("outcome") == "failed"),
            "saved_by_memory": sum(s["amount"] for s in savings), "savings": savings}


@app.get("/api/plots/{pid}")
def plot_detail(pid: str):
    p = _plot_or_404(pid)
    ev = mem.events(pid)
    return {"plot": p, "timeline": ev[::-1], "guard": resistance_guard(ev), "followups": mem.due_followups(pid),
            "ledger": _ledger(pid)}


@app.get("/api/home/{pid}")
def home(pid: str, lang: str = "te"):
    """Everything for the farmer's home screen in one call."""
    p = _plot_or_404(pid)
    outbreaks = [o for o in mem.outbreaks(p["village"])]
    alerts = [{"kind": "outbreak", "level": "warn", **o,
               "text": phrase("outbreak", lang, pest=o["pest"], n=o["count"], village=o["village"], days=o["days"])}
              for o in outbreaks]
    inbox = [m for m in mem.store["inbox"] if m["plot_id"] == p["id"]][::-1]
    stage = crop_stage(p.get("crop_key"), p.get("sown"))
    if stage:
        stage["buy"] = cards_for(stage["tasks"], p.get("district", ""), limit=3)
    return {"plot": p, "greeting": phrase("greet", lang, name=p["farmer"].split()[0]),
            "stage": stage,
            "weather": spray_window(p["lat"], p["lon"]) if p.get("lat") else None,
            "alerts": alerts, "followups_due": len(mem.due_followups(pid)), "inbox": inbox,
            "ledger": _ledger(pid), "market": market(p.get("crop_key", ""), p["district"], p["state"]),
            "allergy": resistance_guard(mem.events(pid))["avoid"]}


def run_ask(plot, question, lang, image_note=None):
    """The KrishiSmriti pipeline: recall -> guard -> weather -> LLM -> enforce guard."""
    plot_id = plot["id"]
    events = mem.events(plot_id)
    guard = resistance_guard(events)
    q = question + (" " + image_note if image_note else "")
    plot_mem = mem.recall(plot_id, q)
    village_mem = mem.recall_village(plot["village"], q, exclude_pid=plot_id)
    weather = spray_window(plot["lat"], plot["lon"]) if plot.get("lat") else None

    warnings = check_mentions(question, guard)
    problem = detect_problem(q)
    targets = PROBLEMS[problem]["targets"] if problem else []
    mentioned_groups = {moa(p) for p in find_products(question)} - {None}
    # Village resistance map: same mode of action failing on neighbouring plots = local resistance
    neighbour_ev = [e for e in mem.store["events"]
                    if e["plot_id"] != plot_id and mem.plot(e["plot_id"])["village"] == plot["village"]]
    vg = resistance_guard(neighbour_ev)
    for a in vg["avoid"]:
        tg = (a.get("target") or "").lower()
        relevant = a["moa"] in mentioned_groups or (tg and any(t in tg or tg in t for t in targets))
        if a["moa"] and relevant and not any(w["product"] == a["product"] for w in warnings):
            warnings.append({"level": "warn", "product": a["product"],
                             "reason": f"Also failed on {a['count']} neighbouring plot(s) in {plot['village']}. "
                                       f"Likely local resistance to {a['moa']}."})
    guard["village_resistance"] = vg["blocked_groups"]
    for w in warnings:  # farmer asked about a product memory knows is a waste -> money saved
        f = next((a for a in guard["avoid"] if a["product"] == w["product"]), None)
        if f and w["level"] == "danger":
            mem.add_saving(plot_id, f["product"], f["wasted"] // f["count"], "Farmer asked to repeat a failed spray; blocked")

    advice = llm.advise(question, lang, plot, guard, plot_mem, village_mem, weather, image_note, problem)
    advice.setdefault("problem", problem)
    for rec in advice.get("recommend", []):  # buy cards: name, natural/chemical, price, where to buy
        if "buy_keys" in rec:        # offline option: exact products
            src = rec.pop("buy_keys")
        elif rec.get("product"):     # "worked before" item
            src = [rec["product"]]
        else:                        # LLM text: find product names in it
            src = [rec.get("action", ""), rec.get("why", "")]
        rec["buy"] = cards_for(src, plot.get("district", ""))
    if advice.get("mode") == "offline":  # say out loud why the product they asked about is a bad idea
        failed = guard["avoid"][0]["product"] if guard["avoid"] else None
        extra = [phrase("same_group", lang, product=w["product"].title(), failed=failed.title())
                 for w in warnings if w["level"] == "warn" and failed and w["product"] in find_products(question)]
        if extra:
            advice["speak"] = " ".join(extra) + " " + advice["speak"]
    esc = None
    if advice.get("escalate_to_expert"):
        esc = mem.escalate(plot_id, question, advice.get("english_summary", ""), lang, image_note)
    return {"question": question, "photo_observation": image_note, "warnings": warnings, "guard": guard,
            "weather": weather, "memories_used": {"plot": plot_mem, "village": village_mem},
            "advice": advice, "escalation": esc}


@app.post("/api/ask")
async def ask(plot_id: str = Form(...), lang: str = Form("te"), text: str = Form(None),
              audio: UploadFile = File(None), photo: UploadFile = File(None)):
    plot = _plot_or_404(plot_id)
    question, was_voice = await _input_text(text, audio, lang)
    image_note = None
    if photo is not None and photo.filename:
        data = await photo.read()
        image_note = llm.describe_photo(base64.b64encode(data).decode(), photo.content_type or "image/jpeg")
    out = run_ask(plot, question, lang, image_note)
    out["was_voice"] = was_voice
    out["audio_b64"] = voice.speak(out["advice"]["speak"], lang)
    return out


@app.post("/api/log")
async def log(plot_id: str = Form(...), lang: str = Form("te"), text: str = Form(None), audio: UploadFile = File(None)):
    """Farmer says 'I sprayed Confidor yesterday, 850 rupees' -> structured memory."""
    _plot_or_404(plot_id)
    said, _ = await _input_text(text, audio, lang)
    saved, confirm = _save_spoken(plot_id, said, lang)
    return {"heard": said, "event": saved, "confirm": confirm, "audio_b64": voice.speak(confirm, lang)}


def _save_spoken(plot_id, said, lang):
    ev = llm.extract_event(said, lang)
    confirm = ev.pop("confirm", None) or phrase("saved", lang)
    ev = {k: v for k, v in ev.items() if v not in (None, "")}
    ev.update(plot_id=plot_id, source="voice", raw=said, lang=lang)
    if ev.get("type") not in ("treatment", "seed", "fertilizer", "soil_test", "observation", "harvest"):
        ev["type"] = "observation"
    return mem.add_event(ev), confirm


@app.post("/api/scan-bill")
async def scan_bill(plot_id: str = Form(...), lang: str = Form("te"), photo: UploadFile = File(...)):
    """Cold start: photo of old shop bills / notebook -> seasons of history in one tap."""
    _plot_or_404(plot_id)
    data = await photo.read()
    try:
        parsed = llm.scan_bill(base64.b64encode(data).decode(), photo.content_type or "image/jpeg")
    except Exception as e:
        raise HTTPException(400, str(e))
    saved = []
    for it in parsed.get("items", []):
        if not it.get("product"):
            continue
        ev = {"plot_id": plot_id, "type": it.get("type") or "treatment", "product": it["product"],
              "cost": it.get("cost"), "date": it.get("date") or date.today().isoformat(), "source": "bill-scan",
              "notes": f"From bill: {it.get('brand') or ''} {it.get('quantity') or ''}".strip()}
        saved.append(mem.add_event({k: v for k, v in ev.items() if v is not None}))
    msg = f"{len(saved)} items added to memory. I will ask you if each spray worked."
    return {"shop": parsed.get("shop"), "saved": saved, "message": msg, "audio_b64": voice.speak(llm.translate(msg, lang), lang)}


@app.get("/api/followups")
def followups(plot_id: str = None, lang: str = "te"):
    out = []
    for f in mem.due_followups(plot_id):
        e = f["event"]
        days = (date.today() - date.fromisoformat(e["date"])).days
        q = phrase("followup", lang, days=days, product=e.get("product", ""), target=e.get("target") or "")
        out.append({**f, "question": q, "audio_b64": voice.speak(q, lang)})
    return out


@app.post("/api/followups/{fid}")
def answer_followup(fid: str, body: dict):
    ev = mem.close_followup(fid, body.get("outcome", "worked"), body.get("days_healthy"), body.get("notes"))
    if not ev:
        raise HTTPException(404, "follow-up not found")
    return {"event": ev}


@app.get("/api/plots/{pid}/report")
def report(pid: str, lang: str = "en"):
    """Season report. Uses Hindsight reflect when connected (reasons over the whole memory)."""
    p = _plot_or_404(pid)
    text = mem.reflect(pid, f"What has worked and failed on plot {p['id']}, how much money was wasted, "
                            f"and what should the farmer do next season? Answer in {LANGUAGES.get(lang, {}).get('name', 'English')}.")
    source = "hindsight-reflect"
    if not text:
        text, source = llm.plot_report(p, mem.events(pid), lang), "llm-summary"
    return {"report": text, "source": source, "audio_b64": voice.speak(text, lang)}


@app.post("/api/speak")
def speak(body: dict):
    """Read any card aloud in the farmer's language (translates first when a Groq key is set).
    If the text could not be translated and is still English, read it with an English voice
    instead of a Telugu/Hindi voice mangling English words."""
    lang = body.get("lang", "en")
    src = body.get("text", "")
    text = llm.translate(src, lang)
    voice_lang = lang
    if text == src and lang != "en" and src.isascii():
        voice_lang = "en"
    return {"text": text, "voice_lang": voice_lang, "audio_b64": voice.speak(text, voice_lang)}


@app.post("/api/adopt")
def adopt(body: dict):
    """Farmer taps "I'll do this" on a recommendation -> pending treatment + 7-day follow-up. Closes the loop
    without the farmer having to report it separately."""
    p = _plot_or_404(body["plot_id"])
    lang = body.get("lang", p.get("lang", "te"))
    product = body.get("product") or next(iter(find_products(body.get("action", ""))), None)
    ev = mem.add_event({"plot_id": p["id"], "type": "treatment" if product else "observation",
                        "product": product or None, "target": body.get("target"), "cost": body.get("cost"),
                        "notes": "Chosen from KrishiSmriti advice: " + body.get("action", "")[:160], "source": "advice"})
    msg = phrase("adopt", lang)
    return {"event": ev, "message": msg, "audio_b64": voice.speak(msg, lang)}


@app.get("/api/market/{crop_key}")
def market_api(crop_key: str, district: str = "Guntur", state: str = "Andhra Pradesh"):
    return market(crop_key, district, state)


@app.get("/api/problems")
def problems():
    """Picture menu for farmers who can't type: tap what you see."""
    from agronomy import PROBLEMS
    return [{"key": k, "names": v["names"], "img": f"/static/img/{k}.svg"} for k, v in PROBLEMS.items()]


@app.get("/api/schemes")
def schemes():
    return SCHEMES


@app.post("/api/inbox/{mid}/read")
def inbox_read(mid: str):
    for m in mem.store["inbox"]:
        if m["id"] == mid:
            m["read"] = True
    mem.save()
    return {"ok": True}


@app.post("/api/escalate")
def escalate(body: dict):
    p = _plot_or_404(body["plot_id"])
    return mem.escalate(p["id"], body.get("question", ""), body.get("ai_answer", ""), body.get("lang", "te"))


# ======================= community / elders =======================
@app.post("/api/elder")
async def elder(village: str = Form(...), elder_name: str = Form(...), lang: str = Form("te"),
                text: str = Form(None), audio: UploadFile = File(None)):
    said, _ = await _input_text(text, audio, lang)
    item = mem.add_elder({"village": village, "elder": elder_name, "text": said, "lang": lang})
    return {"item": item, "audio_b64": voice.speak(phrase("saved", lang), lang)}


@app.get("/api/village/{village}")
def village(village: str):
    stats = defaultdict(lambda: {"worked": 0, "failed": 0, "plots": set()})
    for e in mem.store["events"]:
        p = mem.plot(e["plot_id"])
        if p["village"].lower() != village.lower() or e.get("type") != "treatment" or e.get("outcome") not in ("worked", "failed"):
            continue
        key = (e.get("target") or "?", e["product"])
        stats[key][e["outcome"]] += 1
        stats[key]["plots"].add(e["plot_id"])
    rows = [{"problem": k[0], "product": k[1], "moa": moa(k[1]), "worked": v["worked"], "failed": v["failed"],
             "plots": len(v["plots"])} for k, v in stats.items()]
    rows.sort(key=lambda r: (r["problem"], -(r["worked"] - r["failed"])))
    return {"village": village, "treatments": rows, "outbreaks": mem.outbreaks(village),
            "elder_knowledge": [x for x in mem.store["elder"] if x["village"].lower() == village.lower() and not x.get("rejected")],
            "farmers": sum(1 for p in mem.plots() if p["village"].lower() == village.lower())}


# ======================= field agent / KVK desk =======================
@app.get("/api/agent/overview")
def agent_overview():
    plots_ = mem.plots()
    ev = mem.store["events"]
    treats = [e for e in ev if e.get("type") == "treatment"]
    groups = sorted({moa(e["product"]) for e in ev if e.get("outcome") == "failed" and moa(e.get("product", ""))
                     and "Botanical" not in (moa(e["product"]) or "")})
    villages = sorted({p["village"] for p in plots_})
    heat = []
    for v in villages:
        vids = {p["id"] for p in plots_ if p["village"] == v}
        cells = {g: sum(1 for e in ev if e["plot_id"] in vids and e.get("outcome") == "failed" and moa(e.get("product", "")) == g)
                 for g in groups}
        heat.append({"village": v, "cells": cells, "farmers": len(vids)})
    farmers = []
    for p in plots_:
        pev = mem.events(p["id"])
        last = pev[-1]["date"] if pev else None
        farmers.append({**p, "records": len(pev), "last_active": last, "ledger": _ledger(p["id"]),
                        "stage": (crop_stage(p.get("crop_key"), p.get("sown")) or {}).get("stage"),
                        "followups_due": len(mem.due_followups(p["id"])),
                        "allergies": [a["product"] for a in resistance_guard(pev)["avoid"]]})
    total_saved = sum(s["amount"] for s in mem.store["savings"])
    total_wasted = sum(int(e.get("cost") or 0) for e in ev if e.get("outcome") == "failed")
    return {
        "kpis": {"farmers": len(plots_), "villages": len(villages), "records": len(ev),
                 "voice_records": sum(1 for e in ev if e.get("source") in ("voice", "whatsapp")),
                 "saved": total_saved, "wasted_before": total_wasted,
                 "followup_rate": round(sum(1 for e in treats if e.get("outcome") in ("worked", "failed", "partial"))
                                        / len(treats) * 100) if treats else 0,
                 "open_escalations": sum(1 for e in mem.store["escalations"] if e["status"] == "open")},
        "heatmap": {"groups": groups, "rows": heat},
        "outbreaks": mem.outbreaks(),
        "escalations": sorted(mem.store["escalations"], key=lambda e: (e["status"] != "open", e["created"]), reverse=False),
        "elder_pending": [x for x in mem.store["elder"] if not x["verified"] and not x.get("rejected")],
        "farmers": farmers,
    }


@app.post("/api/escalations/{eid}/answer")
def answer_escalation(eid: str, body: dict):
    esc = next((e for e in mem.store["escalations"] if e["id"] == eid), None)
    if not esc:
        raise HTTPException(404, "not found")
    farmer_text = llm.translate(body["answer"], esc.get("lang", "en"))
    return mem.answer_escalation(eid, body["answer"], body.get("expert", "KVK Scientist"), farmer_text)


@app.post("/api/elder/{eid}/verify")
def verify_elder(eid: str, body: dict):
    item = mem.verify_elder(eid, body.get("verified", True))
    if not item:
        raise HTTPException(404, "not found")
    return item


# ======================= WhatsApp (Twilio) =======================
@app.post("/webhook/whatsapp")
async def whatsapp(request: Request):
    """Point your Twilio WhatsApp sandbox 'When a message comes in' URL here.
    Voice note -> Whisper -> KrishiSmriti -> reply text + voice note back.
    Start a message with 'log' / 'రికార్డ్' / 'दर्ज' to save a record instead of asking."""
    form = await request.form()
    sender = (form.get("From") or "").replace("whatsapp:", "")
    body = (form.get("Body") or "").strip()
    digits = lambda x: "".join(ch for ch in (x or "") if ch.isdigit())[-10:]
    plot = next((p for p in mem.plots() if p.get("phone") and digits(p["phone"]) == digits(sender)), None)
    if not plot:
        return _twiml("Welcome to KrishiSmriti. This number is not registered yet. Ask your field agent to add your plot.")
    lang = plot.get("lang", "te")
    image_note = None
    for i in range(int(form.get("NumMedia") or 0)):
        url, ctype = form.get(f"MediaUrl{i}"), form.get(f"MediaContentType{i}") or ""
        data = _download_twilio(url)
        if not data:
            continue
        if ctype.startswith("audio"):
            try:
                body = voice.transcribe(data, "voice.ogg", lang)
            except Exception as e:
                print("[whatsapp] transcribe failed:", e)
        elif ctype.startswith("image"):
            image_note = llm.describe_photo(base64.b64encode(data).decode(), ctype)
    if not body and not image_note:
        return _twiml(phrase("saved", lang))
    if body.lower().split(" ")[0] in ("log", "record", "రికార్డ్", "दर्ज", "பதிவு", "രേഖ"):
        _, confirm = _save_spoken(plot["id"], body, lang)
        reply = confirm
    else:
        reply = run_ask(plot, body or "What is wrong with my crop?", lang, image_note)["advice"]["speak"]
    media_url = None
    b64 = voice.speak(reply, lang)
    if b64 and os.getenv("PUBLIC_BASE_URL"):
        name = uuid.uuid4().hex[:10] + ".mp3"
        with open(os.path.join(MEDIA, name), "wb") as f:
            f.write(base64.b64decode(b64))
        media_url = os.getenv("PUBLIC_BASE_URL").rstrip("/") + "/media/" + name
    return _twiml(reply, media_url)


def _download_twilio(url):
    import httpx
    try:
        auth = (os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", ""))
        return httpx.get(url, auth=auth, follow_redirects=True, timeout=20).content
    except Exception as e:
        print("[whatsapp] media download failed:", e)
        return None


def _twiml(text, media_url=None):
    media = f"<Media>{xesc(media_url)}</Media>" if media_url else ""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message><Body>{xesc(text)}</Body>{media}</Message></Response>'
    return Response(xml, media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
