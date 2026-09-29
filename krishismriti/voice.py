"""Voice in / voice out.
STT: Groq Whisper large-v3 (handles Telugu, Hindi, Tamil, Malayalam, Kannada, Marathi, Bengali, Gujarati, Punjabi, English).
TTS: gTTS for the prototype. Production swap: Sarvam Bulbul or Bhashini TTS (more natural Indian voices).
"""
import base64
import io
import os
import time

from llm import groq_client


def transcribe(audio_bytes: bytes, filename: str, lang: str) -> str:
    client = groq_client()
    if not client:
        raise RuntimeError("Voice input needs GROQ_API_KEY. Type the question instead.")
    r = client.audio.transcriptions.create(
        file=(filename or "voice.webm", audio_bytes),
        model=os.getenv("GROQ_STT_MODEL", "whisper-large-v3"),
        language=lang if lang != "auto" else None,
        prompt="Farmer talking about crops, pests, pesticides, fertiliser, neem, whitefly, imidacloprid.",
        response_format="json",
    )
    return r.text.strip()


_cache: dict = {}
_down_until = 0.0


def speak(text: str, lang: str) -> str | None:
    """Return base64 mp3 (free Google TTS, needs internet, no key), or None -> browser speaks instead."""
    global _down_until
    if not text or time.time() < _down_until:
        return None
    key = (text[:900], lang)
    if key in _cache:
        return _cache[key]
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text[:900], lang=lang if lang else "en", slow=False, timeout=8).write_to_fp(buf)
        out = base64.b64encode(buf.getvalue()).decode()
        if len(_cache) > 300:
            _cache.clear()
        _cache[key] = out
        return out
    except Exception as e:
        print("[voice] TTS unavailable, browser will speak instead:", str(e)[:80])
        _down_until = time.time() + 120  # don't slow every request while offline
        return None
