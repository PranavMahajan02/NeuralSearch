import os
import requests

from app.platforms.github.auth import get_token


BASE_URL = "https://api.github.com"


def get_headers():

    return {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json"
    }


def list_repositories():

    response = requests.get(
        f"{BASE_URL}/user/repos",
        headers=get_headers()
    )

    response.raise_for_status()

    return response.json()

def list_repository_files(
    owner,
    repo,
    path=""
):

    response = requests.get(
        f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}",
        headers=get_headers()
    )

    response.raise_for_status()

    return response.json()

def get_user():

    response = requests.get(
        f"{BASE_URL}/user",
        headers=get_headers()
    )

    response.raise_for_status()

    return response.json()

def get_all_files(
    owner,
    repo,
    path=""
):

    items = list_repository_files(
        owner,
        repo,
        path
    )

    files = []

    for item in items:

        if item["type"] == "file":

            files.append(item)

        elif item["type"] == "dir":

            files.extend(

                get_all_files(
                    owner,
                    repo,
                    item["path"]
                )

            )

    return files
    
def download_file(file_info, download_folder="temp"):

    import os
    import requests

    os.makedirs(download_folder, exist_ok=True)

    url = file_info.get("download_url")

    if not url:
        print(f"No download URL: {file_info['path']}")
        return None

    safe_name = file_info["path"].replace("/", "__")
    file_path = os.path.join(download_folder, safe_name)

    try:

        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        if response.status_code != 200:
            print(f"Failed to download: {file_info['path']}")
            return None

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    except Exception as e:

        print(f"Download failed: {file_info['path']}")
        print(e)

        return None