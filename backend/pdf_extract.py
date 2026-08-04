"""Extração de texto do PDF. Isolado num módulo próprio para poder trocar
a biblioteca (ex: por um serviço de OCR) sem tocar no parser."""
import fitz  # PyMuPDF


def extract_pages(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [page.get_text() for page in doc]


def extract_pages_from_path(path: str) -> list[str]:
    with open(path, "rb") as f:
        return extract_pages(f.read())
