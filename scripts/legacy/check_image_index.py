import pickle
from collections import Counter

with open("image_index.pkl", "rb") as f:
    images = pickle.load(f)

print("Total images:", len(images))

counter = Counter()

for img in images:
    counter[img.get("platform", "unknown")] += 1

print("\nPlatforms:")
for platform, count in counter.items():
    print(f"{platform}: {count}")