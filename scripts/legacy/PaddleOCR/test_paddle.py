from paddle_extract import extract_text

images = [
    "../data/admit-card-01.jpeg",
    "../data/postal-document-01.jpeg",
    "../data/medical-bill-01.jpeg",
    "../data/fee-receipt-01.jpeg"
]

for image_path in images:

    print("\n" + "=" * 80)
    print("FILE:", image_path)
    print("=" * 80)

    text = extract_text(image_path)

    print(text[:2000])