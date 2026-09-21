from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str


def chunk_text(text: str, max_characters: int = 1200, overlap: int = 150) -> list[TextChunk]:
    if max_characters <= 0 or overlap < 0 or overlap >= max_characters:
        raise ValueError("Chunk size and overlap must define a positive forward window.")

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + max_characters, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary > start + max_characters // 2:
                end = boundary
        content = text[start:end].strip()
        if content:
            chunks.append(TextChunk(index=index, content=content))
            index += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
