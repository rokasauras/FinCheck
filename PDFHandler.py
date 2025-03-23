import pdf2image
from PyPDF2 import PdfReader
from pathlib import Path


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

    # Add methods to extract metadata, text, and convert to images
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

    # Add a method to extract text from the PDF
    def extract_text(self):
        """Extract text from PDF pages (if they are text-based, not images)."""
        try:
            reader = PdfReader(self.pdf_path)
            all_text = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                all_text.append(page_text)
            self.text = "\n".join(all_text)

            # Print the first 1000 characters (or less if the document is shorter)
            print("\n--- Extracted Text Preview (First 1000 characters) ---\n")
            print(self.text[:1000])  # Slice the first 1000 characters
            print("\n--- Extracted Text Preview End ---\n")
        except Exception as e:
            print(f"Error extracting text: {e}")
            self.text = ""

    # Add a method to convert the PDF to images
    def convert_to_images(self, max_pages=20):
        """Convert the PDF to images (for OCR or AI-based image analysis)."""
        try:
            # If poppler_path is needed (Windows users), pass it explicitly
            self.images = pdf2image.convert_from_path(
                self.pdf_path, 
                poppler_path=self.poppler_path
            )
            # Limit pages if needed
            if len(self.images) > max_pages:
                self.images = self.images[:max_pages]
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            self.images = []
