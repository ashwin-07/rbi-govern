import fitz
import pdfplumber

from src.logger import get_logger

log = get_logger("rbi_govern.extractor")

_GARBLED_SIZE = 5_000       # chars
_GARBLED_NON_ASCII = 0.30   # 30% non-ASCII signals mojibake or scanned


def _is_garbled(text: str) -> bool:
    if len(text) < _GARBLED_SIZE:
        return True
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return (non_ascii / len(text)) > _GARBLED_NON_ASCII


def _pymupdf(path: str) -> str:
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _pdfplumber(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_text(path: str) -> str:
    text = _pymupdf(path)
    if not _is_garbled(text):
        log.debug("%s — pymupdf ok (%d chars)", path, len(text))
        return text

    log.warning("%s — pymupdf garbled, trying pdfplumber", path)
    text = _pdfplumber(path)
    if not _is_garbled(text):
        log.debug("%s — pdfplumber ok (%d chars)", path, len(text))
        return text

    log.error("%s — both extractors failed (%d chars), needs OCR", path, len(text))
    return text


def extract_tables(path: str) -> list[list]:
    with pdfplumber.open(path) as pdf:
        tables = []
        for page in pdf.pages:
            tables.extend(page.extract_tables() or [])
    return tables
