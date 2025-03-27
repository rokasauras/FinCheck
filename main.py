import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv
import json

from OpenAIHelper import OpenAIHelper
from PDFHandler import PDFHandler
from StatementVerifier import StatementVerifier
from LocalPreper import LocalPreper
from MachineLearning import StatementClassifier
import sqlite3
import pandas as pd
import numpy as np

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            try:
                stream.write(message)
            except ValueError:
                pass

    def flush(self):
        for stream in self.streams:
            try:
                stream.flush()
            except ValueError:
                pass

def main():
    # Load environment
    env_path = r"C:\Users\rokas\Documents\FinCheck\OpenAI.env"
    load_dotenv(env_path)
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key:
        print("Warning: OPENAI_API_KEY is not set. AI analysis won't work.\n")
    else:
        print("API key loaded successfully from .env.\n")

    # User selects a PDF
    root = tk.Tk()
    root.withdraw()
    pdf_file = filedialog.askopenfilename(
        title="Select a PDF File",
        filetypes=[("PDF Files", "*.pdf")]
    )
    if not pdf_file:
        print("No file selected. Exiting.")
        sys.exit(1)

    pdf_path = Path(pdf_file)
    if not pdf_path.exists():
        print(f"Error: File '{pdf_path}' does not exist.")
        sys.exit(1)

    # Process PDF with PDFHandler
    pdf_handler = PDFHandler(pdf_path=pdf_path, poppler_path=None)
    pdf_handler.extract_metadata()
    pdf_handler.extract_text()
    pdf_handler.convert_to_images(max_pages=20)

    print("\n=== PDF Metadata ===")
    for k, v in pdf_handler.metadata.items():
        print(f"{k}: {v}")
    print(f"\nExtracted text length: {len(pdf_handler.text)} characters.")
    print(f"Found {len(pdf_handler.images)} page images.\n")

    # Run OpenAI analysis if key is present
    USE_OPENAI = True
    gpt_response = None

    if openai_key and USE_OPENAI:
        try:
            ai_helper = OpenAIHelper(model="gpt-4o")
            gpt_response = ai_helper.analyse_bank_statements(pdf_handler.images)

            if gpt_response:
                print("\n--- OpenAI Image Analysis ---")
                print(gpt_response)
                # Parse JSON
                if isinstance(gpt_response, str):
                    try:
                        gpt_data = json.loads(gpt_response)
                    except json.JSONDecodeError:
                        print("Failed to parse OpenAI response as JSON.")
                        sys.exit(1)
                else:
                    gpt_data = gpt_response

                # Classification Check
                first_page = gpt_data.get("pages", [{}])[0]
                if first_page.get("classification") != "bank_statement":
                    print("\nDocument was not classified as a bank statement. Exiting.\n")
                    sys.exit(1)

                # Tampering Check
                pages = gpt_data.get("pages", [])
                tampering_found = any(page.get("Obvious Tampering") == 1 for page in pages)
                if tampering_found:
                    print("\nFraudulent Document Detected (Obvious Tampering = 1). Exiting.\n")
                    sys.exit(1)

                print("No obvious tampering found. Proceeding...")

            else:
                print("OpenAI returned an empty or null response.")

        except Exception as e:
            print(f"OpenAI Analysis Error: {e}")
    else:
        print("Skipping OpenAI analysis (API key missing or USE_OPENAI=False).")

    # Run StatementVerifier for local analysis
    try:
        verifier = StatementVerifier(ai_output=gpt_response, pdf_handler=pdf_handler)
        verifier.compare_text()  # sets self.ai_word_similarity
        verifier.compare_numbers()  # sets self.ai_numeric_match_ratio, etc.
        verifier.verify_opening_closing_balance_consistency()  # sets self.opening_balance, etc.

    except Exception as e:
        print(f"Error running StatementVerifier: {e}")
        sys.exit(1)

    # Use LocalPreper to parse & store final data into statements.db
    db_path = r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\statements_training.db"
    local_parser = LocalPreper(db_path=db_path)
    parse_success = local_parser.process_locally(pdf_handler, verifier)
    if parse_success:
        print("Local data has been saved to the database via LocalPreper.")
    else:
        print("Local parsing or DB save failed.")

    # ML Training and Prediction Pipeline
    try:
        # Initialise the classifier pointing to statements.db
        ml_classifier = StatementClassifier(db_path=db_path)

        # Load and preprocess data from 'statement_features'
        df = ml_classifier.load_data()
        X, y = ml_classifier.preprocess_data(df)

        # Only train if we have enough labeled data
        if not X.empty and y is not None and len(y) > 5:
            ml_classifier.train_model(X, y)
            print("Model trained successfully.")

            # 4) Retrieve newest row from DB
            conn = sqlite3.connect(db_path)
            latest_record = pd.read_sql(
                "SELECT * FROM statement_features ORDER BY id DESC LIMIT 1", 
                conn
            )
            conn.close()

            if latest_record.empty:
                print("No recent record found to predict.")
                return

            # Convert that row to dictionary
            last_row_dict = latest_record.iloc[0].to_dict()

            # Build the feature dict your model expects
            feature_cols = [
                'pdf_page_count', 'extracted_text_chars', 'ai_word_similarity',
                'ai_numeric_match_ratio', 'ai_numeric_count_diff',
                'opening_balance', 'closing_balance', 'transaction_count',
                'computed_vs_stated_diff', 'balance_mismatch'
            ]
            # Pull out only the needed features
            feature_dict = {col: last_row_dict.get(col) for col in feature_cols}

            # Convert any numpy types to python scalars
            for k, v in feature_dict.items():
                if isinstance(v, (np.generic, np.ndarray)):
                    feature_dict[k] = v.item()

            # Predict the label
            pred_label = ml_classifier.predict_label(feature_dict)

            # Update DB record
            latest_id = last_row_dict['id']
            ml_classifier.update_label_in_db(latest_id, pred_label)

            label_name = "Legit" if pred_label == 0 else "Fraudulent"
            print(f"\n=== Prediction ===")
            print(f"Document ID:  {latest_id}")
            print(f"Label:        {pred_label} ({label_name})")

        else:
            print("Insufficient labeled data - skipping ML prediction.")

    except Exception as e:
        print(f"ML Pipeline Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    log_path = Path("output_logs/log.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, message):
            for s in self.streams:
                try:
                    s.write(message)
                except ValueError:
                    pass
        def flush(self):
            for s in self.streams:
                try:
                    s.flush()
                except ValueError:
                    pass

    with open(log_path, "w", encoding="utf-8") as log_file:
        sys.stdout = Tee(sys.__stdout__, log_file)

        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

    print(f"Logs written to {log_path}")
