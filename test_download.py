import os

from app.platforms.google_drive.drive_service import (
    download_file
)

FILE_ID = "1_hhpihNzb5QSLtvDqAQhcM4d-IFf0eUs"

os.makedirs(
    "temp",
    exist_ok=True
)

download_file(
    FILE_ID,
    "temp/test.pdf"
)

print("Downloaded")