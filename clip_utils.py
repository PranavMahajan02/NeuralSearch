import numpy as np
import pickle
from app.ai.model_manager import model_manager
from transformers import CLIPProcessor, CLIPModel

print("Loading CLIP...")

model = model_manager.clip_model
processor = model_manager.clip_processor

print("CLIP Ready")


with open(
    "image_index.pkl",
    "rb"
) as f:

    image_index = pickle.load(f)


def cosine_similarity(a, b):

    return np.dot(a, b) / (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )


def clip_search(query):

    inputs = processor(
        text=[query],
        return_tensors="pt",
        padding=True
    )

    query_embedding = model.get_text_features(
        **inputs
    )

    query_embedding = (
        query_embedding
        .detach()
        .numpy()[0]
    )

    results = []

    for image in image_index:

        score = cosine_similarity(
            query_embedding,
            image["embedding"]
        )

        results.append(
            (
                score,
                image
            )
        )

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return results