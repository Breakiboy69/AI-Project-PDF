# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\__init__.py
__all__ = []


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\config.py
import os

# Basisverzeichnis (bei Bedarf anpassen)
BASE_DIR = r"C:\\Users\\gamin\\AI-Project-PDF"
INPUT_DIR = os.path.join(BASE_DIR, "input")
TXT_DIR = os.path.join(BASE_DIR, "txtspace")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# LM Studio API
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama_-_meta-llama-3-8b-instruct"  # aus /v1/models

# Betriebsmodus: "clean_for_tts" | "tts_passthrough" | "summary"
MODE = "clean_for_tts"

# Extractor: v2 nutzen, falls Datei vorhanden/importierbar
USE_EXTRACTOR_V2 = True

# LLM-Parameter
MAX_TOKENS_CLEAN = 1500
MAX_TOKENS_SUMMARY = 1500
CHUNK_SIZE = 5000
SINGLECALL_LIMIT = 6000


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\prompts.py
PROMPT_CLEAN_SYSTEM = (
    "Antworte ausschließlich auf Deutsch. "
    "Gib den Text inhaltlich vollständig wieder (keine Kürzung, keine Interpretation, kein neues Wissen). "
    "Erlaube nur minimale Bereinigung für TTS (z. B. doppelte Leerzeilen, harte Umbrüche, offensichtliche Artefakte). "
    "Gib AUSSCHLIESSLICH den bereinigten Text zurück – KEINE Einleitung, KEINE Erklärungen, KEINE Formulierungen wie 'Hier ist der Text ...'. "
    "Wenn Informationen im Text fehlen, schreibe ausdrücklich: 'Nicht im Text vorhanden'. "
    "Beantworte KEINE Fragen und forme den Text NICHT zu Q&A um."
)

PROMPT_SUMMARY_SYSTEM = (
    "Du bist ein hilfsbereiter Assistent. Fasse den folgenden Text auf Deutsch präzise zusammen. "
    "Erhalte alle wichtigen Fachbegriffe, Definitionen, Zahlen und Beispiele. "
    "Keine Halluzinationen, keine externen Infos. "
    "Gib AUSSCHLIESSLICH die Zusammenfassung ohne Einleitung aus."
)


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\normalizer.py
import re

_SOFT_HYPHEN = "\u00ad"


def normalize_for_tts(text: str) -> str:
    """Bereinigt Nicht-Inhaltsartefakte vor TTS. Keine Kürzung, kein Umschreiben."""
    if not text:
        return ""
    # Soft hyphen entfernen
    text = text.replace(_SOFT_HYPHEN, "")
    # Silbentrennung am Zeilenende: "so-\nmit" -> "somit"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Einzelne Zeilenumbrüche (kein Absatz) in Space wandeln
    text = re.sub(r"(?<![.!?:])\n(?!\n)", " ", text)
    # Mehrfach-Leerzeichen reduzieren
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Überlange Leerzeilenfolgen eindampfen
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_llm_output(s: str) -> str:
    """Entfernt typische Boilerplates/Wrapper aus LLM-Antworten, ohne Inhalt zu verlieren."""
    if not s:
        return s
    s = s.strip()
    # Code fences entfernen
    if s.startswith("```"):
        s = re.sub(r"^```[\w-]*\n?", "", s, count=1)
        s = re.sub(r"\n?```$", "", s, count=1)
    # Häufige Einleitungs-Phrasen entfernen
    s = re.sub(r"^(Hier ist .*?:\s*)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^(Bereinigter Text:?\s*)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^(Zusammenfassung:?\s*)", "", s, flags=re.IGNORECASE)
    # Überzählige Leerzeilen reduzieren
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\chunking.py
from typing import List


def chunk_text(text: str, max_chars: int) -> List[str]:
    """Zerlegt Text an sinnvollen Grenzen (bevorzugt Zeilenumbrüche)."""
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + max_chars, n)
        cut = text.rfind("\n", start, end)
        if cut == -1 or cut <= start:
            cut = end
        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        start = cut
    return chunks


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\llm.py
import requests
from .normalizer import sanitize_llm_output


def query_llm(api_url: str, model_name: str, messages, *,
              temperature: float = 0.0, top_p: float = 0.1,
              max_tokens: int = 1500,
              presence_penalty: float = 0.0, frequency_penalty: float = 0.0,
              timeout: int = 180) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "max_tokens": max_tokens,
    }
    resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return sanitize_llm_output(content)


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\extractor_fallback.py
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


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\extractor_v2.py
import io
import fitz
from pytesseract import image_to_data, Output
from PIL import Image

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
    cur_y = None
    buf = []
    for y, x, tok in rows:
        if cur_y is None:
            cur_y = y
        # Neue Zeile, wenn y-Abstand größer als ~10 px
        if abs(y - cur_y) > 10:
            if buf:
                lines.append(" ".join(buf))
            buf = [tok]
            cur_y = y
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
    from .normalizer import normalize_for_tts
    doc = fitz.open(pdf_path)
    pages = []
    for p in doc:
        pages.append(extract_page_text_v2(p))
    doc.close()
    text = "\n\n".join(pages)
    text = normalize_for_tts(text)  # leichte Normalisierung (keine Kürzung)
    return text.strip()


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\utils.py
import os
from .config import TXT_DIR, OUTPUT_DIR


def ensure_dirs():
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===== C:\\Users\\gamin\\AI-Project-PDF\\program\\main.py
import os
from .config import (
    INPUT_DIR, TXT_DIR, OUTPUT_DIR,
    API_URL, MODEL_NAME, MODE,
    USE_EXTRACTOR_V2, MAX_TOKENS_CLEAN, MAX_TOKENS_SUMMARY,
    CHUNK_SIZE, SINGLECALL_LIMIT
)
from .utils import ensure_dirs
from .normalizer import normalize_for_tts
from .chunking import chunk_text
from .llm import query_llm

