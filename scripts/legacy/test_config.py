from app.config.local_config import (
    remove_folder,
    load_local_folders
)

remove_folder(
    r"C:\Users\Pranav Mahajan\Downloads"
)

print(load_local_folders())