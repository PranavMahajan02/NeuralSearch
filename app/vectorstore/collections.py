from qdrant_client.models import (
    Distance,
    VectorParams
)

from app.vectorstore.client import client

from app.vectorstore.config import (
    TEXT_COLLECTION,
    IMAGE_COLLECTION
)

from app.vectorstore.config import (
    TEXT_COLLECTION,
    IMAGE_COLLECTION,
    AUDIO_COLLECTION,
)

from app.vectorstore.config import (
    TEXT_COLLECTION,
    IMAGE_COLLECTION,
    AUDIO_COLLECTION,
    VIDEO_COLLECTION,
)

from app.vectorstore.config import (
    TEXT_COLLECTION,
    IMAGE_COLLECTION,
    AUDIO_COLLECTION,
    VIDEO_COLLECTION,
    VIDEO_FRAME_COLLECTION,
)

def create_collection():

    collections = client.get_collections().collections

    names = [c.name for c in collections]

    # -------------------------
    # Text Collection
    # -------------------------

    if TEXT_COLLECTION not in names:

        client.create_collection(

            collection_name=TEXT_COLLECTION,

            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )

        )

        print(f"{TEXT_COLLECTION} collection created.")

    else:

        print(f"{TEXT_COLLECTION} already exists.")

    # -------------------------
    # Image Collection
    # -------------------------

    if IMAGE_COLLECTION not in names:

        client.create_collection(

            collection_name=IMAGE_COLLECTION,

            vectors_config=VectorParams(
                size=512,
                distance=Distance.COSINE
            )

        )

        print(f"{IMAGE_COLLECTION} collection created.")

    else:

        print(f"{IMAGE_COLLECTION} already exists.")

    # -------------------------
    # Audio Collection
    # -------------------------

    if AUDIO_COLLECTION not in names:

        client.create_collection(

            collection_name=AUDIO_COLLECTION,

            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )

        )

        print(f"{AUDIO_COLLECTION} collection created.")

    else:

        print(f"{AUDIO_COLLECTION} already exists.")

    # -------------------------
    # Video Collection
    # -------------------------

    if VIDEO_COLLECTION not in names:

        client.create_collection(

            collection_name=VIDEO_COLLECTION,

            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )

        )

        print(f"{VIDEO_COLLECTION} collection created.")

    else:

        print(f"{VIDEO_COLLECTION} already exists.")


    # -------------------------
    # Video Frame Collection
    # -------------------------

    if VIDEO_FRAME_COLLECTION not in names:

        client.create_collection(

            collection_name=VIDEO_FRAME_COLLECTION,

            vectors_config=VectorParams(
                size=512,
                distance=Distance.COSINE
            )

        )

        print(f"{VIDEO_FRAME_COLLECTION} collection created.")

    else:

        print(f"{VIDEO_FRAME_COLLECTION} already exists.")