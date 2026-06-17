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

image = Image.open(
    "data\WhatsApp Image 2026-06-13 at 12.06.02 PM.jpeg"
)

inputs = processor(
    images=image,
    return_tensors="pt"
)

image_features = model.get_image_features(
    **inputs
)

print("\nEmbedding Shape:")
print(image_features.shape)