# KrishiSmriti prototype audit

I walked through the app as Ramaiah (Telugu, cotton, Kondapur), who can speak but can't read, on a basic Android phone with patchy internet. Each problem below is marked **Fixed**, **Partly fixed** or **Open**.

## A. Where a farmer gets stuck

| # | Problem as the farmer | Status |
|---|---|---|
| 1 | Asked a question and had to scroll down to find the answer | **Fixed.** On a laptop the answer appears in a panel beside the phone. On a phone it slides up full screen with a ✕ to close, and a short "Answer ready" card sits at the top of the Ask screen. |
| 2 | Pressing Enter did nothing | **Fixed.** Enter sends, and empty sends show a hint. |
| 3 | App went silent on errors | **Fixed.** Clear messages for no server, no internet, slow network, and mic blocked. |
| 4 | Advice steps were in English even when Telugu was chosen (offline) | **Fixed for te/hi/ta/ml.** All 23 offline options are translated and the first step is spoken. Other languages still show English steps. |
| 5 | Told what to buy, but not where or at what price | **Fixed.** Every product shows its name, example brands, 🌿 natural or 🧪 chemical, pack size, approximate price and buy buttons (BigHaat, Amazon, shop near me). Urea and DAP show a natural alternative. Crop-stage tasks that mention a fertiliser also get buy cards. |
| 6 | After hearing the advice, the farmer never reports what he did, so memory learns nothing | **Fixed.** An "👍 I will do this" button saves the treatment and schedules the 7-day "did it work?" check. |
| 7 | 🔊 on English-only cards read English with a Telugu voice (garbled) | **Fixed.** Untranslated text is read with an English voice. |
| 8 | Can't type a pest name | **Fixed earlier.** 8 picture buttons, one tap. |
| 9 | Needed an API key to get any voice | **Fixed earlier.** Browser mic and free Google voice, no key. |
| 10 | Crop-stage tasks, scheme text and warning reasons are still English offline | **Open.** Needs a translation file or a Groq key (the LLM translates them live). |
| 11 | Voice needs internet (browser speech recognition and Google voice) | **Open.** Offline fallback is typing or picture tap. Production: on-device Indic speech models or an IVR call line. |
| 12 | The "Ramaiah · Kondapur" dropdown is a demo control, not something a farmer would have | **Open by design.** In production each phone logs in as one farmer. |
| 13 | Farmers with no smartphone | **Partly.** A WhatsApp voice-note webhook exists. A missed-call IVR is still on the roadmap. |
| 14 | Leaf photo does nothing useful without a key | **Partly.** The app says so and points to the picture buttons. |

## B. Technical drawbacks and fallbacks

| Area | Drawback | Current fallback | Production fix |
|---|---|---|---|
| AI answers | Offline engine knows 8 problems only | Memory guard + built-in pest guide; unknown questions offer pictures / expert | Groq/LLM + agronomist-reviewed knowledge base (ICAR/SAU Package of Practices) |
| Memory | JSON file on one laptop, no login, not multi-user safe | Hindsight when configured; JSON otherwise | Postgres + Hindsight, farmer login by phone OTP, consent flow (DPDP Act) |
| Resistance guard | Product table ~40 items; brand aliases limited | Unknown products pass through with no warning | Full CIB&RC registration list + IRAC/FRAC map, brand alias crowdsourcing |
| Prices | Approximate ranges typed in by hand | Labelled "approximate"; urea/DAP use govt MRP | Live feed from partner shops (BigHaat/AgroStar/DeHaat/IFFCO Bazar) + nearest dealer stock |
| Buy links | Open a shop *search*, not a checked product page | Search keeps working when pages change | Partner deep links with affiliate tracking |
| Mandi price | Sample series unless data.gov.in key is set | Clearly marked SAMPLE | Agmarknet/eNAM live |
| Weather | Needs internet | Card says "needs internet" | Cache last forecast; SMS alerts |
| Outcomes | Self-reported 👍/👎 can be wrong | Village pattern + expert check | Field agent spot-checks, satellite NDVI change as a second signal |
| Safety | App must never invent doses | Always "follow the label / ask KVK" | Keep; add label photo reader |
| Bias risk | Shop links could look like selling | Natural options listed first; chemicals only from a *different* group | Never take payment to rank a product; publish this rule |

## C. What to say to judges when they ask about limits
"The memory and the resistance guard are rule-based and can't be overridden by the AI. The AI only phrases the advice. Offline it covers the 8 most common problems in 4 languages. With an LLM key it covers everything. Prices are indicative until we plug in a partner feed."
