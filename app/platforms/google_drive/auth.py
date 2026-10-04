from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

CLIENT_SECRET = "credentials/client_secret.json"


def authenticate():

    flow = InstalledAppFlow.from_client_secrets_file(

        CLIENT_SECRET,

        SCOPES

    )

    creds = flow.run_local_server(

        port=0

    )

    return creds