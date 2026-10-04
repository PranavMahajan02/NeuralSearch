from PIL import Image
import torch

from app.ai.model_manager import model_manager


def get_image_embedding(image_path):

    image = Image.open(image_path).convert("RGB")

    processor = model_manager.clip_processor

    model = model_manager.clip_model

    device = model_manager.device

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    inputs = {
        k: v.to(device)
        for k, v in inputs.items()
    }

    with torch.no_grad():

        embedding = model.get_image_features(
            **inputs
        )

    return embedding.cpu().numpy()[0].tolist()


def get_text_embedding(text):

    processor = model_manager.clip_processor

    model = model_manager.clip_model

    device = model_manager.device

    inputs = processor(
        text=[text],
        return_tensors="pt",
        padding=True
    )

    inputs = {
        k: v.to(device)
        for k, v in inputs.items()
    }

    with torch.no_grad():

        embedding = model.get_text_features(
            **inputs
        )

    return embedding.cpu().numpy()[0].tolist()