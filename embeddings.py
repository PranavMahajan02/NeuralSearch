from sentence_transformers import SentenceTransformer
from extract import extract_text
from chunk import chunk_text

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Extract text
text = extract_text("data/ADHAR.pdf")

# Create chunks
chunks = chunk_text(text)

# Generate embeddings
embeddings = model.encode(chunks)

print("Number of Chunks:", len(chunks))
print("Embedding Dimension:", len(embeddings[0]))

for i, embedding in enumerate(embeddings):
    print(f"\nChunk {i+1} Embedding (First 10 values):")
    print(embedding[:10])