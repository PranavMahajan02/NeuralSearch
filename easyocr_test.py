from easyocr_extract import extract_image_text

text = extract_image_text("data/medical bill.jpeg")

print(text)