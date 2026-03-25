# app/services/pdf_extractor.py
"""
PDF and plain-text content extractor for admin policy uploads.
Falls back gracefully if neither PyPDF2 nor pdfplumber is installed.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF or plain-text files with automatic fallback."""

    @staticmethod
    async def extract_text(file_path: str) -> str:
        """
        Try PyPDF2, then pdfplumber, then plain-text fallback.
        Returns extracted string (may be empty if all methods fail).
        """
        path = Path(file_path)

        if path.suffix.lower() in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        # --- PyPDF2 ---
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            if text.strip():
                logger.debug("PDF extracted via PyPDF2")
                return text
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")

        # --- pdfplumber ---
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
            if text.strip():
                logger.debug("PDF extracted via pdfplumber")
                return text
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

        logger.error("No PDF extraction library available – install PyPDF2 or pdfplumber")
        return ""
