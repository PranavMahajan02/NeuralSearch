from easyocr_extract import extract_image_text

images = [
    "data/Hall ticket.jpeg",
    "data/india_post.jpeg",
    "data/mit_receipt.jpeg",
    "data/medical bill.jpeg"
]

for image_path in images:

    print("\n" + "=" * 80)
    print("FILE:", image_path)
    print("=" * 80)

    text = extract_image_text(image_path)

    print(text)