model = None


def get_model():

    global model

    if model is None:

        from sentence_transformers import SentenceTransformer

        print("Loading embedding model...")

        model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            device="cuda"
        )

        print("Embedding model loaded.")

    return model


def get_embeddings(texts):

    model = get_model()

    embeddings = model.encode(
        texts,
        convert_to_numpy=True
    )

    return embeddings