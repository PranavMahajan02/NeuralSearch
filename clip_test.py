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
    "data\photo-09.jpeg"
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