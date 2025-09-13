import fitz
import math
from pytesseract import image_to_data, Output
from PIL import Image
import io

HEADER_FOOTER_MARGIN = 0.08  # oberste/unterste 8%

def _sort_blocks_reading_order(blocks):
    # sortiere nach y, dann x (auf 0.1 runden für Stabilität)
    return sorted(blocks, key=lambda b: (round(b["bbox"][1], 1), round(b["bbox"][0], 1)))

def _filter_header_footer(blocks, page_height):
    top, bot = page_height * HEADER_FOOTER_MARGIN, page_height * (1 - HEADER_FOOTER_MARGIN)
    def is_hf(b):
        y0, y1 = b["bbox"][1], b["bbox"][3]
        return y1 < top or y0 > bot
    return [b for b in blocks if not is_hf(b)]

def extract_text_blocks(page):
    """Textblöcke mit Geometrie aus PyMuPDF, geordnet, mit Header/Footer-Filter."""
    page_h = page.rect.height
    raw = page.get_text("dict")
    blocks = [b for b in raw.get("blocks", []) if "lines" in b]
    blocks = _sort_blocks_reading_order(blocks)
    blocks = _filter_header_footer(blocks, page_h)

    out_lines = []
    for b in blocks:
        for line in b["lines"]:
            parts = []
            for span in line["spans"]:
                parts.append(span["text"])
            text_line = " ".join(parts).strip()
            if text_line:
                out_lines.append(text_line)
        out_lines.append("")  # Absatz
    return "\n".join(out_lines).strip()

def extract_annotations(page):
    """Noteshelf-Textboxen etc. einsammeln (falls als Annotation gespeichert)."""
    lines = []
    annots = page.annots()
    if annots:
        for a in annots:
            c = (a.info or {}).get("content")
            if c and c.strip():
                lines.append(f"[Notiz] {c.strip()}")
    return "\n".join(lines)

def ocr_page_with_layout(page, dpi=300, lang="deu+eng"):
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    data = image_to_data(img, lang=lang, config="--oem 3 --psm 6", output_type=Output.DICT)
    rows = []
    n = len(data["text"])
    for i in range(n):
        txt = data["text"][i]
        conf = data["conf"][i]
        if txt and txt.strip() and conf not in ("-1", "") and int(conf) >= 70:
            rows.append((data["top"][i], data["left"][i], txt))
    # zu Zeilen gruppieren (grobe Toleranz)
    rows.sort(key=lambda t: (t[0], t[1]))
    lines = []
    cur_y = None; buf = []
    for y, x, tok in rows:
        if cur_y is None:
            cur_y = y
        # Neue Zeile, wenn y-Abstand größer als ~10 px
        if abs(y - cur_y) > 10:
            lines.append(" ".join(buf))
            buf = [tok]; cur_y = y
        else:
            buf.append(tok)
    if buf:
        lines.append(" ".join(buf))
    return "\n".join(lines)

def extract_page_text_v2(page):
    # 1) Versuche strukturierten Text
    txt = extract_text_blocks(page)
    # 2) Annotations dran
    ann = extract_annotations(page)
    # 3) Falls nix da -> OCR mit Layout
    if not txt.strip():
        txt = ocr_page_with_layout(page)
    # zusammensetzen
    parts = [p for p in [txt, ann] if p]
    return "\n\n".join(parts).strip()

def extract_pdf_v2(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for p in doc:
        pages.append(extract_page_text_v2(p))
    doc.close()
    # leichte TTS-Normalisierung (kein Kürzen!)
    text = "\n\n".join(pages)
    text = text.replace("\u00ad", "")  # Soft hyphen raus
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()
