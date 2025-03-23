import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import os

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Users\rokas\Documents\Release-24.08.0-0\poppler-24.08.0\Library\bin"

BANK_STATEMENT_KEYWORDS = [
    "account number", "statement date", "transaction", "balance",
    "deposits", "withdrawals", "closing balance", "opening balance",
    "available balance", "interest", "statement period"
]

# Function to extract text using pdfplumber
def load_and_extract_text(pdf_path: str) -> str:
    all_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Iterate through each page in the PDF
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract the text from the page
                text = page.extract_text() 
                if text: # If text is extracted
                    all_text.append(text)  # Append to list
        return "\n".join(all_text)
    except Exception as e:
        print(f"[pdfplumber ERROR]: {e}")
        return ""

# Function to extract text using OCR
def extract_text_ocr(pdf_path: str) -> str:
    all_text = []
    try:
        images = convert_from_path(pdf_path, poppler_path=r"C:\Users\rokas\Documents\Release-24.08.0-0\poppler-24.08.0\Library\bin") # Convert PDF to images
        for i, img in enumerate(images, start=1):
            print(f"Running OCR on page {i}...")
            text = pytesseract.image_to_string(img)
            all_text.append(text)
    except Exception as e:
        print(f"[OCR ERROR]: {e}")
        return ""
    return "\n".join(all_text)

# Function to classify document type
def classify_document(text: str) -> str:
    text_lower = text.lower()
    keyword_count = sum(1 for keyword in BANK_STATEMENT_KEYWORDS if keyword in text_lower) # Count keyword matches
    return "Bank Statement" if keyword_count >= 3 else "Other Document" # Classify based on keyword count

# Main function
if __name__ == "__main__":
    pdf_path = "sample_bank_statement_png.pdf" # Path to PDF file

    if not os.path.exists(pdf_path):
        print(f"[FILE ERROR]: {pdf_path} not found.")
        exit()

    # Try PDFPlumber extraction first
    extracted_text = load_and_extract_text(pdf_path)

    if extracted_text.strip(): 
        print("[INFO] Text extracted using pdfplumber.")
    else:
        print("[INFO] No text found via pdfplumber. Trying OCR...")
        extracted_text = extract_text_ocr(pdf_path)
        if extracted_text.strip():
            print("[INFO] Text extracted using OCR.")
        else:
            print("[ERROR] OCR failed to extract text. Exiting.")
            exit()

    # Preview text (first 500 characters)
    print("\n--- Extracted Text Preview ---")
    print(extracted_text[:500]) #   Print first 500 characters
    print("--- End Preview ---\n")

    # Classify document
    doc_type = classify_document(extracted_text)
    print(f"Document classified as: {doc_type}")


