import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv

from OpenAIHelper import OpenAIHelper
from PDFHandler import PDFHandler
from BankStatementAnalyser import BankStatementAnalyser

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
    pdf_handler = PDFHandler(pdf_path=pdf_path, poppler_path=None)  # Set poppler_path if needed on Windows
    pdf_handler.extract_metadata()
    pdf_handler.extract_text()
    pdf_handler.convert_to_images(max_pages=20)

    print("PDF Metadata:") # Print metadata
    for k, v in pdf_handler.metadata.items():
        print(f"{k}: {v}")

    print(f"\nExtracted text length: {len(pdf_handler.text)} characters.")
    print(f"Found {len(pdf_handler.images)} page images.") # Print number of images

    #  Analyse if it’s a Bank Statement
    analyser = BankStatementAnalyser(pdf_handler.text)
    if analyser.is_bank_statement():
        print("\nThis document appears to be a bank statement.")
        analyser.extract_business_details()
        analyser.extract_balances_and_transactions()
        is_reconciled = analyser.reconcile_statement()

        print("\n--- Statement Details ---")
        print(f"Business Name: {analyser.business_name or 'Not found'}")
        print(f"Business Address:\n{analyser.business_address or 'Not found'}")

        print(f"Opening Balance: {analyser.opening_balance or 'Not found'}")
        print(f"Closing Balance: {analyser.closing_balance or 'Not found'}")
        print(f"Number of Transactions: {len(analyser.transactions)}")

        if is_reconciled:
            print("Balances reconcile successfully.")
        else:
            print("Balances do NOT reconcile.")
    else:
        print("\nThis PDF doesn't appear to be a bank statement (based on simple keyword checks).")

    # Use OpenAI to analyse the bank statement
    USE_OPENAI = True  # Set to False to disable OpenAI analysis during testing of other functions


    if openai_key and USE_OPENAI:
        try: # Analyse the bank statement with OpenAI
            ai_helper = OpenAIHelper(model="gpt-4o")
            gpt_response = ai_helper.analyse_bank_statements(pdf_handler.images)

            if gpt_response:
                print("\n--- OpenAI Image Analysis ---")
                print(gpt_response)  # Print the raw JSON (or string) returned by OpenAI
            else:
                print("No response from OpenAI.")
        except Exception as e:
            print(f"OpenAI Analysis Error: {e}")

if __name__ == "__main__": # Run the main function
    main()
