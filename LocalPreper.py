import os
import sqlite3
import datetime
import json
from pathlib import Path
from PDFHandler import PDFHandler
from StatementVerifier import StatementVerifier

class LocalPreper:
    """
    A class that gathers all locally extracted data (metadata, text analysis,
    numeric comparisons, etc.) from PDFHandler, StatementVerifier,
    and other local modules, then stores them into 'statement_features'.
    """

    def __init__(self, db_path=None):
        """
        :param db_path: Path to the SQLite database (e.g. 'statements.db').
                        Defaults to 'statements.db' if not provided.
        """
        db_path = r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\statements_training.db"
        self.db_path = db_path 

    def gather_data(self, pdf_handler, statement_verifier):
        """
        Gather locally extracted info from pdf_handler and statement_verifier
        and return a dictionary that matches the columns in statement_features.

        pdf_handler: an instance of PDFHandler after .extract_* methods have run
        statement_verifier: an instance of StatementVerifier after compare_* methods
        """
        # Basic PDF metadata
        metadata = pdf_handler.metadata or {}
        pdf_page_count = metadata.get("Pages", 0)
        pdf_title = metadata.get("Title", "")
        pdf_author = metadata.get("Author", "")
        pdf_creator = metadata.get("Creator", "")
        pdf_producer = metadata.get("Producer", "")
        pdf_creation_date = metadata.get("Creation Date", "")
        pdf_mod_date = metadata.get("Modification Date", "")

        # Extracted text length
        extracted_text_chars = len(pdf_handler.text or "")

        # AI analysis results
        ai_word_similarity = statement_verifier.get_text_similarity_ratio() if hasattr(statement_verifier, "get_text_similarity_ratio") else None
        ai_numeric_match_ratio = getattr(statement_verifier, "ai_numeric_match_ratio", None)
        ai_numeric_count_diff = getattr(statement_verifier, "ai_numeric_count_diff", None)
        # StatementVerifier results
        opening_balance = getattr(statement_verifier, "opening_balance", None)
        closing_balance = getattr(statement_verifier, "closing_balance", None)
        transaction_count = getattr(statement_verifier, "transaction_count", None)
        computed_vs_stated_diff = getattr(statement_verifier, "computed_vs_stated_diff", None)
        balance_mismatch = getattr(statement_verifier, "balance_mismatch", None)

        # Label (0 for legit, 1 for fraud, or None if unknown)
        label = None
        

        # Build a dictionary matching statement_features columns
        parsed_data = {
            "pdf_page_count": pdf_page_count,
            "pdf_title": pdf_title,
            "pdf_author": pdf_author,
            "pdf_creator": pdf_creator,
            "pdf_producer": pdf_producer,
            "pdf_creation_date": pdf_creation_date,
            "pdf_mod_date": pdf_mod_date,
            "extracted_text_chars": extracted_text_chars,
            "ai_word_similarity": ai_word_similarity,
            "ai_numeric_match_ratio": ai_numeric_match_ratio,
            "ai_numeric_count_diff": ai_numeric_count_diff,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "transaction_count": transaction_count,
            "computed_vs_stated_diff": computed_vs_stated_diff,
            "balance_mismatch": balance_mismatch,
            "label": label  # 0 for legit, 1 for fraud, or None if unknown
        }

        return parsed_data
    # Save the parsed_data dictionary to the statement_features table
    def save_to_database(self, parsed_data):
        """
        Save the parsed_data dictionary to the statement_features table
        in the local SQLite database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            required_fields = [
                'pdf_page_count', 'pdf_title', 'pdf_author', 'pdf_creator',
                'pdf_producer', 'pdf_creation_date', 'pdf_mod_date',
                'extracted_text_chars', 'ai_word_similarity', 'ai_numeric_match_ratio',
                'ai_numeric_count_diff', 'opening_balance', 'closing_balance',
                'transaction_count', 'computed_vs_stated_diff', 'balance_mismatch',
                'label'
            ]

            # Build the list of values in order
            values = [parsed_data.get(field, None) for field in required_fields]
            # Append a timestamp
            values.append(datetime.datetime.now())

            # Insert or replace if a matching row is found
            insert_query = """
            INSERT OR REPLACE INTO statement_features (
                pdf_page_count,
                pdf_title,
                pdf_author,
                pdf_creator,
                pdf_producer,
                pdf_creation_date,
                pdf_mod_date,
                extracted_text_chars,
                ai_word_similarity,
                ai_numeric_match_ratio,
                ai_numeric_count_diff,
                opening_balance,
                closing_balance,
                transaction_count,
                computed_vs_stated_diff,
                balance_mismatch,
                label,
                scanned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(insert_query, values)
            conn.commit()
            conn.close()

            print(f"Data saved to database. Title: {parsed_data.get('pdf_title', 'unknown')}")
        except Exception as e:
            print(f"Database error: {e}")

    def process_locally(self, pdf_handler, statement_verifier):
        """
        Main workflow to gather local data from PDFHandler, StatementVerifier,
        then save to DB.
        """
        if not Path(self.db_path).exists():
            print(f"Database not found at: {self.db_path}")
            return False

        # Gather from local classes
        parsed_data = self.gather_data(pdf_handler, statement_verifier)
        if not parsed_data:
            print("No data gathered. Exiting.")
            return False

        # Insert
        self.save_to_database(parsed_data)
        return True
