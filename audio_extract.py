from faster_whisper import WhisperModel

print("Loading Whisper model... (This may take some time on first run)")

# Load the model only once
model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

print("Whisper model loaded successfully!")


def extract_audio_text(audio_path):
    """
    Extract text from an audio file.

    Parameters:
        audio_path (str): Path to audio file

    Returns:
        str: Transcript
    """

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