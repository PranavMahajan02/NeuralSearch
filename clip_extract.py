import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Loading CLIP...")

model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32"
).to(device)

model.eval()

processor = CLIPProcessor.from_pretrained(
    "openai/clip-vit-base-patch32"
)

print(f"CLIP Loaded ({device})")


def get_image_embedding(image_path):

    image = Image.open(image_path).convert("RGB")

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

    return embedding.cpu().numpy()[0]