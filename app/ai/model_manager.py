"""Lazy, thread-safe access to the AI models.

Nothing heavy happens at import time: the ML libraries are imported and each
model is constructed the first time it is used (or by the startup preload
when settings.PRELOAD_MODELS is true). Each model also has its own lock, used
by the encoders so concurrent requests take turns on the GPU instead of
thrashing it.
"""

import logging
import os
import threading


logger = logging.getLogger("cogniseek.models")


class ModelManager:

    def __init__(self):

        self._device = None
        self._semantic_model = None
        self._clip_model = None
        self._clip_processor = None
        self._whisper_model = None
        self._ocr_model = None

        self._load_lock = threading.Lock()

        # Inference locks (encode/transcribe/ocr): one per model, so each model
        # runs one call at a time while different models may overlap (measured
        # fastest). settings.GPU_SERIALIZE=true makes every GPU model share ONE lock.
        self._model_locks = {name: threading.Lock() for name in ("semantic", "clip", "whisper", "ocr")}
        self._gpu_lock = threading.Lock()
        self._ocr_on_gpu = False

    # ------------------------------------------------------------------
    # Device
    # ------------------------------------------------------------------

    @property
    def device(self) -> str:

        if self._device is None:
            import torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device: %s", self._device)

        return self._device

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    @property
    def semantic_model(self):

        if self._semantic_model is None:
            with self._load_lock:
                if self._semantic_model is None:
                    from sentence_transformers import SentenceTransformer
                    logger.info("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
                    self._semantic_model = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)

        return self._semantic_model

    @property
    def clip_model(self):

        if self._clip_model is None:
            with self._load_lock:
                if self._clip_model is None:
                    from transformers import CLIPModel
                    logger.info("Loading CLIP model (openai/clip-vit-base-patch32)...")
                    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                    model.to(self.device)
                    model.eval()
                    self._clip_model = model

        return self._clip_model

    @property
    def clip_processor(self):

        if self._clip_processor is None:
            with self._load_lock:
                if self._clip_processor is None:
                    from transformers import CLIPProcessor
                    logger.info("Loading CLIP processor...")
                    self._clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        return self._clip_processor

    @property
    def whisper_model(self):

        if self._whisper_model is None:
            with self._load_lock:
                if self._whisper_model is None:
                    from faster_whisper import WhisperModel
                    logger.info("Loading Whisper (base)...")
                    compute_type = "float16" if self.device == "cuda" else "int8"
                    self._whisper_model = WhisperModel("base", device=self.device, compute_type=compute_type)

        return self._whisper_model

    @property
    def ocr_model(self):

        if self._ocr_model is None:
            with self._load_lock:
                if self._ocr_model is None:
                    # On Windows, torch must load its DLLs before paddle's,
                    # otherwise a later `import torch` fails (WinError 127). On Linux,
                    # importing paddleocr first segfaults in zlib (inflateReset2) - also
                    # avoided by loading torch first.
                    import torch  # noqa: F401
                    use_gpu = ocr_uses_gpu()
                    from paddleocr import PaddleOCR
                    logger.info("Loading PaddleOCR (%s)...", "GPU" if use_gpu else "CPU")
                    self._ocr_model = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=use_gpu, show_log=False)
                    self._ocr_on_gpu = use_gpu

        return self._ocr_model

    def _lock_for(self, name: str, on_gpu: bool) -> threading.Lock:

        from app.core.config import settings

        return self._gpu_lock if (on_gpu and settings.GPU_SERIALIZE) else self._model_locks[name]

    @property
    def semantic_lock(self) -> threading.Lock:

        return self._lock_for("semantic", self.device == "cuda")

    @property
    def clip_lock(self) -> threading.Lock:

        return self._lock_for("clip", self.device == "cuda")

    @property
    def whisper_lock(self) -> threading.Lock:

        return self._lock_for("whisper", self.device == "cuda")

    @property
    def ocr_lock(self) -> threading.Lock:

        return self._lock_for("ocr", self._ocr_on_gpu)

    @property
    def ready(self) -> bool:
        """Every preloaded model is in memory (GET /ready)."""

        return all(m is not None for m in (
            self._semantic_model, self._clip_model, self._clip_processor, self._whisper_model, self._ocr_model
        ))

    def preload(self) -> None:

        _ = self.semantic_model
        _ = self.clip_model
        _ = self.clip_processor
        _ = self.whisper_model
        _ = self.ocr_model


def register_cuda_dll_dirs() -> list:
    """Windows: let a CUDA build of Paddle find the CUDA/cuDNN DLLs. torch's
    lib folder has cudart/cublas/cufft/curand/cusolver/cusparse (CUDA 12) and the
    nvidia-cudnn-cu12 wheel (requirements-gpu.txt) has cuDNN 8, which Paddle 2.6
    needs. No-op elsewhere."""

    if os.name != "nt":
        return []

    import importlib.util

    import torch

    folders = [os.path.join(os.path.dirname(torch.__file__), "lib")]
    spec = importlib.util.find_spec("nvidia.cudnn") if importlib.util.find_spec("nvidia") else None
    if spec and spec.submodule_search_locations:
        folders += [os.path.join(location, "bin") for location in spec.submodule_search_locations]

    added = [f for f in folders if os.path.isdir(f)]
    for folder in added:
        os.add_dll_directory(folder)
    os.environ["PATH"] = os.pathsep.join(added + [os.environ.get("PATH", "")])
    return added


def ocr_uses_gpu() -> bool:
    """settings.OCR_DEVICE: "cpu", "gpu", or "auto" (GPU when Paddle is a CUDA
    build and a GPU is visible). The CPU build is the default install; the GPU
    build is opt-in (requirements-gpu.txt) and measured ~7.7x faster on OCR."""

    from app.core.config import settings

    if settings.OCR_DEVICE == "cpu":
        return False

    import torch

    if not torch.cuda.is_available():
        return False

    register_cuda_dll_dirs()

    import paddle

    available = paddle.is_compiled_with_cuda()
    if settings.OCR_DEVICE == "gpu" and not available:
        logger.warning("OCR_DEVICE=gpu but Paddle is a CPU build; using the CPU.")
    return available


model_manager = ModelManager()
