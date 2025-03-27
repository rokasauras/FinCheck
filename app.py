import streamlit as st
import os
import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from io import StringIO
import contextlib

# Custom classes
from PDFHandler import PDFHandler
from OpenAIHelper import OpenAIHelper
from StatementVerifier import StatementVerifier
from LocalPreper import LocalPreper

# We'll modify StatementClassifier to handle SettingWithCopy and zero_division
from MachineLearning import StatementClassifier

# ============== Streamlit Page Config ==============
st.set_page_config(page_title="Bank Statement Fraud Detector", layout="centered")
st.title("📄 Bank Statement Fraud Detector")

# ============== Environment & Constants ==============
@st.cache_resource
def load_environment():
    load_dotenv(r"C:\Users\rokas\Documents\FinCheck\OpenAI.env")
    return os.getenv("OPENAI_API_KEY")

openai_key = load_environment()
DB_PATH = r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\statements_training.db"

# ============== ML Classifier ==============
@st.cache_resource
def get_classifier():
    return StatementClassifier(db_path=DB_PATH)

# ============== File Uploader ==============
uploaded_file = st.file_uploader("Upload a PDF bank statement", type=["pdf"])
if not uploaded_file:
    st.info("Please upload a PDF to begin.")
    st.stop()

# ============== PDF Processing Pipeline ==============
def process_pdf(file_data):
    """Main pipeline: PDF -> OpenAI (optional) -> StatementVerifier -> LocalPreper -> ML Prediction."""
    with st.spinner("Processing PDF..."):
        try:
            # Save PDF to temp
            temp_pdf_path = Path("temp_upload.pdf")
            temp_pdf_path.write_bytes(file_data.getvalue())

            # Extract Data via PDFHandler
            pdf_handler = PDFHandler(pdf_path=temp_pdf_path)
            pdf_handler.extract_metadata()
            pdf_handler.extract_text()
            pdf_handler.convert_to_images(max_pages=20)

            # Show some metadata
            st.subheader("📄 Document Metadata")
            st.json(pdf_handler.metadata)

            # Show PDF text in an expander
            with st.expander("📝 Extracted Text from PDFHandler"):
                # You can show all or a partial preview
                st.write(pdf_handler.text[:1000] + "..." if len(pdf_handler.text) > 2000 else pdf_handler.text)

            # OpenAI Analysis
            gpt_response = None
            if openai_key:
                    ai_helper = OpenAIHelper(model="gpt-4o")
                    gpt_response = ai_helper.analyse_bank_statements(pdf_handler.images)

                    if gpt_response:
                        try:
                            parsed_gpt = json.loads(gpt_response) if isinstance(gpt_response, str) else gpt_response
                            st.subheader("🤖 AI Image Analysis")
                            st.json(parsed_gpt)

                            # Classification Check
                            first_page = parsed_gpt.get("pages", [{}])[0]
                            if first_page.get("classification") != "bank_statement":
                                st.error("❌ Document not classified as bank statement.")
                                st.stop()

                            # Tampering Check
                            tampering = any(p.get("Obvious Tampering") == 1 for p in parsed_gpt.get("pages", []))
                            if tampering:
                                st.error("🚨 Tampering Detected! Marking as fraudulent.")
                                st.stop()

                            st.success("No obvious tampering found. Proceeding...")

                        except json.JSONDecodeError:
                            st.error("Failed to parse AI response as JSON.")
                    else:
                        st.info("OpenAI returned an empty/null response.")
            else:
                st.info("OpenAI key missing; skipping AI analysis.")

            # Local Verification
            verifier = StatementVerifier(ai_output=gpt_response, pdf_handler=pdf_handler)

            # Capture console output to show in Streamlit
            with st.expander("🔍 Text Comparison Results"):
                output_buf = StringIO()
                with contextlib.redirect_stdout(output_buf):
                    verifier.compare_text()
                st.text(output_buf.getvalue())

            with st.expander("🔢 Number Comparison Results"):
                output_buf = StringIO()
                with contextlib.redirect_stdout(output_buf):
                    verifier.compare_numbers()
                st.text(output_buf.getvalue())

            with st.expander("⚖️ Balance Consistency Check"):
                output_buf = StringIO()
                with contextlib.redirect_stdout(output_buf):
                    verifier.verify_opening_closing_balance_consistency()
                st.text(output_buf.getvalue())

            # Store results into DB
            with st.spinner("Storing data locally..."):
                local_parser = LocalPreper(db_path=DB_PATH)
                if local_parser.process_locally(pdf_handler, verifier):
                    st.success("✅ Data saved to database.")
                else:
                    st.error("❌ Failed to save data.")

            # Train the Model before final prediction
            ml_classifier = get_classifier()
            df_data = ml_classifier.load_data()
            X, y = ml_classifier.preprocess_data(df_data)

            if not X.empty and len(X) > 5:
                ml_classifier.train_model(X, y)
                st.success("Model trained successfully before final prediction.")
            else:
                st.warning("Insufficient labelled data (need >5) - skipping training. The model remains untrained.")
                
            # Final ML Prediction on last inserted record
            conn = sqlite3.connect(DB_PATH)
            latest_record = pd.read_sql_query("SELECT * FROM statement_features ORDER BY id DESC LIMIT 1", conn)
            conn.close()

            if not latest_record.empty and ml_classifier.model is not None:
                row_dict = latest_record.iloc[0].to_dict()

                # Prepare features for the model
                needed_cols = [
                    'pdf_page_count','extracted_text_chars','ai_word_similarity','ai_numeric_match_ratio',
                    'ai_numeric_count_diff','opening_balance','closing_balance','transaction_count',
                    'computed_vs_stated_diff','balance_mismatch'
                ]
                features = {col: row_dict.get(col, 0) for col in needed_cols}

                # Convert numpy/scalar types
                for k, v in features.items():
                    if isinstance(v, np.generic):
                        features[k] = v.item()

                # Predict label
                try:
                    prediction = ml_classifier.predict_label(features)
                    label_str = "✅ Legit" if prediction == 0 else "🚨 Fraudulent"
                    st.write(f"**Last Statement ID**: {row_dict.get('id')}")
                    st.subheader(f"🧠 Model Prediction: {label_str} (Label={prediction})")

                    # Update DB
                    ml_classifier.update_label_in_db(row_dict['id'], prediction)
                    st.success("Database updated with final prediction.")
                except ValueError as e:
                    st.error(f"Prediction failed (model not trained?): {e}")
            else:
                st.warning("No records found in DB to predict on, or model was never trained.")

        finally:
            # Cleanup temp file
            if temp_pdf_path.exists():
                temp_pdf_path.unlink()

# ============== Run the Pipeline ==============
process_pdf(uploaded_file)


