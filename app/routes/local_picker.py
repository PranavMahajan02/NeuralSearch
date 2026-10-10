"""Development-only native folder picker (tkinter dialog on the backend machine).

tkinter is imported lazily: Linux containers and CI runners usually have no Tk
libraries, and importing it at module level used to break the whole app in
development mode there. Without Tk the frontend hides the Browse button
(picker_available is false) and this endpoint answers 503.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends

from app.auth.auth_dependency import get_current_user
from app.core.errors import AppError
from app.models import response_models as rm

router = APIRouter(prefix="/platforms/local", tags=["Local Storage"])


@lru_cache(maxsize=1)
def tk_available() -> bool:
    try:
        import tkinter  # noqa: F401
    except ImportError:  # no python3-tk / libtk on this machine
        return False
    return True


@router.post("/pick-folder", response_model=rm.PickFolderResponse)
def pick_folder(current_user=Depends(get_current_user)):
    if not tk_available():
        raise AppError(503, "The folder picker is not available on this server. Type the folder path instead.")

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(title="Select Folder To Index")

    root.destroy()

    return {"folder": folder}
