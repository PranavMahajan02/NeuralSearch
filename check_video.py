import pickle

with open(
    "video_index.pkl",
    "rb"
) as f:

    data = pickle.load(f)

print(data[0].keys())

print(
    len(
        data[0]["clip_embeddings"]
    )
)