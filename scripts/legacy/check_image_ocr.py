import pickle

with open(
    "image_index.pkl",
    "rb"
) as f:
    images = pickle.load(f)

filename = "WhatsApp Image 2026-06-21 at 5.34.44 PM (1).jpeg"

for image in images:

    if image["file"] == filename:

        print(image["ocr_text"])
        break