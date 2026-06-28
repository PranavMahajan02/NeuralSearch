from paddleocr import PaddleOCR

ocr = None


def get_ocr():

    global ocr

    if ocr is None:

        print("Loading PaddleOCR...")

        ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en"
        )

        print("PaddleOCR Loaded")

    return ocr


def extract_text(image_path):

    ocr = get_ocr()

    result = ocr.ocr(image_path)

    if result is None or result[0] is None:
        return ""

    text = []

    for line in result[0]:
        text.append(line[1][0])

    return " ".join(text)