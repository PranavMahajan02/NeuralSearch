import pickle

with open("index.pkl", "rb") as f:
    docs = pickle.load(f)

for doc in docs:
    if doc["file"] == "Hall ticket.jpeg":
        print(doc["chunk"])
        print("=" * 50)