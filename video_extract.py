import os
import tempfile

from moviepy import VideoFileClip

from audio_extract import (
    extract_audio_text
)


def extract_video_text(
    video_path
):

    print(
        f"\nReading video: {video_path}"
    )

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    ) as temp_audio:

        temp_audio_path = temp_audio.name

    video = VideoFileClip(
        video_path
    )

    video.audio.write_audiofile(
        temp_audio_path,
        logger=None
    )

    transcript = (
        extract_audio_text(
            temp_audio_path
        )
    )

    os.remove(
        temp_audio_path
    )

    return transcript