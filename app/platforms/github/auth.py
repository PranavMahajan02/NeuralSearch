import os


TOKEN_FILE = "***REDACTED***"


def save_token(token):

    with open(TOKEN_FILE, "w") as f:
        f.write(token.strip())


def get_token():

    if not os.path.exists(TOKEN_FILE):
        raise Exception("GitHub token not found.")

    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()