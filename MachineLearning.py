import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import json
from SQLPreper import SQLPreper

class StatementClassifier:
    def __init__(self, db_path):
        self.db_path = db_path 
        self.model = None 
    
    

    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM statement_features WHERE label IS NOT NULL"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def preprocess_data(self, df):
        features = [
            'pdf_page_count', 'extracted_text_chars', 'ai_word_similarity',
            'ai_numeric_match_ratio', 'ai_numeric_count_diff',
            'opening_balance', 'closing_balance', 'transaction_count',
            'computed_vs_stated_diff', 'balance_mismatch'
        ]

        df = df.dropna(subset=['label'] + features)
        df = df.copy()  # ensure we operate on a real, independent DataFrame

        df['balance_mismatch'] = df['balance_mismatch'].astype(int)
        df['label'] = df['label'].astype(int)

        X = df[features]
        y = df['label']
        return X, y

    def train_model(self, X, y):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=1
        )
        self.model = RandomForestClassifier(n_estimators=200, random_state=1)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        print("Model Performance:")
        print(classification_report(y_test, y_pred, zero_division=0))

    def predict_label(self, feature_dict):
        if not self.model:
            raise ValueError("Model not trained yet.")
        df_input = pd.DataFrame([feature_dict])
        return int(self.model.predict(df_input)[0])

    def update_label_in_db(self, statement_id, predicted_label):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE statement_features
            SET label = ?
            WHERE id = ?
        """, (predicted_label, statement_id))
        conn.commit()
        conn.close()
        print(f"Updated statement ID {statement_id} with label={predicted_label}.")

def extract_features_for_prediction(full_record):
    expected_features = [
        "pdf_page_count", "extracted_text_chars", "ai_word_similarity",
        "ai_numeric_match_ratio", "ai_numeric_count_diff",
        "opening_balance", "closing_balance", "transaction_count",
        "computed_vs_stated_diff", "balance_mismatch"
    ]
    # Ensure all expected features are present in the record
    float_keys = {
        "ai_word_similarity", "ai_numeric_match_ratio",
        "opening_balance", "closing_balance", "computed_vs_stated_diff",
    }
    int_keys = { # These are not float, but should be treated as such
        "pdf_page_count", "extracted_text_chars", "transaction_count",
        "ai_numeric_count_diff", "balance_mismatch"
    }

    feature_dict = {}
    for key in expected_features:
        value = full_record.get(key, 0.0 if key in float_keys else 0)
        feature_dict[key] = float(value) if key in float_keys else int(value)
    return feature_dict

    


if __name__ == "__main__": 
    db_path = r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\statements_training.db"

    classifier = StatementClassifier(db_path)

    df = classifier.load_data()
    X, y = classifier.preprocess_data(df)
    if len(X) == 0:
        print("No data available for training.")
        exit()

    classifier.train_model(X, y)

    sql_preper = SQLPreper()
    with open("output_logs/log.txt", "r", encoding="utf-8") as f:
        log_text = f.read()

    record_dict = sql_preper.parse_log_with_ai(log_text)
    if not record_dict:
        print("Failed to retrieve data for prediction.")
        exit()

    new_statement_features = extract_features_for_prediction(record_dict)

    predicted_label = classifier.predict_label(new_statement_features)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM statement_features ORDER BY id DESC LIMIT 1")
    latest_id = cursor.fetchone()[0]
    conn.close()

    classifier.update_label_in_db(latest_id, predicted_label)

    label_name = "Legit" if predicted_label == 0 else "Fraudulent"
    print(f"\nFinal Prediction: {label_name} (Label: {predicted_label})")

