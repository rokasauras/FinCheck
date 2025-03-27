import pdf2image
from PyPDF2 import PdfReader
from pathlib import Path
import json


class PDFHandler:
    """
    Responsible for reading a PDF, extracting text, metadata,
    and optionally converting pages to images.
    """

    # Add a constructor to initialise the PDFHandler

    def __init__(self, pdf_path, poppler_path=None):
        self.pdf_path = Path(pdf_path)
        self.poppler_path = poppler_path
        self.metadata = {}
        self.text = ""
        self.images = []

    def extract_metadata(self):
        """Extract basic metadata from PDF."""
        try:
            reader = PdfReader(self.pdf_path)
            pdf_metadata = reader.metadata or {}
            self.metadata = {
                "Pages": len(reader.pages),
                "Title": pdf_metadata.get("/Title", "Not available"),
                "Author": pdf_metadata.get("/Author", "Not available"),
                "Creator": pdf_metadata.get("/Creator", "Not available"),
                "Producer": pdf_metadata.get("/Producer", "Not available"),
                "Creation Date": pdf_metadata.get("/CreationDate", "Not available"),
                "Modification Date": pdf_metadata.get("/ModDate", "Not available")
            }
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            self.metadata = {}

    # Add methods to extract metadata, text, and convert to images
    def extract_text(self):
        """Extract text from PDF pages (if they are text-based, not images)."""
        try:
            reader = PdfReader(self.pdf_path)
            pages_list = []

            for i, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                # Append a dict similar to the AI's JSON structure
                pages_list.append({
                    "page_number": i,
                    "page_text": page_text
                })

            self.text = "\n".join([p["page_text"] for p in pages_list])
            self.text_pages = pages_list  # Keep the JSON-like list

            # Print a JSON preview of the extracted text
            preview_pages = []
            for p in pages_list:
                preview_text = p["page_text"][:1000]
                preview_pages.append({
                    "page_number": p["page_number"],
                    "page_text": preview_text
                })

            preview_json = {"pages": preview_pages}
            print("\n--- Extracted Text as JSON Preview (First 1000 chars per page) ---")
            print(json.dumps(preview_json, indent=2))
            print("--- End of Extracted Text Preview ---\n")

        except Exception as e:
            print(f"Error extracting text: {e}")
            self.text = ""
            self.text_pages = []

    def convert_to_images(self, max_pages=20):
        """Convert the PDF to images (AI-based image analysis)."""
        try:
            self.images = pdf2image.convert_from_path(
                self.pdf_path, 
                poppler_path=self.poppler_path
            )
            # Limit the number of pages to avoid memory issues
            if len(self.images) > max_pages:
                self.images = self.images[:max_pages]
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            self.images = []
