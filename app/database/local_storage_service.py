from sqlalchemy.orm import Session

from app.database.models import LocalStorageFolder


def get_local_folders(
    db: Session,
    user_id
):

    return (

        db.query(LocalStorageFolder)

        .filter(

            LocalStorageFolder.user_id == user_id

        )

        .all()

    )


def add_local_folder(
    db: Session,
    user_id,
    folder_path: str
):

    existing = (

        db.query(LocalStorageFolder)

        .filter(

            LocalStorageFolder.user_id == user_id,

            LocalStorageFolder.folder_path == folder_path

        )

        .first()

    )

    if existing:

        return existing

    folder = LocalStorageFolder(

        user_id=user_id,

        folder_path=folder_path

    )

    db.add(folder)

    db.commit()

    db.refresh(folder)

    return folder


def remove_local_folder(
    db: Session,
    user_id,
    folder_path: str
):

    folder = (

        db.query(LocalStorageFolder)

        .filter(

            LocalStorageFolder.user_id == user_id,

            LocalStorageFolder.folder_path == folder_path

        )

        .first()

    )

    if folder:

        db.delete(folder)

        db.commit()