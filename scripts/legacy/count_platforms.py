from collections import Counter

from app.vectorstore.client import client
from app.vectorstore.config import IMAGE_COLLECTION

points, _ = client.scroll(
    collection_name=IMAGE_COLLECTION,
    limit=500
)

counter = Counter()

for p in points:
    counter[p.payload.get("platform", "unknown")] += 1

print("Images per platform:")
for platform, count in counter.items():
    print(f"{platform}: {count}")