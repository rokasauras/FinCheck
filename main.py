import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv
from io import StringIO
from contextlib import redirect_stdout

from OpenAIHelper import OpenAIHelper
from PDFHandler import PDFHandler
from StatementVerifier import StatementVerifier

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            try:
                stream.write(message)
            except ValueError:
                # The file might be closed already, so ignore
                pass
    def flush(self):
        for stream in self.streams:
            try:
                stream.flush()
            except ValueError:
                # The file might be closed, so ignore the flush
                pass



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
                print("OpenAI returned an empty or null response.")

        except Exception as e:
            print(f"OpenAI Analysis Error: {e}")
    else:
        print("Skipping OpenAI Vision analysis (API key missing or USE_OPENAI=False).")

    # Run the StatementVerifier
    if gpt_response:
        try:
            verifier = StatementVerifier(ai_output=gpt_response, pdf_handler=pdf_handler)

            # Compare AI and PDF text
            verifier.compare_text()

            # Compare numeric values with no tolerance
            verifier.compare_numbers()

            # Check opening/closing balance consistency
            verifier.verify_opening_closing_balance_consistency()

        except Exception as e:
            print(f"Error running StatementVerifier: {e}")
    else:
        print("No valid AI output available for statement verification.")

if __name__ == "__main__":
    log_path = Path("output_logs/log.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Open log file in a context manager
    with open(log_path, "w", encoding="utf-8") as log_file:
        # Tee writes to both the real stdout (sys.__stdout__) and log_file
        sys.stdout = Tee(sys.__stdout__, log_file)

        try:
            # Run main code
            main()
        finally:
            # Restore original stdout
            sys.stdout = sys.__stdout__

    print(f"Logs have been written to {log_path}")
    os.system("python SQLPreper.py")
    os.system("python MachineLearning.py")



