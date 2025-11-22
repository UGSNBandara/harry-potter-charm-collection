import os
import re
import time
import math
import io
from typing import Optional

import numpy as np
import streamlit as st
import soundfile as sf
from scipy.signal import resample_poly
from scipy.io import wavfile as wav_write
from pymongo import MongoClient
from gridfs import GridFS

# Load env from .env file if present
def load_env():
    from pathlib import Path
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

load_env()

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "spells")
MONGO_BUCKET = os.getenv("MONGO_BUCKET", "fs")

TARGET_SR = 16000
SPELLS = ["Lumos", "Nox", "Alohomora", "Wingardium Leviosa", "Accio", "Reparo"]

_mongo_client: Optional[MongoClient] = None
_mongo_fs: Optional[GridFS] = None


def get_gridfs() -> Optional[GridFS]:
    global _mongo_client, _mongo_fs
    if not MONGO_URI:
        return None
    if _mongo_fs is not None:
        return _mongo_fs
    _mongo_client = MongoClient(MONGO_URI)
    db = _mongo_client[MONGO_DB]
    _mongo_fs = GridFS(db, collection=MONGO_BUCKET)
    return _mongo_fs


def sanitize_username(name: Optional[str]) -> str:
    if not name:
        return "anon"
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    return name.lower() or "anon"


def to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 2:
        return audio.mean(axis=1)
    return audio


def resample_to_target(audio: np.ndarray, sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    if sr == target_sr:
        return audio
    g = math.gcd(sr, target_sr)
    up = target_sr // g
    down = sr // g
    return resample_poly(audio, up=up, down=down)


def save_audio_to_mongo(audio_bytes: bytes, spell: str, username: str) -> Optional[str]:
    """Process uploaded audio and save to MongoDB GridFS."""
    try:
        audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=False)
        if audio is None or (isinstance(audio, np.ndarray) and audio.size == 0):
            return None

        audio = to_mono(np.asarray(audio))
        audio = resample_to_target(audio, sr, TARGET_SR)
        audio = np.clip(audio, -1.0, 1.0)

        # Convert to int16 PCM WAV
        pcm16 = (audio * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        wav_write.write(buf, TARGET_SR, pcm16)
        wav_bytes = buf.getvalue()

        fs = get_gridfs()
        if fs is None:
            return None

        ts = int(time.time() * 1000)
        spell_slug = re.sub(r"[^a-zA-Z0-9]+", "_", spell).strip("_").lower()
        filename = f"{spell_slug}_{username}_{ts}.wav"
        metadata = {
            "username": username,
            "spell": spell,
            "timestamp_ms": ts,
            "sample_rate": TARGET_SR,
            "format": "wav",
        }
        file_id = fs.put(wav_bytes, filename=filename, contentType="audio/wav", metadata=metadata)
        return str(file_id)
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return None


def main():
    st.set_page_config(page_title="Spell Recorder", page_icon="✨", layout="wide")
    
    st.title("✨ Spell Recorder")
    st.markdown("""
    Record each spell using your microphone. Press the record button and speak the spell clearly.
    
    **Spells to collect:** Lumos, Nox, Alohomora, Wingardium Leviosa, Accio, Reparo
    """)

    if not MONGO_URI:
        st.warning("⚠️ Database not configured. Set MONGO_URI in your environment or .env file.")
    
    # Username input
    username = st.text_input("Your Name (for metadata)", placeholder="e.g., harry_p", key="username")
    
    st.markdown("### 🎤 Record Each Spell")
    
    # Audio recorder for each spell
    audio_files = {}
    cols = st.columns(2)
    
    for idx, spell in enumerate(SPELLS):
        col = cols[idx % 2]
        with col:
            st.markdown(f"**{spell}**")
            audio_file = st.audio_input(
                f"Record {spell}",
                key=f"audio_{spell}",
                label_visibility="collapsed"
            )
            if audio_file:
                audio_files[spell] = audio_file
    
    # Counter
    selected_count = len(audio_files)
    st.markdown(f"**Selected: {selected_count}/6**")
    
    # Submit button
    if st.button("Submit Recordings", type="primary", use_container_width=True):
        if not username.strip():
            st.error("Please enter your name")
        elif selected_count == 0:
            st.error("Please upload at least one spell recording")
        else:
            user = sanitize_username(username)
            saved = []
            skipped = []
            
            with st.spinner("Processing and saving recordings..."):
                for spell in SPELLS:
                    if spell in audio_files:
                        audio_bytes = audio_files[spell].read()
                        file_id = save_audio_to_mongo(audio_bytes, spell, user)
                        if file_id:
                            saved.append(f"{spell} → id {file_id}")
                        else:
                            skipped.append(spell)
                    else:
                        skipped.append(spell)
            
            # Display results
            if saved:
                st.success("✅ Saved recordings:")
                for item in saved:
                    st.write(f"- {item}")
            
            if skipped:
                with st.expander("ℹ️ Missing (not provided)"):
                    for spell in skipped:
                        st.write(f"- {spell}")
            
            st.info(f"**Total saved this submission: {len(saved)}**")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Notes:**
    - Click the microphone icon to record each spell
    - Speak clearly and press stop when done
    - Recordings are stored in MongoDB GridFS with 16 kHz mono WAV format
    - You don't have to record all spells at once
    - Files are saved with metadata: username, spell, timestamp
    """)


if __name__ == "__main__":
    main()
