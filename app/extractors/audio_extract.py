"""Whisper transcription."""

import logging
import os

from app.ai.model_manager import model_manager


logger = logging.getLogger("cogniseek.extractors.audio")


def extract_audio_text(audio_path: str) -> str:

    model = model_manager.whisper_model

    logger.debug("Transcribing %s", os.path.basename(audio_path))

    with model_manager.whisper_lock:
        segments, _info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
        transcript = " ".join(segment.text for segment in segments)

    return transcript.strip()
