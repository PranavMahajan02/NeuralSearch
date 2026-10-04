import pickle

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import VIDEO_COLLECTION

print("Loading video_index.pkl...")

with open("video_index.pkl", "rb") as f:
    videos = pickle.load(f)

print(f"Loaded {len(videos)} video chunks.")

print(f"Migrating {len(videos)} video vectors to Qdrant...")

insert_vectors(
    videos,
    VIDEO_COLLECTION
)

print("Migration completed successfully.")