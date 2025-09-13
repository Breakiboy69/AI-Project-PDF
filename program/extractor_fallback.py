import io
import fitz
import pytesseract
from PIL import Image
from .normalizer import normalize_for_tts


def _ocr_page(page, dpi=300, lang="deu+eng") -> str:
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang=lang)


def extract_text_simple(pdf_path: str) -> str:
    """Einfacher Extraktor: get_text(); wenn leer -> OCR für die ganze Seite."""
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        text = page.get_text()
        if not text or not text.strip():
            text = _ocr_page(page)
        parts.append((text or "").strip())
    doc.close()
    full_text = "\n\n".join(p for p in parts if p)
    full_text = normalize_for_tts(full_text)
    return full_text.strip()

