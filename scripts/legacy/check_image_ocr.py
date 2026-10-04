import pickle

with open(
    "image_index.pkl",
    "rb"
) as f:
    images = pickle.load(f)

filename = "photo-15.jpeg"

for image in images:

    if image["file"] == filename:

        print(image["ocr_text"])
        break