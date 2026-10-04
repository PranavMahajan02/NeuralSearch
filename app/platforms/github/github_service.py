import os
import requests
from sqlalchemy.orm import Session

from app.platforms.github.oauth import get_access_token

BASE_URL = "https://api.github.com"


def github_get(
    db: Session,
    user_id,
    url
):

    headers = {
        "Authorization": f"Bearer {get_access_token(db, user_id)}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code == 401:
        raise RuntimeError("GitHub authentication failed.")

    if response.status_code == 403:
        raise RuntimeError("GitHub API rate limit exceeded.")

    response.raise_for_status()

    return response


def get_user(
    db: Session,
    user_id
):

    response = github_get(
        db,
        user_id,
        f"{BASE_URL}/user"
    )

    return response.json()


def list_repositories(
    db: Session,
    user_id
):

    response = github_get(
        db,
        user_id,
        f"{BASE_URL}/user/repos"
    )

    return response.json()


def list_repository_files(
    db: Session,
    user_id,
    owner,
    repo,
    path=""
):

    response = github_get(
        db,
        user_id,
        f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    )

    return response.json()


def get_all_files(
    db: Session,
    user_id,
    owner,
    repo,
    path=""
):

    items = list_repository_files(
        db,
        user_id,
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
                    db,
                    user_id,
                    owner,
                    repo,
                    item["path"]
                )

            )

    return files


def download_file(
    db: Session,
    user_id,
    file_info,
    download_folder="temp"
):

    os.makedirs(download_folder, exist_ok=True)

    url = file_info["download_url"]

    if url is None:
        return None

    response = github_get(
        db,
        user_id,
        url
    )

    safe_name = file_info["path"].replace("/", "__")

    file_path = os.path.join(
        download_folder,
        safe_name
    )

    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path


def get_github_file_url(
    owner,
    repo,
    path
):

    return (
        f"https://github.com/"
        f"{owner}/"
        f"{repo}/blob/main/"
        f"{path}"
    )