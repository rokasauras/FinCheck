import streamlit as st
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from PDFHandler import PDFHandler
from OpenAIHelper import OpenAIHelper
from OpenAIHelper import OpenAIHelper
from PDFHandler import PDFHandler
from StatementVerifier import StatementVerifier
from SQLPreper import SQLPreper

# --- Streamlit Setup ---
st.set_page_config(page_title="Bank Statement Fraud Detector", layout="centered")
st.title("📄 Bank Statement Fraud Detector")

# --- Step 1: Load Environment Variables ---
@st.cache_resource
def load_environment():
    load_dotenv(r"C:\Users\rokas\Documents\FinCheck\OpenAI.env")
    return os.getenv("OPENAI_API_KEY")

openai_key = load_environment()

# --- Step 2: Upload PDF ---
uploaded_file = st.file_uploader("Upload PDF Statement", type=["pdf"])

# --- Step 3: Process PDF ---
def process_pdf(uploaded_file):
    """Main processing pipeline"""
    with st.spinner("Processing PDF..."):
        try:
            # Save uploaded file temporarily
            temp_path = Path("temp_upload.pdf")
            temp_path.write_bytes(uploaded_file.getvalue())

            # Initialise PDF handler
            pdf_handler = PDFHandler(temp_path)
            pdf_handler.extract_metadata()
            pdf_handler.extract_text()
            pdf_handler.convert_to_images(max_pages=20)

            # Display metadata
            st.subheader("📄 Document Metadata")
            st.json(pdf_handler.metadata)

            # Display text preview
            st.subheader("📃 Extracted Text Preview")
            st.json({p['page_number']: p['page_text'][:1000] for p in pdf_handler.text_pages})

            # --- AI Analysis ---
            if openai_key:
                ai_helper = OpenAIHelper(model="gpt-4o")
                gpt_response = ai_helper.analyse_bank_statements(pdf_handler.images)

                if gpt_response:
                    st.subheader("🤖 AI Image Analysis")
                    try:
                        parsed_response = json.loads(gpt_response) if isinstance(gpt_response, str) else gpt_response
                        st.session_state["parsed_response"] = parsed_response
                        st.json(parsed_response)

                        # Confirm step is reached
                        st.success("✅ Reached verification step")

                        # 👇 Add this line for a clear section heading
                        st.subheader("🧪 Verification Results")

                        verifier = StatementVerifier(ai_output=parsed_response, pdf_handler=pdf_handler)

                        with st.expander("🔍 Text Comparison"):
                            text_results = verifier.compare_text()
                            for res in text_results:
                                st.markdown(f"**Page {res['page']}** — Similarity: {res['similarity']}%")
                                if res['pass']:
                                    st.success("Pass")
                                else:
                                    st.error("Fail")

                        with st.expander("🔢 Number Matching"):
                            num_results = verifier.compare_numbers()
                            for res in num_results:
                                st.markdown(f"**Page {res['page']}** — Match Ratio: {res['match_ratio']}%")
                                if res['exact_match']:
                                    st.success("Exact Match")
                                else:
                                    st.error("Mismatch")

                        with st.expander("⚖️ Balance Consistency"):
                            balance_results = verifier.verify_opening_closing_balance_consistency()
                            for line in balance_results:
                                st.write(line)
                                if res['pass']:
                                    st.success("Pass")
                                else:
                                    st.error("Fail")

                        sql_preper = SQLPreper()
                        log_path = "output_logs/log.txt"
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8") as f:
                                log_text = f.read()
                                parsed_record = sql_preper.parse_log_with_ai(log_text)

                                print("\n--- Parsed Log Data ---")
                                print(json.dumps(parsed_record, indent=2))
                        else:
                            print("No log file found at expected path.")



                    except json.JSONDecodeError as e:
                        st.error(f"Failed to parse AI response as JSON: {e}")
                else:
                    st.warning("OpenAI returned an empty or null response.")
            else:
                st.warning("OpenAI API key missing – skipping AI analysis.")

        except Exception as e:
            st.error(f"Processing error: {str(e)}")

        finally:
            if temp_path.exists():
                temp_path.unlink()


# --- Run Analysis if File is Uploaded ---
if uploaded_file:
    process_pdf(uploaded_file)
else:
    st.info("📥 Please upload a PDF bank statement to begin.")