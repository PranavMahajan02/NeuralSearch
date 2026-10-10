"""Whisper transcription."""

import logging
import os

from app.ai.model_manager import model_manager
from app.core.timing import span, waiting_for

logger = logging.getLogger("cogniseek.extractors.audio")


def extract_audio_text(audio_path: str) -> str:
    """Transcript of an audio file, or of a video's audio track (faster-whisper
    decodes either directly). VAD skips silence. settings.WHISPER_BATCH_SIZE > 0
    uses the batched pipeline (faster, but the transcript wording shifts)."""

    from app.core.config import settings

    model = model_manager.whisper_model

    logger.debug("Transcribing %s", os.path.basename(audio_path))

    with span("whisper"), waiting_for(model_manager.whisper_lock):
        if settings.WHISPER_BATCH_SIZE > 0:
            from faster_whisper import BatchedInferencePipeline

            segments, _info = BatchedInferencePipeline(model=model).transcribe(
                audio_path, beam_size=1, vad_filter=True, batch_size=settings.WHISPER_BATCH_SIZE
            )
        else:
            segments, _info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
        transcript = " ".join(segment.text for segment in segments)

    return transcript.strip()
