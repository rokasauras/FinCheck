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

    
    def compare_text(self, similarity_threshold=0.89):
        """
        Compares AI vs PDF text and returns a list of similarity results per page.
        """
        results = []
        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        for page_num in range(1, total_pages + 1):
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "")
            pdf_text = pdf_page.get("page_text", "")

            ai_text_clean = preprocess_text(ai_text).split()
            pdf_text_clean = preprocess_text(pdf_text).split()

            matcher = difflib.SequenceMatcher(None, ai_text_clean, pdf_text_clean)
            similarity = matcher.ratio()

            result = {
                "page": page_num,
                "similarity": round(similarity * 100, 2),
                "pass": similarity >= similarity_threshold
            }

            results.append(result)

        return results


    @staticmethod # Static method to extract numbers from text
    def extract_numbers(text):
        """
        Extract all numeric tokens (e.g., 100, 100.00, +200, -50) in order of appearance,
        returning only the numeric part without any leading '+' or '-'.
        """
        pattern = r'[+-]?\d+(?:\.\d+)?'
        matches = re.findall(pattern, text)
        return [match.lstrip('+-') for match in matches]

    def compare_text(self, similarity_threshold=0.89):
        """
        Compares AI vs PDF text and returns a list of similarity results per page.
        Also prints the results for logging or real-time feedback.
        """
        results = []
        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        print("\n=== Text Comparison Results ===")

        for page_num in range(1, total_pages + 1):
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "")
            pdf_text = pdf_page.get("page_text", "")

            ai_text_clean = preprocess_text(ai_text).split()
            pdf_text_clean = preprocess_text(pdf_text).split()

            matcher = difflib.SequenceMatcher(None, ai_text_clean, pdf_text_clean)
            similarity = matcher.ratio()

            result = {
                "page": page_num,
                "similarity": round(similarity * 100, 2),
                "pass": similarity >= similarity_threshold
            }
            results.append(result)

            # ✅ Print for log or terminal
            print(f"Page {page_num}: Similarity = {result['similarity']}% - {'✅ Pass' if result['pass'] else '❌ Fail'}")

        return results



    def verify_opening_closing_balance_consistency(self, tolerance=0.01):
        ai_data = getattr(self, 'ai_data', {})
        pages = ai_data.get("pages", []) if isinstance(ai_data, dict) else []

        results = []

        if not pages:
            results.append("No pages found. Skipping.")
            print("No pages found. Skipping.")
            return results

        results.append("=== Multi-Page Balance Consistency Check ===")
        print("=== Multi-Page Balance Consistency Check ===")

        previous_closing = None

        for i, page_data in enumerate(pages):
            page_number = page_data.get("page_number", f"index{i}")
            results.append(f"--- Page {page_number} ---")
            print(f"--- Page {page_number} ---")

            opening_raw = page_data.get("opening_balance", "unknown")
            closing_raw = page_data.get("closing_balance", "unknown")
            transactions = page_data.get("transactions", "unknown")

            if transactions == "unknown" or not isinstance(transactions, list):
                msg = " - Invalid transactions list. Skipping."
                results.append(msg)
                print(msg)
                continue

            if opening_raw == "unknown" and previous_closing is None:
                msg = " - Missing opening balance and no previous closing to infer from. Skipping."
                results.append(msg)
                print(msg)
                continue

            try:
                ob_val = float(opening_raw) if opening_raw != "unknown" else previous_closing
            except ValueError:
                msg = f" - Invalid opening balance '{opening_raw}'. Skipping."
                results.append(msg)
                print(msg)
                continue

            try:
                stated_close = float(closing_raw)
            except ValueError:
                stated_close = None
                msg = f" - Non-numeric closing: '{closing_raw}'."
                results.append(msg)
                print(msg)

            total_txn = 0.0
            for idx, tx in enumerate(transactions, start=1):
                try:
                    total_txn += float(tx.get("amount", "0"))
                except ValueError:
                    msg = f"   Tx#{idx}: Invalid amount '{tx.get('amount')}'."
                    results.append(msg)
                    print(msg)

            expected_closing = ob_val + total_txn
            diff = abs(expected_closing - stated_close) if stated_close is not None else None

            msg_lines = [
                f"   Opening: {ob_val}",
                f"   Transactions Total: {total_txn}",
                f"   Computed Closing: {expected_closing}",
            ]

            if stated_close is not None:
                msg_lines.append(f"   Stated Closing: {stated_close}")
                if diff <= tolerance:
                    msg_lines.append(f"✅ Matches stated closing (±{tolerance})")
                else:
                    msg_lines.append(f"❌ Diff: {diff}")

            for line in msg_lines:
                results.append(line)
                print(line)

            previous_closing = expected_closing

        return results




    

    

