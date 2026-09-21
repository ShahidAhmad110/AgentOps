from io import BytesIO
from pathlib import Path
import re

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


def validate_filename(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, TXT, and Markdown documents are supported.")
    return extension


def extract_text(filename: str, content_type: str, content: bytes) -> tuple[str, dict[str, str]]:
    extension = validate_filename(filename)
    if not content:
        raise ValueError("The uploaded document is empty.")

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        metadata = {"format": "pdf", "page_count": str(len(reader.pages))}
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must use UTF-8 encoding.") from exc
        metadata = {"format": "markdown" if extension in {".md", ".markdown"} else "text"}

    normalized = normalize_text(text)
    if not normalized:
        raise ValueError("The document does not contain extractable text.")
    return normalized, {"content_type": content_type, **metadata}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
