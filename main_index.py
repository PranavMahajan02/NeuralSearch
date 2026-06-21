import sys
import subprocess
import time


def run_document_index():

    print("\n==========================")
    print("DOCUMENT INDEXING STARTED")
    print("==========================\n")

    start = time.time()

    result = subprocess.run(
        [sys.executable, "index.py"]
    )

    end = time.time()

    if result.returncode == 0:

        print(
            f"\nDocument Indexing Finished "
            f"in {end-start:.2f}s"
        )

    else:

        print(
            "\nDocument Indexing Failed"
        )


def run_image_index():

    print("\n======================")
    print("IMAGE INDEXING STARTED")
    print("======================\n")

    start = time.time()

    result = subprocess.run(
        [sys.executable, "clip_index.py"]
    )

    end = time.time()

    if result.returncode == 0:

        print(
            f"\nImage Indexing Finished "
            f"in {end-start:.2f}s"
        )

    else:

        print(
            "\nImage Indexing Failed"
        )


if __name__ == "__main__":

    print(
        f"\nUsing Python:\n{sys.executable}\n"
    )

    total_start = time.time()

    print(
        "================================="
    )
    print(
        "COGNISEEK UNIFIED INDEXING"
    )
    print(
        "=================================\n"
    )

    run_document_index()

    run_image_index()

    total_time = (
        time.time()
        - total_start
    )

    print(
        "\n================================="
    )
    print(
        "ALL INDEXING COMPLETED"
    )
    print(
        "================================="
    )

    print(
        f"\nTotal Time: "
        f"{total_time:.2f}s"
    )