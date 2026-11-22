import re
from io import BytesIO

from pypdf import PdfReader


def split_page_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """Split one page into overlapping chunks without losing its page identity."""
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            boundary = clean.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_pdf_chunks(pdf_bytes: bytes, max_chars: int = 1000, overlap: int = 150) -> tuple[int, list[tuple[int, int, str]]]:
    """Return page-aware chunks. Reject malformed, encrypted, or text-empty PDFs."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF")
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported")
        chunks: list[tuple[int, int, str]] = []
        chunk_index = 0
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            for chunk in split_page_text(page_text, max_chars=max_chars, overlap=overlap):
                chunks.append((page_number, chunk_index, chunk))
                chunk_index += 1
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not read this PDF. Try another file.") from exc

    if not chunks:
        raise ValueError("This PDF has no extractable text. Scanned PDFs need OCR, which is not enabled yet.")
    return len(reader.pages), chunks
