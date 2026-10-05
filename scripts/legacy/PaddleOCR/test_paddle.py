from paddle_extract import extract_text

images = [
    "../data/Hall ticket.jpeg",
    "../data/india_post.jpeg",
    "../data/medical bill.jpeg",
    "../data/mit_receipt.jpeg"
]

for image_path in images:

    print("\n" + "=" * 80)
    print("FILE:", image_path)
    print("=" * 80)

    text = extract_text(image_path)

    print(text[:2000])