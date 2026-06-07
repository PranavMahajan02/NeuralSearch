from PIL import Image, ImageEnhance
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_image_text(image_path):

    image = Image.open(image_path)

    image = image.convert("L")

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    text = pytesseract.image_to_string(image)

    return text