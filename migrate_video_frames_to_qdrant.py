import pickle

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import VIDEO_FRAME_COLLECTION

print("Loading video_index.pkl...")

with open("video_index.pkl", "rb") as f:
    videos = pickle.load(f)

frames = []

for video in videos:

    clip_embeddings = video.get("clip_embeddings", [])

    for i, embedding in enumerate(clip_embeddings):

        frames.append(
            {
                "file": video["file"],
                "path": video["path"],
                "platform": video["platform"],
                "file_id": video["file_id"],
                "owner": video.get("owner"),
                "repo": video.get("repo"),
                "sha": video.get("sha"),
                "last_modified": video.get("last_modified"),
                "frame_number": i,
                "chunk": f"Frame {i}",
                "embedding": embedding,
            }
        )

print(f"Loaded {len(frames)} frame embeddings.")

BATCH_SIZE = 200

print(f"Migrating {len(frames)} frame embeddings...")

for i in range(0, len(frames), BATCH_SIZE):

    batch = frames[i:i + BATCH_SIZE]

    insert_vectors(
        batch,
        VIDEO_FRAME_COLLECTION
    )

    print(
        f"Inserted {min(i+BATCH_SIZE, len(frames))}/{len(frames)}"
    )

print("Migration completed successfully.")