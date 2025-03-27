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
    text = re.sub(r'\s+', ' ', text) # Collapse whitespace
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

    def __init__(self, ai_output=None, pdf_handler=None): 
        """
        Initialise the StatementVerifier with AI-generated and locally extracted text data.

        :param ai_output: JSON output from OpenAI Vision (image analysis) as a string or dict.
        :param pdf_handler: An instance of PDFHandler with extracted text data, or None.
        """

        self.pdf_handler = pdf_handler
        self.ai_output = ai_output
        # If ai_output is a string, try to load it as JSON; otherwise, assume it's already a dict.
        self.ai_data = self.load_json(ai_output) if isinstance(ai_output, str) else ai_output # AI data
        self.pdf_handler = pdf_handler # PDFHandler instance

        self.ai_word_similarity = None
        self.ai_numeric_match_ratio = None
        self.ai_numeric_count_diff = None
        self.opening_balance = None
        self.closing_balance = None
        self.transaction_count = None
        self.computed_vs_stated_diff = None
        self.balance_mismatch = None

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
        Compares the 'page_text' from AI vs. PDF output based on WORD similarity.
        Stores similarity ratios and diffs for later analysis.
        Also sets self.ai_word_similarity for LocalPreper to pick up.
        """
        print("\n=== Comparing AI Vision Output with PDF Extracted Text ===\n")
        
        self.page_similarities = {}
        self.text_diffs = {}

        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        for page_num in range(1, total_pages + 1):
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "unknown")
            pdf_text = pdf_page.get("page_text", "unknown")

            # Preprocess and split texts into words for comparison
            ai_words = preprocess_text(ai_text).split()
            pdf_words = preprocess_text(pdf_text).split()

            matcher = difflib.SequenceMatcher(None, ai_words, pdf_words)
            similarity = matcher.ratio()
            
            self.page_similarities[page_num] = similarity
            self.text_diffs[page_num] = None  # to store diff lines if needed

            print(f"\n--- Page {page_num} ---")
            print(f"Word-based Similarity Ratio: {similarity:.2f}")

            if similarity < similarity_threshold:
                print("Significant differences detected:")
                diff = difflib.unified_diff(
                    pdf_words,
                    ai_words,
                    fromfile="PDF Extracted Text",
                    tofile="AI Vision Text",
                    lineterm=""
                )
                diff_lines = list(diff)
                self.text_diffs[page_num] = diff_lines
                
                for line in diff_lines:
                    print(line)
            else:
                print("Text similarity is acceptable.")

        # Calculate overall similarity
        if self.page_similarities:
            self.overall_similarity = sum(self.page_similarities.values()) / len(self.page_similarities)
        else:
            self.overall_similarity = 0

        # We store overall_similarity in a more standard attribute name for LocalPreper
        self.ai_word_similarity = self.overall_similarity

        print(f"\nOverall similarity across all pages: {self.overall_similarity:.2f}")

    def get_text_similarity_ratio(self):
        """
        Provide a getter for the overall text similarity ratio, 
        so LocalPreper can do: statement_verifier.get_text_similarity_ratio()
        """
        return getattr(self, 'ai_word_similarity', 0.0)

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

        At the end:
        - self.ai_numeric_match_ratio stores the overall percentage match
        - self.ai_numeric_count_diff stores the overall difference in token counts
        """
        print("\n=== Comparing Numeric Values Between AI and PDF ===\n")

        total_common_count = 0
        total_ai_numbers = 0
        total_pdf_numbers = 0

        # For debug: track number of pages actually processed
        total_pages = max(len(self.pages_ai["pages"]), len(self.pages_pdf["pages"]))

        for page_num in range(1, total_pages + 1):
            # Retrieve page data for both AI and PDF
            ai_page = next((p for p in self.pages_ai["pages"] if p.get("page_number") == page_num), {})
            pdf_page = next((p for p in self.pages_pdf["pages"] if p.get("page_number") == page_num), {})

            ai_text = ai_page.get("page_text", "")
            pdf_text = pdf_page.get("page_text", "")

            # Extract numeric tokens
            ai_numbers = self.extract_numbers(ai_text)
            pdf_numbers = self.extract_numbers(pdf_text)

            print(f"--- Page {page_num} ---")
            print(f"AI Numbers: {ai_numbers}")
            print(f"PDF Numbers: {pdf_numbers}")

            if len(ai_numbers) != len(pdf_numbers):
                print("Number of numeric tokens does NOT match!")
            else:
                print("Number of numeric tokens match in count.")

            # Compare ignoring order using Counter
            ai_counter = Counter(ai_numbers)
            pdf_counter = Counter(pdf_numbers)

            # Calculate how many tokens match in a min-frequency sense
            page_common_count = 0
            for token, count in ai_counter.items():
                page_common_count += min(count, pdf_counter.get(token, 0))

            # Summation for overall
            total_common_count += page_common_count
            total_ai_numbers += len(ai_numbers)
            total_pdf_numbers += len(pdf_numbers)

            # For display: compute a per-page ratio
            page_total = max(len(ai_numbers), len(pdf_numbers))
            if page_total > 0:
                page_match_ratio = (page_common_count / page_total) * 100
            else:
                page_match_ratio = 0

            # Check if counters fully match
            if ai_counter == pdf_counter and len(ai_numbers) == len(pdf_numbers):
                print("All numeric values match exactly!")
            else:
                print("Mismatched numeric values!")
                print("Sorted AI:  ", sorted(ai_numbers))
                print("Sorted PDF: ", sorted(pdf_numbers))

            # Always print numeric info
            print(f"Numeric Match Ratio (page {page_num}): {page_match_ratio:.2f}%")
            print(f"Numberic_count_ai: {len(ai_numbers)}")
            print(f"Numberic_count_pdf: {len(pdf_numbers)}")
            print(f"Numberic_count_diff: {len(ai_numbers) - len(pdf_numbers)}\n")

        # Final overall values across all pages
        overall_total = max(total_ai_numbers, total_pdf_numbers)
        if overall_total > 0:
            self.ai_numeric_match_ratio = (total_common_count / overall_total) * 100
        else:
            self.ai_numeric_match_ratio = 0

        self.ai_numeric_count_diff = abs(total_ai_numbers - total_pdf_numbers)

        # Debug print
        print(f"== Overall Numeric Match Ratio: {self.ai_numeric_match_ratio:.2f}% ==")
        print(f"== Overall Numeric Count Diff: {self.ai_numeric_count_diff} ==\n")


    def verify_opening_closing_balance_consistency(self, tolerance=0.01):
        """
        Iterates through each page in self.ai_data (or self.pages_ai),
        computing or comparing opening balances, closing balances, 
        transaction sums, etc. 
        In the end, sets attributes for LocalPreper to pick up:
        - self.opening_balance
        - self.closing_balance
        - self.transaction_count
        - self.computed_vs_stated_diff
        - self.balance_mismatch
        """
        # Initialize these so LocalPreper can read them later
        self.opening_balance = None
        self.closing_balance = None
        self.transaction_count = 0
        self.computed_vs_stated_diff = 0.0
        self.balance_mismatch = 0  # 1 if mismatch found, else 0

        # Attempt to fetch AI data or pages
        ai_data = getattr(self, 'ai_data', {})
        pages = ai_data.get("pages", []) if isinstance(ai_data, dict) else []
        if not pages:
            print("No pages found. Skipping multi-page balance consistency.")
            return

        print("\n=== Running Multi-Page Balance Consistency Check ===")

        previous_closing = None
        any_mismatch = False  # Track if any page shows mismatch

        total_transactions = 0

        for i, page_data in enumerate(pages):
            page_number = page_data.get("page_number", f"index{i}")
            print(f"\n[Page {page_number}] Checking balances...")

            # Extract the balances and transactions
            opening_raw = page_data.get("opening_balance", "unknown")
            closing_raw = page_data.get("closing_balance", "unknown")
            transactions = page_data.get("transactions", "unknown")

            if transactions == "unknown" or not isinstance(transactions, list):
                print(" - Missing or invalid transactions list. Skipping page.")
                continue

            # Decide the page's effective opening balance
            if opening_raw == "unknown" and previous_closing is not None:
                ob_val = previous_closing
                print(f"   Using last page's computed closing ({previous_closing}) as this page's opening.")
            else:
                try:
                    ob_val = float(opening_raw)
                except ValueError:
                    print(f"   Non-numeric opening_balance '{opening_raw}'. Skipping page.")
                    continue

            # Convert or skip the closing
            try:
                stated_close = float(closing_raw)
            except ValueError:
                stated_close = None
                print(f"   Stated closing is non-numeric or unknown: '{closing_raw}'.")

            # Sum the transactions
            page_txn_sum = 0.0
            for idx, tx in enumerate(transactions, start=1):
                amount_str = tx.get("amount", "0")
                try:
                    parsed = float(amount_str)
                    page_txn_sum += parsed
                except ValueError:
                    print(f"   Tx#{idx}: Invalid transaction amount '{amount_str}'. Using 0.")

            # Compute expected final
            expected_closing = ob_val + page_txn_sum

            # Print stats
            msg_lines = [
                f"   Opening:         {ob_val}",
                f"   Transactions:    {page_txn_sum}",
                f"   Computed Final:  {expected_closing}",
            ]

            diff_value = 0.0
            if stated_close is not None:
                diff_value = abs(expected_closing - stated_close)
                msg_lines.append(f"   Stated Closing:  {stated_close}")
                if diff_value <= tolerance:
                    msg_lines.append(f"Matches stated closing (±{tolerance}).")
                else:
                    msg_lines.append(f"Mismatch! Difference: {diff_value}")
                    any_mismatch = True

            for line in msg_lines:
                print(line)

            # Print a simpler difference line for localpreper
            actual_diff = stated_close if stated_close is not None else expected_closing
            mismatch_state = abs(expected_closing - actual_diff) > tolerance
            print(f"Balance_diff (page {page_number}): {expected_closing - (stated_close or 0)}")
            print(f"Balance_mismatch: {mismatch_state}")

            # Update rolling values
            previous_closing = expected_closing
            total_transactions += len(transactions)

            # Store final values on the last page
            if i == len(pages) - 1:
                # On the final page, store in self:
                self.opening_balance = ob_val
                # If stated close is numeric, store that; else store computed
                self.closing_balance = stated_close if stated_close is not None else expected_closing
                self.transaction_count = total_transactions
                self.computed_vs_stated_diff = diff_value

        # If any mismatch found, set balance_mismatch=1
        self.balance_mismatch = 1 if any_mismatch else 0

        print("\n=== Finished Multi-Page Balance Check ===")
        print(f"Storing final opening_balance: {self.opening_balance}, closing_balance: {self.closing_balance}, "
            f"transaction_count: {self.transaction_count}, computed_vs_stated_diff: {self.computed_vs_stated_diff}, "
            f"balance_mismatch: {self.balance_mismatch}")





    

    

