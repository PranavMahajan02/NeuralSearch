import requests

from app.platforms.google_photos.auth import get_credentials


def list_photos():

    creds = get_credentials()

    headers = {
        "Authorization": f"Bearer {creds.token}"
    }

    response = requests.get(
        "https://photoslibrary.googleapis.com/v1/mediaItems?pageSize=100",
        headers=headers
    )

    response.raise_for_status()

    return response.json().get(
        "mediaItems",
        []
    )