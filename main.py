import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv

from OpenAIHelper import OpenAIHelper
from PDFHandler import PDFHandler
from StatementVerifier import StatementVerifier

def main():
    # Load OpenAI API key from .env file
    env_path = r"C:\Users\rokas\Documents\FinCheck\OpenAI.env"
    load_dotenv(env_path)

    # Load OpenAI API key from environment
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("Warning: OPENAI_API_KEY is not set. AI analysis won't work.\n")
    else:
        print("API key loaded successfully from .env.\n")

    # Ask user to select a PDF file
    root = tk.Tk()
    root.withdraw()
    pdf_file = filedialog.askopenfilename(
        title="Select a PDF File",
        filetypes=[("PDF Files", "*.pdf")]
    )
    #  Exit if no file selected
    if not pdf_file:
        print("No file selected. Exiting.")
        sys.exit(1)
    # Check if the file exists
    pdf_path = Path(pdf_file)
    if not pdf_path.exists():
        print(f"Error: File '{pdf_path}' does not exist.")
        sys.exit(1)

    # Process the PDF file
    pdf_handler = PDFHandler(pdf_path=pdf_path, poppler_path=None)  
    pdf_handler.extract_metadata()
    pdf_handler.extract_text()
    pdf_handler.convert_to_images(max_pages=20)

    print("PDF Metadata:")
    for k, v in pdf_handler.metadata.items():
        print(f"{k}: {v}")

    print(f"\nExtracted text length: {len(pdf_handler.text)} characters.")
    print(f"Found {len(pdf_handler.images)} page images.")

    # Use OpenAI to analyse the bank statement
    USE_OPENAI = True  # Set to False if you don't want to use OpenAI
    
    # Define gpt_response upfront so it's in scope even if AI call is skipped/fails
    gpt_response = None

    if openai_key and USE_OPENAI:
        try:
            ai_helper = OpenAIHelper(model="gpt-4o")
            gpt_response = ai_helper.analyse_bank_statements(pdf_handler.images)

            if gpt_response:
                print("\n--- OpenAI Image Analysis ---")
                print(gpt_response)  # Print the raw JSON (or string) returned by OpenAI
            else:
                print("No response from OpenAI.")
        except Exception as e:
            print(f"OpenAI Analysis Error: {e}")

    # Compare AI output with PDF text data
    if gpt_response:
        verifier = StatementVerifier(ai_output=gpt_response, pdf_handler=pdf_handler)
        verifier.compare_text()       # Compare textual similarity, e.g. difflib
        verifier.compare_numbers()    # Compare numeric values with no tolerance
    else:
        print("No valid AI response available for comparison.")

if __name__ == "__main__":
    main()
