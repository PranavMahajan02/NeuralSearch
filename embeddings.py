from app.ai.model_manager import model_manager


def get_embeddings(texts):

    embeddings = model_manager.semantic_model.encode(
        texts,
        convert_to_numpy=True
    )

    return embeddings