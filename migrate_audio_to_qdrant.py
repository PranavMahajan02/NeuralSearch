import pickle

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import AUDIO_COLLECTION

print("Loading audio_index.pkl...")

with open("audio_index.pkl", "rb") as f:
    audio = pickle.load(f)

print(f"Loaded {len(audio)} audio chunks.")

print(f"Migrating {len(audio)} audio vectors to Qdrant...")

insert_vectors(
    audio,
    AUDIO_COLLECTION
)

print("Migration completed successfully.")