# Versuche den erweiterten Extraktor zu laden
if USE_EXTRACTOR_V2:
    try:
        from .extractor_v2 import extract_pdf_v2 as extract_text
        print("[INFO] extractor_v2 wird genutzt.")
    except Exception as e:
        print(f"[WARNUNG] extractor_v2 nicht verfügbar ({e!r}) – nutze einfachen Extraktor.")
        from .extractor_fallback import extract_text_simple as extract_text
else:
    from .extractor_fallback import extract_text_simple as extract_text

from .prompts import PROMPT_CLEAN_SYSTEM, PROMPT_SUMMARY_SYSTEM


def _save(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def process_file(pdf_filename: str):
    pdf_path = os.path.join(INPUT_DIR, pdf_filename)
    print(f"[INFO] Verarbeite {pdf_filename} …")

    # 1) PDF -> Rohtext
    raw_text = extract_text(pdf_path)

    # 1a) Vor-Normalisierung
    raw_text = normalize_for_tts(raw_text)

    # 2) Rohtext speichern
    txt_path = os.path.join(TXT_DIR, pdf_filename.replace(".pdf", ".txt"))
    _save(txt_path, raw_text)
    print(f"[OK] Rohtext gespeichert: {txt_path}")

    # 3) je nach MODE weiterverarbeiten
    if MODE == "tts_passthrough":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_tts_ready.txt"))
        _save(out_path, raw_text)
        print(f"[OK] TTS-Text gespeichert: {out_path}")
        return

    if MODE == "clean_for_tts":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_clean.txt"))
        if len(raw_text) <= SINGLECALL_LIMIT:
            messages = [
                {"role": "system", "content": PROMPT_CLEAN_SYSTEM},
                {"role": "user", "content": (
                    "Bereinige NUR diesen Text für TTS, ohne ihn zu kürzen oder umzuschreiben:\n\n---\n"
                    + raw_text + "\n---"
                )},
            ]
            try:
                ans = query_llm(API_URL, MODEL_NAME, messages,
                                temperature=0.0, top_p=0.1, max_tokens=MAX_TOKENS_CLEAN)
            except Exception as e:
                ans = f"[Fehler beim Bereinigen: {e}]"
            final_text = ans.strip()
        else:
            chunks = chunk_text(raw_text, max_chars=CHUNK_SIZE)
            results = []
            for idx, ch in enumerate(chunks, start=1):
                print(f"[INFO] LLM-Bereinigung Chunk {idx}/{len(chunks)} …")
                messages = [
                    {"role": "system", "content": PROMPT_CLEAN_SYSTEM},
                    {"role": "user", "content": (
                        "Bereinige NUR diesen Text für TTS, ohne ihn zu kürzen oder umzuschreiben:\n\n---\n"
                        + ch + "\n---"
                    )},
                ]
                try:
                    ans = query_llm(API_URL, MODEL_NAME, messages,
                                    temperature=0.0, top_p=0.1, max_tokens=MAX_TOKENS_CLEAN)
                except Exception as e:
                    ans = f"[Fehler bei Teil {idx}: {e}]"
                results.append(ans)
            final_text = "\n\n".join(results).strip()
        _save(out_path, final_text or "Keine Ausgabe erhalten.")
        print(f"[OK] Bereinigter TTS-Text gespeichert: {out_path}")
        return

    if MODE == "summary":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_summary.txt"))
        if len(raw_text) <= SINGLECALL_LIMIT:
            messages = [
                {"role": "system", "content": PROMPT_SUMMARY_SYSTEM},
                {"role": "user", "content": f"Fasse den folgenden Text präzise zusammen:\n\n{raw_text}"},
            ]
            try:
                ans = query_llm(API_URL, MODEL_NAME, messages,
                                temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS_SUMMARY)
            except Exception as e:
                ans = f"[Fehler bei Zusammenfassung: {e}]"
            final_text = ans.strip()
        else:
            chunks = chunk_text(raw_text, max_chars=CHUNK_SIZE)
            results = []
            for idx, ch in enumerate(chunks, start=1):
                print(f"[INFO] LLM-Zusammenfassung Chunk {idx}/{len(chunks)} …")
                messages = [
                    {"role": "system", "content": PROMPT_SUMMARY_SYSTEM},
                    {"role": "user", "content": f"Fasse diesen Abschnitt zusammen (Teil {idx}/{len(chunks)}):\n\n{ch}"},
                ]
                try:
                    ans = query_llm(API_URL, MODEL_NAME, messages,
                                    temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS_SUMMARY)
                except Exception as e:
                    ans = f"[Fehler bei Teil {idx}: {e}]"
                results.append(ans)
            final_text = "\n\n".join(results).strip()
        _save(out_path, final_text or "Keine Zusammenfassung erhalten.")
        print(f"[OK] Zusammenfassung gespeichert: {out_path}")
        return

    print(f"[WARN] Unbekannter MODE: {MODE}")


def main():
    ensure_dirs()
    files = [fn for fn in os.listdir(INPUT_DIR) if fn.lower().endswith('.pdf')]
    if not files:
        print(f"[HINWEIS] Keine PDFs in {INPUT_DIR} gefunden.")
    for filename in files:
        try:
            process_file(filename)
        except Exception as e:
            print(f"[FEHLER] {filename}: {e}")


if __name__ == "__main__":
    main()
