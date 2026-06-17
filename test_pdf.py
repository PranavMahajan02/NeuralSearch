from pdf2image import convert_from_path

POPPLER_PATH = r"C:\Users\owner\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"

pages = convert_from_path(
    "data/id-document-01.pdf",
    poppler_path=POPPLER_PATH
)

print("Pages found:", len(pages))