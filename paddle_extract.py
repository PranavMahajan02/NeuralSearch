from paddleocr import PaddleOCR

print("Loading PaddleOCR...")

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en"
)

print("PaddleOCR Loaded")


def extract_text(image_path):

    result = ocr.ocr(image_path)

    if result is None or result[0] is None:
        return ""

    text = []

    for line in result[0]:
        text.append(line[1][0])

    return " ".join(text)