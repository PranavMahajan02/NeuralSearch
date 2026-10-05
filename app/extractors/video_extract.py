"""Video transcript: extract the audio track, then Whisper."""

import logging
import os
import tempfile

from app.extractors.audio_extract import extract_audio_text


logger = logging.getLogger("cogniseek.extractors.video")


def extract_video_text(video_path: str) -> str:

    from moviepy import VideoFileClip

    video = VideoFileClip(video_path)

    try:
        if video.audio is None:
            logger.debug("No audio track: %s", os.path.basename(video_path))
            return ""

        with tempfile.TemporaryDirectory(prefix="video-audio-") as tmp:
            audio_path = os.path.join(tmp, "audio.wav")
            video.audio.write_audiofile(audio_path, logger=None)
            return extract_audio_text(audio_path)
    finally:
        video.close()
