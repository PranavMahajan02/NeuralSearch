from image_search import search_images

def search_image(
    query: str,
    platform="all"
):
    return search_images(
        query,
        platform
    )