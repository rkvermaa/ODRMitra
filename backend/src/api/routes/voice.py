"""Voice API routes — Sarvam AI STT + TTS for real-time voice interaction."""

import base64
import io
import re
import wave
import uuid

import httpx
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from src.config import settings
from src.core.logging import log

router = APIRouter()

SARVAM_API_KEY = settings.get("SARVAM_API_KEY", "")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_LID_URL = "https://api.sarvam.ai/text-lid"

TTS_CHAR_LIMIT = 2500

# In-memory audio store (for demo — use Redis in production)
_audio_store: dict[str, bytes] = {}


# ─── STT (Speech-to-Text) ───

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """Convert speech audio to text using Sarvam ASR."""
    audio_data = await file.read()
    if not audio_data:
        return JSONResponse({"error": "No audio data"}, status_code=400)

    log.info(f"STT: received {len(audio_data)} bytes")

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": ("input.wav", audio_data, "audio/wav")},
            data={"model": "saarika:v2.5", "language_code": "unknown"},
        )

    if resp.status_code != 200:
        log.error(f"STT failed: {resp.status_code} {resp.text}")
        return JSONResponse({"error": "STT failed"}, status_code=502)

    transcript = resp.json().get("transcript", "")
    log.info(f"STT result: {transcript}")
    return {"transcript": transcript}


# ─── LID (Language Identification) ───

@router.post("/lid")
async def identify_language(text: str = Form(...)):
    """Detect language of text using Sarvam LID."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            SARVAM_LID_URL,
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={"input": text},
        )

    if resp.status_code != 200:
        log.warning(f"LID failed: {resp.status_code}")
        return {"language_code": "hi-IN", "script_code": "Deva"}

    return resp.json()


# ─── TTS (Text-to-Speech) ───

def _clean_for_tts(text: str) -> str:
    """Clean markdown/emoji for TTS."""
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[`~\[\]()>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str, limit: int = TTS_CHAR_LIMIT) -> list[str]:
    """Split text at sentence boundaries respecting char limit."""
    if len(text) <= limit:
        return [text]

    chunks = []
    pos = 0
    while pos < len(text):
        if len(text) - pos <= limit:
            chunks.append(text[pos:])
            break
        end = pos + limit
        # Try sentence boundary
        for delim in [". ", "! ", "? ", "\n"]:
            idx = text.rfind(delim, pos, end)
            if idx > pos:
                end = idx + len(delim)
                break
        else:
            # Try word boundary
            idx = text.rfind(" ", pos, end)
            if idx > pos:
                end = idx + 1
        chunks.append(text[pos:end].strip())
        pos = end

    return [c for c in chunks if c]


async def _call_sarvam_tts(
    text: str, lang_code: str, speaker: str = "shubh", model: str = "bulbul:v3"
) -> str:
    """Call Sarvam TTS API, return base64 audio."""
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            SARVAM_TTS_URL,
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "target_language_code": lang_code,
                "speaker": speaker,
                "model": model,
            },
        )

    if resp.status_code != 200:
        log.error(f"TTS API failed: {resp.status_code} {resp.text}")
        raise Exception(f"TTS failed: {resp.status_code}")

    audios = resp.json().get("audios", [])
    if not audios or not audios[0]:
        raise Exception("TTS returned no audio")

    return audios[0]


def _concat_wav_b64(parts: list[str]) -> str:
    """Concatenate multiple base64 WAV chunks into one."""
    if len(parts) == 1:
        return parts[0]

    all_frames = []
    params = None

    for b64 in parts:
        wav_bytes = base64.b64decode(b64)
        with io.BytesIO(wav_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                if params is None:
                    params = wf.getparams()
                all_frames.append(wf.readframes(wf.getnframes()))

    with io.BytesIO() as out:
        with wave.open(out, "wb") as wf:
            wf.setparams(params)
            for frames in all_frames:
                wf.writeframes(frames)
        return base64.b64encode(out.getvalue()).decode()


@router.post("/tts")
async def text_to_speech(text: str = Form(...), lang_code: str = Form("hi-IN")):
    """Convert text to speech using Sarvam TTS. Returns audio_id to fetch."""
    cleaned = _clean_for_tts(text)
    if not cleaned:
        return JSONResponse({"error": "Empty text"}, status_code=400)

    log.info(f"TTS: {len(cleaned)} chars, lang={lang_code}")

    try:
        chunks = _chunk_text(cleaned)
        b64_parts = []
        for chunk in chunks:
            b64 = await _call_sarvam_tts(chunk, lang_code)
            b64_parts.append(b64)

        final_b64 = _concat_wav_b64(b64_parts)

        # Store and return ID
        audio_id = str(uuid.uuid4())
        _audio_store[audio_id] = base64.b64decode(final_b64)

        # Cleanup old entries
        if len(_audio_store) > 200:
            oldest = next(iter(_audio_store))
            del _audio_store[oldest]

        return {"audio_id": audio_id}

    except Exception as e:
        log.error(f"TTS error: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Retrieve generated audio by ID."""
    audio_bytes = _audio_store.pop(audio_id, None)
    if not audio_bytes:
        return JSONResponse({"error": "Audio not found"}, status_code=404)

    return Response(content=audio_bytes, media_type="audio/wav")
