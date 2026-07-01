import json
import os

from app.auth.password import (
    hash_password,
    verify_password
)

from app.auth.jwt_handler import (
    create_access_token
)


USERS_FILE = "database/users.json"


def load_users():

    if not os.path.exists(USERS_FILE):

        return []

    with open(
        USERS_FILE,
        "r"
    ) as f:

        return json.load(f)


def save_users(users):

    with open(
        USERS_FILE,
        "w"
    ) as f:

        json.dump(
            users,
            f,
            indent=4
        )


def get_user_by_email(email):

    users = load_users()

    for user in users:

        if user["email"].lower() == email.lower():

            return user

    return None


def register_user(
    name,
    email,
    password
):

    users = load_users()

    if get_user_by_email(email):

        raise ValueError(
            "Email already registered."
        )

    if users:

        next_id = max(
            user["id"]
            for user in users
        ) + 1

    else:

        next_id = 1

    new_user = {

        "id": next_id,
        "name": name,
        "email": email,
        "password": hash_password(password)

    }

    users.append(new_user)

    save_users(users)

    return {

        "id": new_user["id"],
        "name": new_user["name"],
        "email": new_user["email"]

    }


def login_user(
    email,
    password
):

    user = get_user_by_email(email)

    if user is None:

        raise ValueError(
            "Invalid email or password."
        )

    if not verify_password(
        password,
        user["password"]
    ):

        raise ValueError(
            "Invalid email or password."
        )

    token = create_access_token(

        {
            "user_id": user["id"],
            "email": user["email"]
        }

    )

    return {

        "access_token": token,
        "token_type": "bearer"

    }