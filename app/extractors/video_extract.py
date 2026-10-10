"""Video transcript: Whisper reads the video's audio track directly.

faster-whisper decodes the media file itself (PyAV), so the audio is no longer
exported to a temporary WAV with moviepy first (that export was ~16% of the
video transcription time; the transcripts are the same - docs/perf/RESULTS.md).
moviepy remains the fallback for a container PyAV cannot read.
"""

import logging
import os
import tempfile

from app.core.timing import span
from app.extractors.audio_extract import extract_audio_text

logger = logging.getLogger("cogniseek.extractors.video")


def has_audio_track(video_path: str) -> bool:

    import av

    with av.open(video_path) as container:
        return bool(container.streams.audio)


def extract_video_text(video_path: str) -> str:

    try:
        if not has_audio_track(video_path):
            logger.debug("No audio track: %s", os.path.basename(video_path))
            return ""
        return extract_audio_text(video_path)
    except Exception as error:
        logger.debug("direct audio decode failed for %s (%s); using moviepy",
                     os.path.basename(video_path), type(error).__name__)
        return _via_wav(video_path)


def _via_wav(video_path: str) -> str:

    from moviepy import VideoFileClip

    with span("audio_extract"):
        video = VideoFileClip(video_path)

    try:
        if video.audio is None:
            return ""

        with tempfile.TemporaryDirectory(prefix="video-audio-") as tmp:
            audio_path = os.path.join(tmp, "audio.wav")
            with span("audio_extract"):
                video.audio.write_audiofile(audio_path, logger=None)
            return extract_audio_text(audio_path)
    finally:
        video.close()
