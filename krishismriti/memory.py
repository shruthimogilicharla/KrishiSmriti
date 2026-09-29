"""Farm memory layer.

Two stores working together:
- Hindsight (semantic, episodic memory): one memory bank per village. Each fact is tagged
  plot:<ID>, so recall can be scoped to one plot (the plot's "medical chart") or run across
  the whole village (community memory: "what worked for my neighbours?").
- Local JSON ledger: structured copy of every event, used for the timeline, the money-saved
  ledger and the deterministic resistance guard. Also the fallback when Hindsight is offline.
"""
import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "store.json")
_lock = threading.Lock()


class FarmMemory:
    def __init__(self):
        self.store = self._load()
        self.hs = None
        url = os.getenv("HINDSIGHT_URL")
        if url:
            try:
                from hindsight_client import Hindsight
                self.hs = Hindsight(base_url=url, api_key=os.getenv("HINDSIGHT_API_KEY") or None, timeout=30)
                self.hs.get_version()
                print(f"[memory] Hindsight connected at {url}")
            except Exception as e:  # keep the app running for the demo
                print(f"[memory] Hindsight unavailable ({e}); using local memory only")
                self.hs = None

    # ---------- persistence ----------
    DEFAULTS = {"plots": {}, "events": [], "followups": [], "elder": [], "savings": [], "hs_seeded": [],
                "escalations": [], "inbox": []}

    def _load(self):
        data = self._read()
        for k, v in self.DEFAULTS.items():
            data.setdefault(k, type(v)())
        return data

    def _read(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self):
        with _lock:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.store, f, ensure_ascii=False, indent=1)

    @property
    def backend(self):
        return "hindsight" if self.hs else "local"

    @staticmethod
    def bank(village: str) -> str:
        return "village-" + re.sub(r"[^a-z0-9]+", "-", village.lower()).strip("-")

    def ensure_bank(self, village: str):
        if not self.hs:
            return
        try:
            self.hs.create_bank(
                bank_id=self.bank(village),
                name=f"{village} farms",
                mission=("Remember every treatment, seed, fertiliser, soil test, harvest and its outcome for each "
                         "farm plot, so advice never repeats a failed treatment and reuses what worked."),
            )
        except Exception:
            pass  # bank already exists

    # ---------- plots ----------
    def plots(self):
        return list(self.store["plots"].values())

    def plot(self, pid):
        return self.store["plots"].get(pid.upper())

    def add_plot(self, plot: dict):
        plot["id"] = plot["id"].upper()
        self.store["plots"][plot["id"]] = plot
        self.ensure_bank(plot["village"])
        self.save()
        return plot

    def events(self, pid=None):
        ev = self.store["events"]
        if pid:
            ev = [e for e in ev if e["plot_id"] == pid.upper()]
        return sorted(ev, key=lambda e: e.get("date", ""))

    # ---------- write ----------
    @staticmethod
    def to_sentence(e: dict, plot: dict) -> str:
        who = f"{e['plot_id']} ({plot.get('crop', '')}, farmer {plot.get('farmer', '')}, {plot.get('village', '')})"
        base = {
            "treatment": f"applied {e.get('product')} for {e.get('target')}",
            "seed": f"sowed seed {e.get('product')}",
            "fertilizer": f"applied fertiliser {e.get('product')}",
            "soil_test": f"soil test result: {e.get('notes')}",
            "observation": f"observed: {e.get('notes')}",
            "harvest": f"harvested: {e.get('notes')}",
        }.get(e["type"], e.get("notes", ""))
        s = f"On {e['date']} on plot {who}, {base}"
        if e.get("cost"):
            s += f", cost ₹{e['cost']}"
        if e.get("outcome") and e["outcome"] != "pending":
            s += f". Outcome: {e['outcome'].upper()}"
            if e.get("days_healthy"):
                s += f", crop stayed healthy for {e['days_healthy']} days"
        if e.get("notes") and e["type"] in ("treatment", "seed", "fertilizer"):
            s += f". Notes: {e['notes']}"
        return s + "."

    def _retain(self, text, plot, tags, when=None):
        if not self.hs:
            return
        try:
            ts = datetime.fromisoformat(when) if when else None
            self.hs.retain(bank_id=self.bank(plot["village"]), content=text, timestamp=ts,
                           context="farm plot record", tags=tags)
        except Exception as e:
            print("[memory] retain failed:", e)

    def add_event(self, e: dict, retain=True):
        e.setdefault("id", uuid.uuid4().hex[:8])
        e.setdefault("date", date.today().isoformat())
        e["plot_id"] = e["plot_id"].upper()
        e.setdefault("outcome", "pending" if e["type"] == "treatment" else None)
        self.store["events"].append(e)
        plot = self.plot(e["plot_id"])
        if e["type"] == "treatment" and e["outcome"] == "pending":
            self.store["followups"].append({
                "id": uuid.uuid4().hex[:8], "event_id": e["id"], "plot_id": e["plot_id"],
                "due": (date.fromisoformat(e["date"]) + timedelta(days=7)).isoformat(), "done": False,
            })
        if retain and plot:
            self._retain(self.to_sentence(e, plot), plot, [f"plot:{e['plot_id']}", f"type:{e['type']}"], e["date"])
        self.save()
        return e

    def close_followup(self, fid, outcome, days_healthy=None, notes=None):
        fu = next((f for f in self.store["followups"] if f["id"] == fid), None)
        if not fu:
            return None
        fu["done"] = True
        ev = next(e for e in self.store["events"] if e["id"] == fu["event_id"])
        ev["outcome"] = outcome
        if days_healthy:
            ev["days_healthy"] = int(days_healthy)
        if notes:
            ev["notes"] = (ev.get("notes", "") + " " + notes).strip()
        plot = self.plot(ev["plot_id"])
        # outcome is a NEW memory: the most valuable fact the system learns
        self._retain("Follow-up result. " + self.to_sentence(ev, plot), plot,
                     [f"plot:{ev['plot_id']}", "type:outcome"], date.today().isoformat())
        self.save()
        return ev

    def due_followups(self, pid=None):
        today = date.today().isoformat()
        out = []
        for f in self.store["followups"]:
            if f["done"] or f["due"] > today or (pid and f["plot_id"] != pid.upper()):
                continue
            ev = next(e for e in self.store["events"] if e["id"] == f["event_id"])
            out.append({**f, "event": ev})
        return out

    def add_elder(self, item: dict):
        item.setdefault("id", uuid.uuid4().hex[:8])
        item.setdefault("date", date.today().isoformat())
        item.setdefault("verified", False)
        self.store["elder"].append(item)
        text = (f"Traditional knowledge from elder {item.get('elder')} of {item['village']}: {item['text']} "
                f"(status: {'verified by KVK' if item['verified'] else 'not yet scientifically verified'}).")
        self._retain(text, {"village": item["village"]}, ["kind:elder"], item["date"])
        self.save()
        return item

    def add_saving(self, pid, product, amount, reason):
        self.store["savings"].append({"plot_id": pid.upper(), "product": product, "amount": amount,
                                      "reason": reason, "date": date.today().isoformat()})
        self.save()

    # ---------- read ----------
    def recall(self, pid: str, query: str, k=8) -> list[str]:
        """Plot-scoped semantic recall (Hindsight) with keyword fallback."""
        plot = self.plot(pid)
        if self.hs and plot:
            try:
                r = self.hs.recall(bank_id=self.bank(plot["village"]), query=query,
                                   tags=[f"plot:{pid.upper()}"], tags_match="any", max_tokens=2000)
                texts = [x.text for x in r.results][:k]
                if texts:
                    return texts
            except Exception as e:
                print("[memory] recall failed:", e)
        return self._keyword(self.events(pid), query, plot, k)

    def recall_village(self, village: str, query: str, exclude_pid=None, k=6) -> list[str]:
        """Community memory: what neighbours and elders in the same village learned."""
        if self.hs:
            try:
                r = self.hs.recall(bank_id=self.bank(village), query=query, max_tokens=2000)
                texts = [x.text for x in r.results if not (exclude_pid and exclude_pid.upper() in x.text)]
                if texts:
                    return texts[:k]
            except Exception as e:
                print("[memory] village recall failed:", e)
        ev = [e for e in self.store["events"]
              if self.plot(e["plot_id"])["village"] == village and e["plot_id"] != (exclude_pid or "").upper()]
        hits = self._keyword(ev, query, None, k)
        elders = [f"Elder {x.get('elder')}: {x['text']} ({'verified' if x['verified'] else 'unverified'})"
                  for x in self.store["elder"] if x["village"] == village]
        return (hits + elders)[:k]

    def _keyword(self, events, query, plot, k):
        words = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 3}
        scored = []
        for e in events:
            p = plot or self.plot(e["plot_id"])
            s = self.to_sentence(e, p)
            score = sum(1 for w in words if w in s.lower()) + (1 if e.get("outcome") in ("failed", "worked") else 0)
            scored.append((score, e.get("date", ""), s))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [s for _, _, s in scored[:k]]

    def reflect(self, pid: str, question: str) -> str | None:
        plot = self.plot(pid)
        if not (self.hs and plot):
            return None
        try:
            r = self.hs.reflect(bank_id=self.bank(plot["village"]), query=question,
                                tags=[f"plot:{pid.upper()}"], budget="mid")
            return r.text
        except Exception as e:
            print("[memory] reflect failed:", e)
            return None

    # ---------- expert escalation ----------
    def escalate(self, pid, question, ai_answer, lang, photo_note=None):
        esc = {"id": uuid.uuid4().hex[:6], "plot_id": pid.upper(), "status": "open", "created": date.today().isoformat(),
               "question": question, "ai_answer": ai_answer, "photo_note": photo_note, "lang": lang, "answer": None}
        self.store["escalations"].append(esc)
        self.save()
        return esc

    def answer_escalation(self, eid, answer, expert, farmer_text):
        esc = next((e for e in self.store["escalations"] if e["id"] == eid), None)
        if not esc:
            return None
        esc.update(status="answered", answer=answer, expert=expert, answered=date.today().isoformat())
        plot = self.plot(esc["plot_id"])
        # the expert's answer becomes plot memory too
        self._retain(f"On {esc['answered']} expert {expert} advised on plot {plot['id']} about '{esc['question']}': {answer}",
                     plot, [f"plot:{plot['id']}", "type:expert"], esc["answered"])
        self.store["inbox"].append({"id": uuid.uuid4().hex[:6], "plot_id": plot["id"], "from": expert,
                                    "text": farmer_text, "date": esc["answered"], "read": False})
        self.save()
        return esc

    def verify_elder(self, eid, verified=True):
        item = next((x for x in self.store["elder"] if x["id"] == eid), None)
        if item:
            item["verified"] = verified
            item["rejected"] = not verified
            self._retain(f"KVK {'verified' if verified else 'rejected'} elder tip from {item['elder']}: {item['text']}",
                         {"village": item["village"]}, ["kind:elder"], date.today().isoformat())
            self.save()
        return item

    # ---------- community ----------
    def outbreaks(self, village=None, days=14, min_plots=2):
        """Same pest reported on >= min_plots plots of a village within `days` -> outbreak alert."""
        since = (date.today() - timedelta(days=days)).isoformat()
        seen = {}
        for e in self.store["events"]:
            p = self.plot(e["plot_id"])
            if not e.get("target") or e.get("date", "") < since or (village and p["village"] != village):
                continue
            k = (p["village"], e["target"].lower())
            seen.setdefault(k, set()).add(e["plot_id"])
        return [{"village": v, "pest": t, "plots": sorted(ps), "count": len(ps), "days": days}
                for (v, t), ps in seen.items() if len(ps) >= min_plots]

    def seed_hindsight(self):
        """Push the local seed history into Hindsight once, so recall works on first run."""
        if not self.hs:
            return
        for plot in self.plots():
            self.ensure_bank(plot["village"])
            if plot["id"] in self.store["hs_seeded"]:
                continue
            for e in self.events(plot["id"]):
                self._retain(self.to_sentence(e, plot), plot, [f"plot:{plot['id']}", f"type:{e['type']}"], e["date"])
            self.store["hs_seeded"].append(plot["id"])
        for item in self.store["elder"]:
            if item["id"] not in self.store["hs_seeded"]:
                text = f"Traditional knowledge from elder {item.get('elder')} of {item['village']}: {item['text']}"
                self._retain(text, {"village": item["village"]}, ["kind:elder"], item["date"])
                self.store["hs_seeded"].append(item["id"])
        self.save()
