# app/cache/search_cache.py

import os
import pickle

DOCUMENT_INDEX = []
IMAGE_INDEX = []
AUDIO_INDEX = []
VIDEO_INDEX = []

DOCUMENT_CONTENT_LOOKUP = {}
DOCUMENT_FILE_CHUNKS = {}


def _load_pickle(index_file):
    if not os.path.exists(index_file):
        return []

    with open(index_file, "rb") as f:
        return pickle.load(f)

def build_document_content_lookup():

    global DOCUMENT_CONTENT_LOOKUP

    lookup = {}

    for doc in DOCUMENT_INDEX:

        filename = doc.get("file")

        if not filename:
            continue

        if filename not in lookup:
            lookup[filename] = ""

        lookup[filename] += " " + doc.get("chunk", "")

    DOCUMENT_CONTENT_LOOKUP = lookup

    print(
        f"Document content lookup built ({len(DOCUMENT_CONTENT_LOOKUP)} files)"
    )

def build_document_file_chunks():

    global DOCUMENT_FILE_CHUNKS

    lookup = {}

    for doc in DOCUMENT_INDEX:

        filename = doc.get("file")

        if not filename:
            continue

        if filename not in lookup:
            lookup[filename] = []

        lookup[filename].append(doc)

    DOCUMENT_FILE_CHUNKS = lookup

    print(
        f"Document file chunk lookup built ({len(DOCUMENT_FILE_CHUNKS)} files)"
    )

def reload_document_cache():

    global DOCUMENT_INDEX

    DOCUMENT_INDEX = _load_pickle("index.pkl")

    print(
        f"Document cache loaded ({len(DOCUMENT_INDEX)} chunks)"
    )

    build_document_content_lookup()
    build_document_file_chunks()


def reload_image_cache():
    global IMAGE_INDEX
    IMAGE_INDEX = _load_pickle("image_index.pkl")
    print(f"Image cache loaded ({len(IMAGE_INDEX)} items)")


def reload_audio_cache():
    global AUDIO_INDEX
    AUDIO_INDEX = _load_pickle("audio_index.pkl")
    print(f"Audio cache loaded ({len(AUDIO_INDEX)} items)")


def reload_video_cache():
    global VIDEO_INDEX
    VIDEO_INDEX = _load_pickle("video_index.pkl")
    print(f"Video cache loaded ({len(VIDEO_INDEX)} items)")


def initialize_search_cache():
    print("=" * 50)
    print("Initializing Search Cache...")
    print("=" * 50)

    reload_document_cache()
    reload_image_cache()
    reload_audio_cache()
    reload_video_cache()

    print("Search Cache Ready.\n")