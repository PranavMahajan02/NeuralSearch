from enum import Enum


class PlatformName(str, Enum):

    local = "local"
    google_drive = "google_drive"
    github = "github"
