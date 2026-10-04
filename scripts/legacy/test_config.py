from app.config.local_config import (
    remove_folder,
    load_local_folders
)

remove_folder(
    r"C:\Users\owner\Downloads"
)

print(load_local_folders())