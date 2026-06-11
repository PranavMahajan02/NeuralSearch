from paddleocr import PaddleOCR

print("Loading PaddleOCR...")

ocr = PaddleOCR()

print("PaddleOCR Loaded")

result = ocr.predict("data/admit-card-01.jpeg")

print(result)