import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import requests

# Ordnerpfade (anpassen falls nötig)
INPUT_DIR = r"C:\Users\gamin\AI-Project-PDF\input"
TXT_DIR = r"C:\Users\gamin\AI-Project-PDF\txtspace"
OUTPUT_DIR = r"C:\Users\gamin\AI-Project-PDF\output"

# LM Studio API Endpunkt
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama_-_meta-llama-3-8b-instruct"  # <--- Hier dein Modellname

# OCR Funktion falls kein Text in PDF
def ocr_page(page):
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes()))
    text = pytesseract.image_to_string(img)
    return text

# Funktion um PDF zu Text zu extrahieren (inkl. OCR fallback)
def pdf_to_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if not text.strip():
            text = ocr_page(page)
        full_text += text + "\n"
    return full_text

# Funktion um Text an LLM zu senden und Antwort zu bekommen
def query_llm(prompt):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,  # Modellname hier verwenden
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Hauptfunktion: PDF lesen, Text speichern, zusammenfassen
def main():
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(INPUT_DIR, filename)
            print(f"Verarbeite {filename} ...")
            text = pdf_to_text(pdf_path)

            # Text in txtspace speichern
            txt_path = os.path.join(TXT_DIR, filename.replace(".pdf", ".txt"))
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

            # Text an LLM schicken und Zusammenfassung holen
            prompt = f"Fasse bitte den folgenden Text sinnvoll zusammen:\n\n{text}"
            summary = query_llm(prompt)

            # Zusammenfassung speichern
            output_path = os.path.join(OUTPUT_DIR, filename.replace(".pdf", "_summary.txt"))
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(summary if summary else "Keine Zusammenfassung erhalten.")
            
            print(f"Zusammenfassung gespeichert: {output_path}")

if __name__ == "__main__":
    main()
