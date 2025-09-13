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

