import pickle

with open("index.pkl", "rb") as f:
    docs = pickle.load(f)

for doc in docs:
    if doc["file"] == "admit-card-01.jpeg":
        print("=" * 50)
        print(doc["chunk"])