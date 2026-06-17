from PIL import Image
from transformers import CLIPProcessor, CLIPModel

print("Loading CLIP...")

model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32"
)

processor = CLIPProcessor.from_pretrained(
    "openai/clip-vit-base-patch32"
)

print("CLIP Loaded")


def get_image_embedding(image_path):

    image = Image.open(image_path)

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    embedding = model.get_image_features(
        **inputs
    )

    embedding = embedding.detach().numpy()[0]

    return embedding