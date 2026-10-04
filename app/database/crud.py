from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    User,
    PlatformConnection,
    LocalStorageFolder,
    IndexingJob,
    IndexedFile
)


# ==========================================================
# USERS
# ==========================================================

def get_user_by_email(
    db: Session,
    email: str
):

    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def create_user(
    db: Session,
    email: str,
    full_name: str,
    provider: str,
    provider_user_id: str
):

    user = User(
        email=email,
        full_name=full_name,
        provider=provider,
        provider_user_id=provider_user_id
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    return user


def update_last_login(
    db: Session,
    user: User
):

    user.last_login = datetime.utcnow()

    db.commit()

    db.refresh(user)

    return user


# ==========================================================
# PLATFORM CONNECTIONS
# ==========================================================

def get_platform_connection(
    db: Session,
    user_id,
    platform: str
):

    return (
        db.query(PlatformConnection)
        .filter(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == platform
        )
        .first()
    )


def save_platform_connection(
    db: Session,
    user_id,
    platform,
    account_email,
    account_name,
    access_token,
    refresh_token
):

    connection = get_platform_connection(
        db,
        user_id,
        platform
    )

    if connection:

        connection.account_email = account_email
        connection.account_name = account_name
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.connected = True

    else:

        connection = PlatformConnection(
            user_id=user_id,
            platform=platform,
            account_email=account_email,
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
            connected=True
        )

        db.add(connection)

    db.commit()

    db.refresh(connection)

    return connection


# ==========================================================
# LOCAL STORAGE
# ==========================================================

def add_local_folder(
    db: Session,
    user_id,
    folder_path
):

    folder = LocalStorageFolder(
        user_id=user_id,
        folder_path=folder_path
    )

    db.add(folder)

    db.commit()

    db.refresh(folder)

    return folder


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


# ==========================================================
# INDEXING JOBS
# ==========================================================

def get_indexing_job(
    db: Session,
    user_id,
    platform
):

    return (
        db.query(IndexingJob)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.platform == platform
        )
        .first()
    )


def create_or_update_indexing_job(
    db: Session,
    user_id,
    platform,
    total_files
):

    job = get_indexing_job(
        db,
        user_id,
        platform
    )

    if job:

        job.total_files = total_files
        job.indexed_files = 0
        job.status = "running"
        job.started_at = datetime.utcnow()

    else:

        job = IndexingJob(
            user_id=user_id,
            platform=platform,
            total_files=total_files,
            indexed_files=0,
            status="running",
            started_at=datetime.utcnow()
        )

        db.add(job)

    db.commit()

    db.refresh(job)

    return job


# ==========================================================
# INDEXED FILES
# ==========================================================

def save_indexed_file(
    db: Session,
    **kwargs
):

    file = IndexedFile(**kwargs)

    db.add(file)

    db.commit()

    db.refresh(file)

    return file