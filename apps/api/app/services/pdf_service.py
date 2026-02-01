"""PDF text extraction service."""

import io
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file.

    Args:
        file_bytes: Raw PDF file bytes.

    Returns:
        Extracted text from all pages.

    Raises:
        ValueError: If the PDF has no extractable text.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    content = "\n\n".join(pages)
    if not content.strip():
        raise ValueError("PDF contains no extractable text.")

    return content
