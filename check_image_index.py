import pickle

with open("image_index.pkl", "rb") as f:
    images = pickle.load(f)

print(images[0].keys())

print("\nFile:")
print(images[0]["file"])

print("\nOCR Preview:")
print(images[0]["ocr_text"][:500])