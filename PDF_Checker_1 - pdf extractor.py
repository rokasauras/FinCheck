import pdfplumber

def load_and_extract_text(pdf_path: str) -> str: # Function to extract text from PDF
    """
    Opens a PDF file with pdfplumber, extracts text from all pages,
    and concatenates it into a single string.
    """
    all_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Iterate through each page in the PDF
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract the text from the page
                page_text = page.extract_text()
                if page_text:
                    all_text.append(f"--- Page {page_num} ---\n{page_text}")
                else:
                    all_text.append(f"--- Page {page_num}: No text found ---")
    except Exception as e:
        print(f"[ERROR] Could not open or read the PDF. Reason: {e}")
        return ""

    # Combine all the extracted text into a single string
    return "\n".join(all_text)


if __name__ == "__main__":
    # Path to the sample PDF file
    path_to_pdf = "sample_bank_statement.pdf" 

    # Load and extract text from the PDF
    extracted_text = load_and_extract_text(path_to_pdf)

    if extracted_text:
        print("Extracted Text (Preview):")
        # Display the first 5000 characters of the extracted text
        print(extracted_text[:5000], "...\n")
    else:
        print("No text extracted or unable to open the file.")
