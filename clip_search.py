import pickle
import numpy as np
from app.ai.model_manager import model_manager
from transformers import CLIPProcessor, CLIPModel


print("Loading CLIP...")

model = model_manager.clip_model
processor = model_manager.clip_processor

print("CLIP Loaded")


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


while True:

    query = input(
        "\nEnter image search query: "
    )

    if query.lower() == "exit":
        break

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
                image["file"]
            )
        )

    results.sort(
        reverse=True
    )

    print("\nTop Matches:\n")

    for score, file in results[:5]:

        print(
            f"{file}  |  Score: {score:.4f}"
        )