from ocr_fusion import extract_best_text

text = extract_best_text(
    "data/Hall ticket.jpeg"
)

print(text)