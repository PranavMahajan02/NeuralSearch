import time

from app.platforms.registry import platform_manager


def search(
    query: str,
    platform: str = "all",
    search_type: str = "all"
):

    start = time.perf_counter()

    if platform == "all":

        results = []

        for p in platform_manager.all():

            platform_start = time.perf_counter()

            platform_results = p.search(
                query=query,
                search_type=search_type
            )

            elapsed = time.perf_counter() - platform_start

            print(
                f"{p.__class__.__name__}: {elapsed:.2f} sec"
            )

            results.extend(platform_results)

        print(
            f"TOTAL SEARCH TIME: {time.perf_counter() - start:.2f} sec"
        )

        return results

    print("\n========== SEARCH DEBUG ==========")
    print("Requested platform:", platform)
    print("Registered platforms:", list(platform_manager.platforms.keys()))

    if platform == "local_storage":
        platform = "local"

    p = platform_manager.get(platform)

    print("Resolved platform:", p)
    print("==================================\n")

    if p is None:
        return []

    platform_start = time.perf_counter()

    results = p.search(
        query=query,
        search_type=search_type
    )

    elapsed = time.perf_counter() - platform_start

    print(
        f"{p.__class__.__name__}: {elapsed:.2f} sec"
    )

    print(
        f"TOTAL SEARCH TIME: {time.perf_counter() - start:.2f} sec"
    )

    return results