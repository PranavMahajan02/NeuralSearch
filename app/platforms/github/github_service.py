import os
import requests

from app.platforms.github.oauth import get_access_token


BASE_URL = "https://api.github.com"

def github_get(url):

    try:

        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        if response.status_code == 401:
            raise RuntimeError("GitHub authentication failed (401).")

        if response.status_code == 403:
            raise RuntimeError("GitHub API rate limit exceeded (403).")

        response.raise_for_status()

        return response

    except requests.exceptions.Timeout:
        raise RuntimeError("GitHub request timed out.")

    except requests.exceptions.ConnectionError:
        raise RuntimeError("Unable to connect to GitHub.")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"GitHub request failed: {e}")


def get_headers():

    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/vnd.github+json"
    }


def list_repositories():

    response = github_get(
    f"{BASE_URL}/user/repos"
    )

    return response.json()

def list_repository_files(
    owner,
    repo,
    path=""
):

    response = github_get(
        f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    )

    return response.json()

def get_user():

    response = github_get(
        f"{BASE_URL}/user"
    )

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

    os.makedirs(download_folder, exist_ok=True)

    url = file_info.get("download_url")

    if not url:
        print(f"No download URL: {file_info['path']}")
        return None

    safe_name = file_info["path"].replace("/", "__")
    file_path = os.path.join(download_folder, safe_name)

    try:

        response = github_get(url)

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    except Exception as e:

        print(f"Download failed: {file_info['path']}")
        print(e)

        return None

def get_all_repository_paths():

    repos = list_repositories()

    paths = set()

    for repo in repos:

        owner = repo["owner"]["login"]
        repo_name = repo["name"]

        files = get_all_files(
            owner,
            repo_name
        )

        for file in files:

            paths.add(
                (
                    repo_name,
                    file["path"]
                )
            )

    return paths

def get_github_file_url(
    owner,
    repo,
    path
):

    return (
        f"https://github.com/"
        f"{owner}/"
        f"{repo}/"
        f"blob/main/"
        f"{path}"
    )