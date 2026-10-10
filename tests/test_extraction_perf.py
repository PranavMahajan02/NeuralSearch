"""Phase 7A.5-B2/B3: OCR device selection and direct video transcription."""

import sys
import types

import pytest

from app.core.config import settings

# ---------------------------------------------------------------------------
# OCR device
# ---------------------------------------------------------------------------

def _load_real_model_manager():
    """conftest replaces app.ai.model_manager with a stub; load the real file."""

    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "app" / "ai" / "model_manager.py"
    spec = importlib.util.spec_from_file_location("real_model_manager", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


real_model_manager = _load_real_model_manager()


@pytest.fixture
def fake_torch_paddle(monkeypatch):

    state = {"cuda": True, "paddle_cuda": True}
    torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: state["cuda"]), __file__="x")
    paddle = types.SimpleNamespace(is_compiled_with_cuda=lambda: state["paddle_cuda"])
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "paddle", paddle)

    monkeypatch.setattr(real_model_manager, "register_cuda_dll_dirs", lambda: [])
    return state


@pytest.mark.parametrize("setting, cuda, paddle_cuda, expected", [
    ("auto", True, True, True),      # CUDA build installed + GPU visible
    ("auto", True, False, False),    # default CPU build of Paddle
    ("auto", False, True, False),    # no GPU
    ("cpu", True, True, False),      # forced CPU
    ("gpu", True, False, False),     # asked for GPU without a CUDA build: falls back, warns
])
def test_ocr_device_choice(fake_torch_paddle, monkeypatch, setting, cuda, paddle_cuda, expected):

    ocr_uses_gpu = real_model_manager.ocr_uses_gpu

    fake_torch_paddle.update(cuda=cuda, paddle_cuda=paddle_cuda)
    monkeypatch.setattr(settings, "OCR_DEVICE", setting)

    assert ocr_uses_gpu() is expected


# ---------------------------------------------------------------------------
# Video transcript
# ---------------------------------------------------------------------------

def test_video_audio_is_transcribed_directly_without_a_wav_export(monkeypatch):

    import app.extractors.video_extract as video

    seen = []
    monkeypatch.setattr(video, "has_audio_track", lambda path: True)
    monkeypatch.setattr(video, "extract_audio_text", lambda path: seen.append(path) or "spoken words")
    monkeypatch.setattr(video, "_via_wav", lambda path: pytest.fail("no WAV export expected"))

    assert video.extract_video_text("clip.mp4") == "spoken words"
    assert seen == ["clip.mp4"]


def test_a_video_without_audio_has_no_transcript(monkeypatch):

    import app.extractors.video_extract as video

    monkeypatch.setattr(video, "has_audio_track", lambda path: False)
    monkeypatch.setattr(video, "extract_audio_text", lambda path: pytest.fail("nothing to transcribe"))

    assert video.extract_video_text("silent.mp4") == ""


def test_unreadable_container_falls_back_to_moviepy(monkeypatch):

    import app.extractors.video_extract as video

    def broken(path):
        raise OSError("PyAV cannot open this container")

    monkeypatch.setattr(video, "has_audio_track", broken)
    monkeypatch.setattr(video, "_via_wav", lambda path: "from the wav")

    assert video.extract_video_text("odd.mkv") == "from the wav"


def test_batched_whisper_is_opt_in(monkeypatch):

    import app.extractors.audio_extract as audio

    class Model:
        def transcribe(self, path, **kwargs):
            assert "batch_size" not in kwargs and kwargs["vad_filter"] is True
            return [types.SimpleNamespace(text=" hello")], None

    monkeypatch.setattr(audio.model_manager, "whisper_model", Model())
    monkeypatch.setattr(settings, "WHISPER_BATCH_SIZE", 0)

    assert audio.extract_audio_text("a.wav") == "hello"


@pytest.mark.parametrize("serialize, on_gpu, shared", [(True, True, True), (True, False, False), (False, True, False)])
def test_gpu_models_share_one_lock(monkeypatch, serialize, on_gpu, shared):

    manager = real_model_manager.ModelManager()
    monkeypatch.setattr(settings, "GPU_SERIALIZE", serialize)
    manager._device = "cuda" if on_gpu else "cpu"
    manager._ocr_on_gpu = on_gpu

    locks = {manager.semantic_lock, manager.clip_lock, manager.whisper_lock, manager.ocr_lock}

    assert (len(locks) == 1) is shared
    if not shared:
        assert len(locks) == 4
