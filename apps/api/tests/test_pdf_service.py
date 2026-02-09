"""Tests for PDF text extraction service.

Tests use dynamically generated PDFs via reportlab fixtures.
No external dependencies beyond pypdf (which is a project dependency).
"""

import pytest

from app.services.pdf_service import extract_text_from_pdf


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf()."""

    def test_extracts_text_from_valid_pdf(self, sample_pdf_bytes: bytes) -> None:
        """Text is extracted from a valid PDF."""
        text = extract_text_from_pdf(sample_pdf_bytes)

        # Verify content from both pages is present
        assert "Page 1" in text
        assert "test content" in text
        assert "first page" in text
        assert "Page 2" in text
        assert "second page" in text

    def test_extracts_multi_page_content(self, sample_pdf_bytes: bytes) -> None:
        """Content from multiple pages is joined."""
        text = extract_text_from_pdf(sample_pdf_bytes)

        # Both pages should be present
        assert "Page 1" in text
        assert "Page 2" in text

        # Pages should be separated (content from page 2 comes after page 1)
        page1_pos = text.find("Page 1")
        page2_pos = text.find("Page 2")
        assert page1_pos < page2_pos

    def test_raises_on_empty_pdf(self, empty_pdf_bytes: bytes) -> None:
        """ValueError is raised for PDFs with no extractable text."""
        with pytest.raises(ValueError, match="no extractable text"):
            extract_text_from_pdf(empty_pdf_bytes)

    def test_raises_on_invalid_bytes(self) -> None:
        """Exception is raised for random bytes that are not a PDF."""
        invalid_bytes = b"This is not a PDF file at all, just random text."

        with pytest.raises(Exception):  # pypdf raises various exceptions
            extract_text_from_pdf(invalid_bytes)

    def test_raises_on_corrupted_pdf(self, corrupted_pdf_bytes: bytes) -> None:
        """Exception is raised for truncated/corrupted PDF files."""
        with pytest.raises(Exception):  # pypdf raises PdfReadError or similar
            extract_text_from_pdf(corrupted_pdf_bytes)

    def test_handles_pdf_with_special_characters(self) -> None:
        """PDFs with unicode and special characters are handled correctly."""
        import io

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        # Note: reportlab may not render all unicode, but basic chars work
        c.drawString(100, 750, "Price: $99.99 - 50% off!")
        c.drawString(100, 730, "Contact: support@example.com")
        c.showPage()
        c.save()

        text = extract_text_from_pdf(buffer.getvalue())

        assert "$99.99" in text
        assert "50%" in text
        assert "support@example.com" in text

    def test_preserves_paragraph_structure(self) -> None:
        """Multiple pages are separated by double newlines."""
        import io

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        c.drawString(100, 750, "Content on page one.")
        c.showPage()

        c.drawString(100, 750, "Content on page two.")
        c.showPage()

        c.drawString(100, 750, "Content on page three.")
        c.showPage()

        c.save()

        text = extract_text_from_pdf(buffer.getvalue())

        # Pages should be separated
        assert "page one" in text
        assert "page two" in text
        assert "page three" in text

        # Should have paragraph separators (double newline) between pages
        assert "\n\n" in text
