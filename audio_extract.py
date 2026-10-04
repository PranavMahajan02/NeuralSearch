from app.ai.model_manager import model_manager


def extract_audio_text(audio_path):
    """
    Extract text from an audio file.

    Parameters:
        audio_path (str): Path to audio file

    Returns:
        str: Transcript
    """

    model = model_manager.whisper_model

    print(f"\nReading audio file: {audio_path}")

    segments, info = model.transcribe(
        audio_path,
        beam_size=1,
        vad_filter=True
    )

    transcript = ""

    print("\nTranscribing...")

    for segment in segments:
        transcript += segment.text + " "

    return transcript.strip()