from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch

model_id = "microsoft/Florence-2-base"

print("Loading Florence-2...")

model = AutoModelForCausalLM.from_pretrained(
model_id,
trust_remote_code=True
)

processor = AutoProcessor.from_pretrained(
model_id,
trust_remote_code=True
)

print("Florence-2 Loaded")

def extract_text(image_path):

    image = Image.open(image_path).convert("RGB")

    prompt = "<OCR>"

    inputs = processor(
        text=prompt,
        images=image,
        return_tensors="pt"
    )

    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024
    )

    generated_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return generated_text