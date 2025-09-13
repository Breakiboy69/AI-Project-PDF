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
    # ... bestehende Sanitizer ...
    s = re.sub(r"^\s*[-]{3,}\s*$", "", s, flags=re.MULTILINE)  # Zeilen nur aus --- raus
    s = re.sub(r"\n{3,}", "\n\n", s)  # Leerzeilen nochmal glätten
    return s.strip()

