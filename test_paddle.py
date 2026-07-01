from paddleocr import PaddleOCR

print("Loading PaddleOCR...")

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en"
)

print("PaddleOCR loaded successfully!")

image_path = "data/Hall ticket.jpeg"   # Replace with your image path

result = ocr.ocr(image_path)

print("\nOCR Result:\n")

for line in result[0]:
    print(line[1][0])