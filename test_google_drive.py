from app.platforms.google_drive.drive_service import get_drive_service

service = get_drive_service()

print("Connected!")

results = service.files().list(
    pageSize=10,
    fields="files(id,name,mimeType)"
).execute()

files = results.get("files", [])

for file in files:
    print(file["name"])