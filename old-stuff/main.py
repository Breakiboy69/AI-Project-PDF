import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import requests

# -------------------------
# Pfade & API
# -------------------------
INPUT_DIR  = r"C:\Users\gamin\AI-Project-PDF\input"
TXT_DIR    = r"C:\Users\gamin\AI-Project-PDF\txtspace"
OUTPUT_DIR = r"C:\Users\gamin\AI-Project-PDF\output"

API_URL    = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama_-_meta-llama-3-8b-instruct"  # aus /v1/models

# -------------------------
# MODI: wähle einen der drei
# -------------------------
# "clean_for_tts"  -> Inhalt NICHT kürzen, nur minimal für TTS bereinigen (LLM strikt)
# "tts_passthrough"-> KEIN LLM; Rohtext 1:1 für TTS
# "summary"        -> echte Zusammenfassung (kurz & knackig)
MODE = "clean_for_tts"

# -------------------------
# Optional: Extractor v2
# -------------------------
USE_EXTRACTOR_V2 = True   # True = nutze extractor_v2.py (falls vorhanden), False = einfacher Extraktor

if USE_EXTRACTOR_V2:
    try:
        from extractor_v2 import extract_pdf_v2 as extract_text
        print("[INFO] extractor_v2 wird genutzt.")
    except ImportError:
        print("[WARNUNG] extractor_v2 nicht gefunden – nutze Standard-Extractor.")
        USE_EXTRACTOR_V2 = False

if not USE_EXTRACTOR_V2:
    def ocr_page(page, dpi=300, lang="deu+eng"):
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, lang=lang)

    def extract_text(pdf_path):
        """Einfach: erst get_text(); wenn leer -> OCR für ganze Seite."""
        doc = fitz.open(pdf_path)
        parts = []
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text()
            if not text or not text.strip():
                text = ocr_page(page)
            parts.append(text.strip())
        doc.close()
        full_text = "\n\n".join(p for p in parts if p)
        full_text = full_text.replace("\u00ad", "")  # Soft Hyphen
        while "  " in full_text:
            full_text = full_text.replace("  ", " ")
        return full_text.strip()

# -------------------------
# Prompts
# -------------------------
PROMPT_CLEAN_SYSTEM = (
    "Antworte ausschließlich auf Deutsch. "
    "Gib den Text inhaltlich vollständig wieder (keine Kürzung, keine Interpretation, kein neues Wissen). "
    "Erlaube nur minimale Bereinigung für TTS (z. B. doppelte Leerzeilen, harte Umbrüche, offensichtliche Artefakte). "
    "Wenn Informationen im Text fehlen, schreibe ausdrücklich: 'Nicht im Text vorhanden'. "
    "Beantworte KEINE Fragen und forme den Text NICHT zu Q&A um."
)

PROMPT_SUMMARY_SYSTEM = (
    "Du bist ein hilfsbereiter Assistent. Fasse den folgenden Text auf Deutsch präzise zusammen. "
    "Erhalte alle wichtigen Fachbegriffe, Definitionen, Zahlen und Beispiele. "
    "Keine Halluzinationen, keine externen Infos. "
)

# -------------------------
# Utils
# -------------------------
def ensure_dirs():
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def chunk_text(text, max_chars=8000):
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + max_chars, n)
        cut = text.rfind("\n", start, end)
        if cut == -1 or cut <= start:
            cut = end
        chunks.append(text[start:cut].strip())
        start = cut
    return [c for c in chunks if c]

def query_llm(messages, *, temperature=0.0, top_p=0.1):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

# -------------------------
# Hauptlogik
# -------------------------
def process_file(pdf_filename):
    pdf_path = os.path.join(INPUT_DIR, pdf_filename)
    print(f"Verarbeite {pdf_filename} ...")

    # 1) PDF -> Rohtext (immer)
    raw_text = extract_text(pdf_path)

    # 2) Rohtext speichern
    txt_path = os.path.join(TXT_DIR, pdf_filename.replace(".pdf", ".txt"))
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    # 3) je nach MODE weiterverarbeiten
    if MODE == "tts_passthrough":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_tts_ready.txt"))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"TTS-Text gespeichert: {out_path}")
        return

    if MODE == "clean_for_tts":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_clean.txt"))
        chunks = chunk_text(raw_text, max_chars=8000)
        results = []
        for idx, ch in enumerate(chunks, start=1):
            messages = [
                {"role": "system", "content": PROMPT_CLEAN_SYSTEM},
                {"role": "user", "content": f"Bereinige NUR diesen Text für TTS, ohne ihn zu kürzen oder umzuschreiben:\n\n---\n{ch}\n---"}
            ]
            try:
                ans = query_llm(messages, temperature=0.0, top_p=0.1)
            except Exception as e:
                ans = f"[Fehler bei Teil {idx}: {e}]"
            results.append(ans)
        final_text = "\n\n".join(results).strip()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_text or "Keine Ausgabe erhalten.")
        print(f"Bereinigter TTS-Text gespeichert: {out_path}")
        return

    if MODE == "summary":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_summary.txt"))
        chunks = chunk_text(raw_text, max_chars=8000)
        results = []
        for idx, ch in enumerate(chunks, start=1):
            messages = [
                {"role": "system", "content": PROMPT_SUMMARY_SYSTEM},
                {"role": "user", "content": f"Fasse diesen Abschnitt zusammen (Teil {idx}/{len(chunks)}):\n\n{ch}"}
            ]
            try:
                ans = query_llm(messages, temperature=0.2, top_p=0.9)
            except Exception as e:
                ans = f"[Fehler bei Teil {idx}: {e}]"
            results.append(ans)
        final_text = "\n\n".join(results).strip()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_text or "Keine Zusammenfassung erhalten.")
        print(f"Zusammenfassung gespeichert: {out_path}")
        return

    print(f"[WARN] Unbekannter MODE: {MODE}")

def main():
    ensure_dirs()
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            process_file(filename)

if __name__ == "__main__":
    main()
