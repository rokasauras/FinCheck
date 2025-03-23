import os
import json
import difflib
import re
from collections import Counter

def preprocess_text(text):
    """
    Normalise text by lowercasing, stripping, and collapsing whitespace.
    """
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def preprocess_text(text):
    """
    Lowercase text, remove punctuation, and extra whitespace.
    This ensures fair word-based comparison.
    """
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)     # Collapse whitespace
    return text.strip()

class StatementVerifier:
    """
    This class verifies the extracted data from OpenAI Vision and local PDF text extraction.
    It compares the outputs and flags inconsistencies.
    """

    def __init__(self, ai_output, pdf_handler):
        """
        Initialise the StatementVerifier with AI-generated and locally extracted text data.

        :param ai_output: JSON output from OpenAI Vision (image analysis) as a string or dict.
        :param pdf_handler: An instance of PDFHandler with extracted text data, or None.
        """
        # If ai_output is a string, try to load it as JSON; otherwise, assume it's already a dict.
        self.ai_data = self.load_json(ai_output) if isinstance(ai_output, str) else ai_output
        self.pdf_handler = pdf_handler

        # Ensure AI output is always a dictionary
        if not isinstance(self.ai_data, dict):
            print("Warning: AI data is not a dictionary. Setting it to empty.")
            self.ai_data = {}

        # Standardise AI pages
        ai_pages = self.ai_data.get("pages", [])
        if not isinstance(ai_pages, list):
            ai_pages = []  # Ensure it is always a list
        
        self.pages_ai = {"pages": ai_pages}  # Now always a dictionary with "pages"

        # Handle PDF pages
        if self.pdf_handler is not None and hasattr(self.pdf_handler, "text_pages"):
            if isinstance(self.pdf_handler.text_pages, list):
                self.pages_pdf = {"pages": self.pdf_handler.text_pages}
            elif isinstance(self.pdf_handler.text_pages, dict) and "pages" in self.pdf_handler.text_pages:
                self.pages_pdf = self.pdf_handler.text_pages
            else:
                self.pages_pdf = {"pages": []}
        else:
            self.pages_pdf = {"pages": []}

        # Print debugging message
        print(f"StatementVerifier initialised with {len(self.pages_ai['pages'])} AI pages "
            f"and {len(self.pages_pdf['pages'])} PDF pages.")

    def load_json(self, input_str):
        """
        Attempts to load JSON data.
        If input_str is a valid file path, loads JSON from the file.
        Otherwise, attempts to parse input_str as JSON.
        """
        if os.path.exists(input_str):
            try:
                with open(input_str, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON from file {input_str}: {e}")
                return {}
        else:
            try:
                return json.loads(input_str)
            except Exception as e:
                print(f"Error parsing JSON string: {e}")
                return {}

    def compare_text(self, similarity_threshold=0.90): # Compare text from AI vs PDF
        """
        Compares the 'page_text' from AI vs. PDF output based on WORD similarity.
        If similarity is below threshold, a unified diff is printed (word-by-word).
        """
        print("\n=== Comparing AI Vision Output with PDF Extracted Text ===\n")

        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        for page_num in range(1, total_pages + 1):
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "unknown")
            pdf_text = pdf_page.get("page_text", "unknown")

            # Preprocess and split texts into words for comparison
            ai_text_clean = preprocess_text(ai_text).split()
            pdf_text_clean = preprocess_text(pdf_text).split()

            matcher = difflib.SequenceMatcher(None, ai_text_clean, pdf_text_clean)
            similarity = matcher.ratio()

            print(f"\n--- Page {page_num} ---")
            print(f"Word-based Similarity Ratio: {similarity:.2f}")

            if similarity < similarity_threshold:
                print("Differences detected. Unified Diff (word-based):")
                diff = difflib.unified_diff(
                    pdf_text_clean,
                    ai_text_clean,
                    fromfile="PDF Extracted Text",
                    tofile="AI Vision Text",
                    lineterm=""
                )
                for line in diff:
                    print(line)
            else:
                print("Text similarity is acceptable.")


    @staticmethod # Static method to extract numbers from text
    def extract_numbers(text):
        """
        Extract all numeric tokens (e.g., 100, 100.00, +200, -50) in order of appearance,
        returning only the numeric part without any leading '+' or '-'.
        """
        pattern = r'[+-]?\d+(?:\.\d+)?'
        matches = re.findall(pattern, text)
        return [match.lstrip('+-') for match in matches]
    
    def compare_numbers(self):
        """
        Compare numeric values from AI output vs. PDF output for each page, 
        ignoring the order of the numbers. They must match in count and value,
        but can appear in different sequences.
        """
        print("\n=== Comparing Numeric Values Between AI and PDF ===\n")
        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        for page_num in range(1, total_pages + 1):
            # Find the page dictionaries
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "")
            pdf_text = pdf_page.get("page_text", "")

            # Extract numbers
            ai_numbers = self.extract_numbers(ai_text)
            pdf_numbers = self.extract_numbers(pdf_text)

            print(f"--- Page {page_num} ---")
            print(f"AI Numbers: {ai_numbers}")
            print(f"PDF Numbers: {pdf_numbers}")

            # Quick length check
            if len(ai_numbers) != len(pdf_numbers):
                print("Number of numeric tokens does NOT match!\n")
                continue

            # Compare ignoring order using Counter
            if Counter(ai_numbers) == Counter(pdf_numbers):
                print("All numeric values match!")
            else:
                print("Mismatched numeric values!")
                print("Sorted AI:  ", sorted(ai_numbers))
                print("Sorted PDF: ", sorted(pdf_numbers))

            print()  # Blank line for clarity

    


    

    

