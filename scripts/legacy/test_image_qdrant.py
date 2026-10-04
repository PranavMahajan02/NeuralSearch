from app.vectorstore.client import client
from app.vectorstore.config import IMAGE_COLLECTION

print("Connected to Qdrant")

points, _ = client.scroll(
    collection_name=IMAGE_COLLECTION,
    limit=200
)

found = False

for p in points:
    file = p.payload.get("file", "").lower()
    ocr = (p.payload.get("ocr_text") or "").lower()

    if "aad" in file or "aad" in ocr:
        found = True
        print("-" * 50)
        print("FILE     :", p.payload.get("file"))
        print("PLATFORM :", p.payload.get("platform"))
        print("OCR      :", p.payload.get("ocr_text"))

if not found:
    print("No Aadhaar-related image found in the collection.")