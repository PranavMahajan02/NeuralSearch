import os
import pickle

from clip_extract import get_image_embedding
from paddle_extract import extract_text as paddle_ocr

all_images = []

data_folder = "data"

print("Building CLIP Image Index...\n")

for filename in os.listdir(data_folder):

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        continue

    file_path = os.path.join(
        data_folder,
        filename
    )

    print(f"Processing: {filename}")

    embedding = get_image_embedding(
        file_path
    )

    ocr_text = paddle_ocr(
        file_path
    )

    all_images.append(
        {
            "file": filename,
            "path": file_path,
            "embedding": embedding,
            "ocr_text": ocr_text
        }
    )

print(
    f"\nTotal Images Indexed: {len(all_images)}"
)

with open(
    "image_index.pkl",
    "wb"
) as f:

    pickle.dump(
        all_images,
        f
    )

print(
    "\nImage index saved as image_index.pkl"
)