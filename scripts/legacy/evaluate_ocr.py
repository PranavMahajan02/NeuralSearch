import pandas as pd

from video_search import (
    search_video
)

df = pd.read_csv(
    "evaluation.csv"
)

total = 0
correct = 0

for _, row in df.iterrows():

    query = str(
        row["Query"]
    ).strip()

    expected = str(
        row["Expected"]
    ).strip()

    results = search_video(
        query
    )

    total += 1

    if not results:

        print(f"✗ {query}")

        print(
            f"Expected : {expected}"
        )

        print(
            "Found    : No Result"
        )

        print()

        continue

    found = False

    for result in results:

        if (
            result["file"]
            .strip()
            .lower()
            ==
            expected
            .strip()
            .lower()
        ):

            found = True
            break

    if found:

        correct += 1

        print(
            f"✓ {query}"
        )

    else:

        print(
            f"✗ {query}"
        )

        print(
            f"Expected : {expected}"
        )

        print(
            "Retrieved Video Files:"
        )

        for result in results:

            print(
                f"  - {result['file']}"
            )

        print()

accuracy = (
    correct / total
) * 100

print("\n===================")

print(
    f"Total Queries           : {total}"
)

print(
    f"Successful Queries      : {correct}"
)

print(
    f"Video Retrieval Success : {accuracy:.2f}%"
)

print("===================")