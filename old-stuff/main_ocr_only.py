import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import requests

# Ordnerpfade
INPUT_DIR = r"C:\Users\gamin\AI-Project-PDF\input"
TXT_DIR = r"C:\Users\gamin\AI-Project-PDF\txtspace"
OUTPUT_DIR = r"C:\Users\gamin\AI-Project-PDF\output"

# LM Studio API
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama_-_meta-llama-3-8b-instruct"

# Systemprompt für TTS-Vorbereitung
SYSTEM_PROMPT = """
Du bist ein Assistent, der Schulungsmaterialien aus PDF-Dokumenten für die Sprachausgabe aufbereitet.

Ziel:
- Gib den Text genau so zurück, wie er ist. Keine Kürzung, keine Änderung, keine Zusammenfassung.
-Nun bereite ihn so auf, dass er gut als Klartext für ein TTS-System geeignet ist (z.B. entferne ungewöhnliche Formatierungen, aber Inhalt bleibt komplett erhalten).
- Zeichnungen oder beschriebene Grafiken bitte ignorieren.
- Antworte ausschließlich auf Deutsch.
"""

# OCR als Fallback

def ocr_page(page):
    pix = page.get_pixmap(dpi=300)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    text = pytesseract.image_to_string(img, lang="deu")
    return text

# PDF zu Rohtext

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        text = page.get_text()
        if not text.strip():
            text = ocr_page(page)
        full_text += text + "\n"
    doc.close()
    return full_text

# Anfrage an LLM für TTS-Vorbereitung

def clean_text_for_tts(raw_text):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text}
        ],
        "temperature": 0.3,
        "stream": False
    }
    response = requests.post(API_URL, json=payload)
    result = response.json()
    return result["choices"][0]["message"]["content"]

# Hauptverarbeitung

def main():
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(INPUT_DIR, filename)
            print(f"Verarbeite {filename} ...")

            raw_text = extract_text_from_pdf(pdf_path)
            txt_path = os.path.join(TXT_DIR, filename.replace(".pdf", ".txt"))
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(raw_text)

            cleaned = clean_text_for_tts(raw_text)
            out_path = os.path.join(OUTPUT_DIR, filename.replace(".pdf", "_tts_ready.txt"))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
            print(f"Fertig: {out_path}\n")

if __name__ == "__main__":
    main()
