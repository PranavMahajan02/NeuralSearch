import pickle

with open("image_index.pkl", "rb") as f:
    data = pickle.load(f)

for img in data:

    if img["file"] == "postal-document-01.jpeg":

        print(img.keys())

        print("\nOCR TEXT:\n")

        print(
            img.get(
                "ocr_text",
                "NO OCR TEXT FOUND"
            )
        )