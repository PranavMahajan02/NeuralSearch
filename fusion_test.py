from ocr_fusion import extract_best_text

text = extract_best_text(
    "data/admit-card-01.jpeg"
)

print(text)