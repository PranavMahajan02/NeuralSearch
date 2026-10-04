from fastapi import APIRouter
from fastapi import Depends

from app.auth.auth_dependency import get_current_user

import tkinter as tk
from tkinter import filedialog

router = APIRouter(
    prefix="/platforms/local",
    tags=["Local Storage"]
)


@router.post("/pick-folder")
def pick_folder(

    current_user=Depends(get_current_user)

):

    root = tk.Tk()

    root.withdraw()

    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(

        title="Select Folder To Index"

    )

    root.destroy()

    return {

        "folder": folder

    }