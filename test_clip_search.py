from clip_utils import clip_search

queries = [
    "city road",
    "traffic",
    "apartment buildings",
    "balcony view",
    "sunset city"
]

for query in queries:

    print(f"\nQUERY: {query}")

    results = clip_search(query)

    for score, image in results[:5]:

        print(
            image["file"],
            round(float(score), 4)
        )