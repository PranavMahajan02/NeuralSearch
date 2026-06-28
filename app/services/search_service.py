from app.platforms.registry import platform_manager


def search(
    query: str,
    platform: str = "all"
):

    if platform == "all":

        results = []

        for p in platform_manager.all():

            results.extend(
                p.search(query)
            )

        return results

    p = platform_manager.get(platform)

    if p is None:

        return []

    return p.search(query)