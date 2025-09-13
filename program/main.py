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
    if MODE == "clean_fast":
        out_path = os.path.join(OUTPUT_DIR, pdf_filename.replace(".pdf", "_fastclean.txt"))
        # reines Regex-Normalisieren (keine LLM-Abfrage)
        final_text = normalize_for_tts(raw_text)
        _save(out_path, final_text or "Keine Ausgabe erhalten.")
        print(f"[OK] Schnell bereinigter TTS-Text gespeichert: {out_path}")
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
