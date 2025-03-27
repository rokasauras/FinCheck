import os
import sqlite3
import datetime
import json
from dotenv import load_dotenv
from openai import OpenAI

class SQLPreper:
    def __init__(self, log_path=None, db_path=None, openai_env_path=None):
        # Initialise paths with defaults if not provided
        self.log_path = log_path or r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\output_logs\log.txt"
        self.db_path = db_path or "statements.db"
        self.openai_env_path = openai_env_path or r"C:\Users\rokas\Documents\FinCheck\OpenAI.env"
        
        # Initialise OpenAI client
        self.client = None
        self._initialize_openai()

    def _initialize_openai(self):
        """Load OpenAI API key from environment file"""
        try:
            load_dotenv(self.openai_env_path)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment file")
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            self.client = None

    def extract_log_data(self):
        """Extract data from log file"""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Log file not found at {self.log_path}")
            return None
        except Exception as e:
            print(f"Error reading log file: {e}")
            return None

    def parse_log_with_ai(self, log_text):
        """Parse log text using OpenAI's API"""
        if not self.client:
            print("OpenAI client not initialized")
            return None

        try:
            prompt = f"""
        You are an AI log-parsing assistant.

        I have the following logs from a bank statement analysis script:

        {log_text}

        Please return a JSON object with these fields (only) – if you can derive them from the logs, do so; 
        otherwise, set them to null:

        - pdf_page_count (integer)
        - pdf_title (text)
        - pdf_author (text)
        - pdf_creator (text)
        - pdf_producer (text)
        - pdf_creation_date (text)
        - pdf_mod_date (text)
        - extracted_text_chars (integer)
        - ai_word_similarity (float)
        - ai_numeric_match_ratio (float)
        - ai_numeric_count_diff (integer)
        - opening_balance (float)
        - closing_balance (float)
        - transaction_count (integer)
        - computed_vs_stated_diff (float)
        - balance_mismatch (0 or 1)
        - label (0 for legit, 1 for fraud, null if unsure)
        - Title (text)

        IMPORTANT details for ai_numeric_count_diff and ai_numeric_match_ratio:
        1) If the logs explicitly show how many numeric tokens AI found (e.g. 'Numberic_count_ai: 64') 
        and how many numeric tokens the PDF had (e.g. 'Numberic_count_pdf: 63'), 
        then:
        - ai_numeric_count_diff = |Numberic_count_ai - Numberic_count_pdf|
        - ai_numeric_match_ratio = (the portion that match) 
            * If the logs say 'All numeric values match', assume ratio = 1.0
            * If partial matches, try to compute approximate ratio from the logs (like 63 / 64 => 0.984).
        2) If the logs only say 'All numeric values match!' but don't provide a count, 
        set ai_numeric_count_diff=0 and ai_numeric_match_ratio=1.0.
        3) If the logs do not mention numeric counts or partial matching, set both fields to null.

        For computed_vs_stated_diff, similarly:
        - If the logs show how to compute it (e.g. 'Opening: 7126.11' and 'Closing: 10521.19' 
        plus a transaction sum?), attempt it. 
        - If the logs explicitly mention 'Mismatch! Difference: 105.00', set that as the float. 
        - Else, null.

        Return strictly valid JSON, with no additional commentary or keys. 
        If uncertain about any field, use null.
        """  

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            return json.loads(response.choices[0].message.content)
        
        except json.JSONDecodeError:
            print("Failed to parse OpenAI response as JSON")
            return None
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def save_to_database(self, parsed_data):
        """Save parsed data to SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Required fields (keep your existing field list)
            required_fields = ['pdf_page_count', 'pdf_title', 'pdf_author', 'pdf_creator',
            'pdf_producer', 'pdf_creation_date', 'pdf_mod_date',
            'extracted_text_chars', 'ai_word_similarity', 'ai_numeric_match_ratio',
            'ai_numeric_count_diff', 'opening_balance', 'closing_balance',
            'transaction_count', 'computed_vs_stated_diff', 'balance_mismatch',
            'label']  
            values = [parsed_data.get(field, None) for field in required_fields] + [datetime.datetime.now()]

            cursor.execute("""
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
        """, values)  # Insert or update if record already exists
            conn.commit()
            conn.close()
            print(f"Data saved to database for file: {parsed_data.get('file_name', 'unknown')}")
        
        except Exception as e:
            print(f"Database error: {e}")

    def process_log(self):
        """Main processing workflow"""
        if not os.path.exists(self.log_path):
            print(f"Log file not found at: {self.log_path}")
            return False

        log_text = self.extract_log_data()
        if not log_text:
            return False

        parsed_data = self.parse_log_with_ai(log_text)
        if not parsed_data:
            return False

        self.save_to_database(parsed_data)
        return True
    
if __name__ == "__main__":
    preper = SQLPreper()
    preper.process_log()
