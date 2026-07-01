from app.platforms.github.github_service import (
    list_repositories,
    get_all_files
)

repos = list_repositories()

for repo in repos:
    owner = repo["owner"]["login"]
    name = repo["name"]

    print(f"\nRepository: {name}")

    files = get_all_files(owner, name)

    found = False

    for f in files:
        ext = f["name"].lower().split(".")[-1]

        if ext in (
            "jpg", "jpeg", "png", "webp", "avif",
            "mp3", "wav", "m4a", "aac", "flac",
            "mp4", "avi", "mov", "mkv"
        ):
            found = True
            print(" ", f["path"])

    if not found:
        print("  No supported media files.")