# KrishiSmriti: every farm plot gets its own memory

A voice-first farm advisor for farmers who can't read. It remembers every spray, seed, fertiliser, soil test and harvest on each plot, and whether it worked. It never recommends a treatment that already failed on that plot, or anything from the same chemical group.

## Run it

**Windows:** double-click `run.bat`. It installs everything and opens the app in your browser. Keep the black window open.

**No API key needed.** Voice input uses the Chrome/Edge microphone (free), voice output uses free Google voice, and answers come from the farm memory plus the built-in pest guide. Both voice features need internet. Adding a free Groq key in `.env` (console.groq.com) turns on full AI answers in any language, leaf-photo diagnosis and bill scanning.

Use **Chrome or Edge**. The first time you tap the mic, click "Allow" for microphone access.

**Mac/Linux:**
```bash
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY
uvicorn main:app --reload
```

| Open | What |
|---|---|
| http://localhost:8000 | Farmer app (phone frame on a laptop, full screen on a phone; installable as an app) |
| http://localhost:8000/agent | Field agent / KVK scientist desk |
| http://localhost:8000/passport/PLOT-14 | Printable plot passport with QR |
| http://localhost:8000/docs | All API endpoints |

With no key and no Hindsight, it still runs from the rule engine and a local memory file. That's your backup if the Wi-Fi dies on stage. Delete `data/store.json` to reset the demo.

### Optional: Hindsight memory server
```bash
docker run -d --name hindsight -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_PROVIDER=groq -e HINDSIGHT_API_LLM_API_KEY=<your groq key> \
  -v hindsight-data:/home/hindsight/.pg0 ghcr.io/vectorize-io/hindsight:latest
```
Then uncomment `HINDSIGHT_URL=http://localhost:8888` in `.env`.

### Optional: real WhatsApp
1. Create a Twilio WhatsApp sandbox, then put `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env`.
2. Run `ngrok http 8000` and set `PUBLIC_BASE_URL` to the ngrok URL.
3. In Twilio, set "When a message comes in" to `<ngrok url>/webhook/whatsapp`.
4. Change a seed farmer's `phone` to your number (or register yourself in the app). Send a voice note and you get a text and voice note back in your language. Start a message with "log" to save a record instead of asking.

## Features

**Farmer app (voice first, 10 languages)**
- Home screen: greeting in the farmer's language, crop stage by days after sowing with this week's tasks, village pest outbreak alerts, "did it work?" check, spray-window weather, money saved and wasted, mandi price with MSP line, and the plot's list of treatments that don't work there. Every card has a 🔊 button that reads it aloud.
- Ask: speak, type (Enter sends), tap a picture of the pest/symptom (no reading needed), attach a leaf photo, or send it to a human expert.
- Answer panel: on a laptop the answer opens beside the phone, on a phone it slides up full screen. No scrolling.
- Buy cards on every recommended product or fertiliser: name, brands, 🌿 natural / 🧪 chemical, pack, approx price, and BigHaat / Amazon / shop-near-me links. Urea and DAP show natural alternatives.
- "👍 I will do this" saves the chosen treatment and schedules the 7-day check.
- See AUDIT.md for the farmer walkthrough, known limits and fallbacks.
- First launch: big language picker. "Listen to today's update" reads the whole home screen aloud.
- Tell: voice-log a spray or harvest, or scan old pesticide bills to fill in past seasons.
- My farm: medical chart, full history, spoken season report (Hindsight reflect).
- More: what worked in the village, mandi prices, government schemes, elder wisdom, plot passport, register a new farmer.

**Memory brain**
- Hindsight: one bank per village, tagged `plot:<ID>`, so recall covers either one plot or the whole village.
- Resistance guard: blocks failed products and their whole IRAC/FRAC group, checks the banned list, and the LLM can't override it.
- Village resistance: when the same chemical group has failed on a neighbour's plot, the farmer gets a warning.
- 7-day follow-up: 👍 🤏 👎 outcomes become new memories.
- Expert answers and verified elder tips go back into memory too.

**Field agent / KVK desk**
- KPIs, resistance heatmap (village × chemical group), outbreak alerts, expert queue (answers are auto-translated and pushed to the farmer), elder tip verification, and a farmer table with passports.

**Channels**
- Web app / installable PWA, WhatsApp voice notes (Twilio), printable passport.

## Demo script (3 minutes)
1. **Ramaiah (Telugu), home screen.** Point out the whitefly outbreak alert (3 farms), the check-in question, crop stage day 100, and the "doesn't work here" list.
2. **🎙️ Ask** "Dealer is giving me thiamethoxam for whitefly, is it ok?" It says no: same chemical group as the imidacloprid that failed twice, and acetamiprid also failed on the neighbour's plot. It recommends neem oil, which gave 47 healthy days, and reads all this out in Telugu.
3. Tap 👍 on the check-in. The outcome is saved to memory.
4. Switch to **Joseph (Malayalam)** and ask about carbendazim. The answer comes back in Malayalam from his own history.
5. Open **/agent**: resistance heatmap, answer Lakshmi's leaf curl question, verify an elder tip.
6. Switch to **Lakshmi**. The expert's answer is on her home screen in Telugu.
7. Open the **passport**: "this is what she shows the bank, the insurer and the dealer."

## Files
| File | Role |
|---|---|
| `main.py` | All routes: farmer app, agent desk, passport, WhatsApp webhook |
| `memory.py` | Hindsight + local ledger, recall/retain/reflect, escalations, outbreaks |
| `agronomy.py` | IRAC/FRAC resistance guard, banned list, brand/local-name aliases |
| `llm.py` | Groq advice, voice-note extraction, photo diagnosis, bill scan, translation, offline fallback |
| `crops.py` | Crop calendars, mandi prices (live Agmarknet or sample), schemes |
| `voice.py` / `weather.py` | Whisper STT + gTTS / Open-Meteo spray window |
| `seed.py` | 8 demo farmers, 4 villages, 4 languages |
| `templates/` | `index.html` farmer app, `agent.html` desk, `passport.html` |
| `static/` | PWA manifest, service worker, icon |

## Honest limits (say these before judges ask)
- The product table covers ~40 common products. Production loads the full CIB&RC list, reviewed by an agronomist.
- Mandi prices are labelled SAMPLE unless you add a free data.gov.in key.
- gTTS voices are robotic. Production uses Sarvam Bulbul or Bhashini.
- Doses are never invented. The app says "follow the label or ask the KVK".
