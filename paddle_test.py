from paddleocr import PaddleOCR

print("Loading PaddleOCR...")

ocr = PaddleOCR()

print("PaddleOCR Loaded")

result = ocr.predict("data/Hall ticket.jpeg")

print(result)