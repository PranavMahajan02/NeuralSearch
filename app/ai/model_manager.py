import torch

from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor
from faster_whisper import WhisperModel
from paddleocr import PaddleOCR


class ModelManager:

    def __init__(self):

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(f"Using device: {self.device}")

        self._semantic_model = None
        self._clip_model = None
        self._clip_processor = None
        self._whisper_model = None
        self._ocr_model = None

    # --------------------------
    # Sentence Transformer
    # --------------------------

    @property
    def semantic_model(self):

        if self._semantic_model is None:

            print("Loading SentenceTransformer...")

            self._semantic_model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                device=self.device
            )

        return self._semantic_model

    # --------------------------
    # CLIP Model
    # --------------------------

    @property
    def clip_model(self):

        if self._clip_model is None:

            print("Loading CLIP Model...")

            self._clip_model = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32"
            )

            self._clip_model.to(self.device)
            self._clip_model.eval()

        return self._clip_model

    # --------------------------
    # CLIP Processor
    # --------------------------

    @property
    def clip_processor(self):

        if self._clip_processor is None:

            print("Loading CLIP Processor...")

            self._clip_processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32"
            )

        return self._clip_processor

    # --------------------------
    # Whisper
    # --------------------------

    @property
    def whisper_model(self):

        if self._whisper_model is None:

            print("Loading Faster Whisper...")

            self._whisper_model = WhisperModel(
                "base",
                device=self.device,
                compute_type=(
                    "float16"
                    if self.device == "cuda"
                    else "int8"
                )
            )

        return self._whisper_model

    # --------------------------
    # PaddleOCR
    # --------------------------

    @property
    def ocr_model(self):

        if self._ocr_model is None:

            print("Loading PaddleOCR...")

            self._ocr_model = PaddleOCR(
                use_angle_cls=True,
                lang="en"
            )

        return self._ocr_model


model_manager = ModelManager()