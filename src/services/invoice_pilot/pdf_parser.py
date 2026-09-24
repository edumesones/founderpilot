"""
PDF parsing utility for InvoicePilot.

Handles:
- Extracting text from PDF invoices
- Converting PDF pages to images for multimodal LLM processing
- Handling corrupted or unreadable PDFs
"""

import base64
import io
from typing import List, Optional, Dict, Any

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PDFParseError(Exception):
    """Raised when PDF parsing fails."""
    pass


class PDFParser:
    """
    PDF parser for invoice documents.

    Provides methods to:
    - Extract text from PDF
    - Convert PDF to images for OCR/multimodal processing
    - Handle various PDF formats and errors
    """

    def __init__(
        self,
        max_pages: int = 5,
        image_dpi: int = 200,
        max_image_width: int = 1600,
    ):
        """
        Initialize PDF parser.

        Args:
            max_pages: Maximum number of pages to process
            image_dpi: DPI for PDF to image conversion
            max_image_width: Maximum width for output images (for optimization)
        """
        self.max_pages = max_pages
        self.image_dpi = image_dpi
        self.max_image_width = max_image_width

    def extract_text(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Extracted text as string

        Raises:
            PDFParseError: If text extraction fails
        """
        if not PYPDF2_AVAILABLE:
            raise PDFParseError("PyPDF2 not installed. Run: pip install PyPDF2")

        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            num_pages = min(len(pdf_reader.pages), self.max_pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                if text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            if not text_parts:
                raise PDFParseError("No text could be extracted from PDF")

            return "\n\n".join(text_parts)

        except PyPDF2.errors.PdfReadError as e:
            raise PDFParseError(f"Failed to read PDF: {str(e)}")
        except Exception as e:
            raise PDFParseError(f"Unexpected error parsing PDF: {str(e)}")

    def pdf_to_images(
        self,
        pdf_bytes: bytes,
        first_page_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Convert PDF pages to images.

        Args:
            pdf_bytes: PDF file content as bytes
            first_page_only: Only convert first page (recommended for invoices)

        Returns:
            List of dicts with 'page_number', 'base64' (base64-encoded PNG), and 'size'

        Raises:
            PDFParseError: If conversion fails
        """
        if not PDF2IMAGE_AVAILABLE:
            raise PDFParseError("pdf2image not installed. Run: pip install pdf2image")

        if not PIL_AVAILABLE:
            raise PDFParseError("Pillow not installed. Run: pip install Pillow")

        try:
            # Convert PDF to images
            if first_page_only:
                images = convert_from_bytes(
                    pdf_bytes,
                    dpi=self.image_dpi,
                    first_page=1,
                    last_page=1,
                )
            else:
                last_page = min(self.max_pages, 999)  # pdf2image doesn't like None
                images = convert_from_bytes(
                    pdf_bytes,
                    dpi=self.image_dpi,
                    last_page=last_page,
                )

            result = []
            for idx, image in enumerate(images):
                # Resize if needed (to reduce token usage)
                if image.width > self.max_image_width:
                    ratio = self.max_image_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((self.max_image_width, new_height), Image.Resampling.LANCZOS)

                # Convert to PNG and base64
                img_buffer = io.BytesIO()
                image.save(img_buffer, format="PNG")
                img_bytes = img_buffer.getvalue()

                base64_image = base64.b64encode(img_bytes).decode("utf-8")

                result.append({
                    "page_number": idx + 1,
                    "base64": base64_image,
                    "size": len(img_bytes),
                    "width": image.width,
                    "height": image.height,
                })

            return result

        except Exception as e:
            raise PDFParseError(f"Failed to convert PDF to images: {str(e)}")

    def get_pdf_info(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Get basic PDF metadata.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Dictionary with metadata (pages, size, encrypted, etc.)
        """
        if not PYPDF2_AVAILABLE:
            return {
                "valid": False,
                "error": "PyPDF2 not installed",
            }

        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            return {
                "valid": True,
                "pages": len(pdf_reader.pages),
                "encrypted": pdf_reader.is_encrypted,
                "size_bytes": len(pdf_bytes),
                "metadata": dict(pdf_reader.metadata) if pdf_reader.metadata else {},
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

    def extract_structured_data(
        self,
        pdf_bytes: bytes,
        prefer_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract both text and images from PDF for LLM processing.

        Args:
            pdf_bytes: PDF file content as bytes
            prefer_images: If True, prioritize image extraction over text

        Returns:
            Dictionary with 'text', 'images', and 'metadata'
        """
        result = {
            "text": None,
            "images": [],
            "metadata": self.get_pdf_info(pdf_bytes),
            "extraction_method": None,
            "error": None,
        }

        # Try text extraction first (unless images preferred)
        if not prefer_images:
            try:
                result["text"] = self.extract_text(pdf_bytes)
                result["extraction_method"] = "text"
            except PDFParseError as e:
                result["error"] = str(e)

        # If text extraction failed or images preferred, try image extraction
        if not result["text"] or prefer_images:
            try:
                result["images"] = self.pdf_to_images(pdf_bytes, first_page_only=True)
                result["extraction_method"] = "images" if not result["text"] else "hybrid"
            except PDFParseError as e:
                if not result["text"]:
                    result["error"] = str(e)

        return result

    def is_valid_invoice_pdf(self, pdf_bytes: bytes) -> bool:
        """
        Quick check if PDF is valid and processable.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            True if PDF appears valid
        """
        info = self.get_pdf_info(pdf_bytes)

        if not info.get("valid"):
            return False

        # Reject encrypted PDFs
        if info.get("encrypted"):
            return False

        # Reject very large PDFs (> 10MB)
        if info.get("size_bytes", 0) > 10 * 1024 * 1024:
            return False

        # Reject PDFs with too many pages (likely not an invoice)
        if info.get("pages", 0) > 10:
            return False

        return True


# Singleton instance
_pdf_parser_instance: Optional[PDFParser] = None


def get_pdf_parser() -> PDFParser:
    """Get or create PDF parser singleton."""
    global _pdf_parser_instance
    if _pdf_parser_instance is None:
        _pdf_parser_instance = PDFParser()
    return _pdf_parser_instance
