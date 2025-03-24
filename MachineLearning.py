import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt
import json
from SQLPreper import SQLPreper




class StatementClassifier:
    def __init__(self, db_path):
        """
        :param db_path: Path to the SQLite database containing statement_features table.
        """
        self.db_path = db_path
        self.model = None  # Placeholder for the trained model

    def load_data(self):
        """
        Connect to the SQLite database and load statement_features into a DataFrame.
        Only load rows with a non-null label so we have supervised data.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT *
            FROM statement_features
            WHERE label IS NOT NULL
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def preprocess_data(self, df):
        """
        Preprocess the DataFrame by selecting useful features,
        dropping nulls, and preparing for model training.
        """

        # Select features — only numeric and useful boolean columns
        features = [
            'pdf_page_count',
            'extracted_text_chars',
            'ai_word_similarity',
            'ai_numeric_match_ratio',
            'ai_numeric_count_diff',
            'opening_balance',
            'closing_balance',
            'transaction_count',
            'computed_vs_stated_diff',
            'balance_mismatch'
        ]

        label_col = 'label'

        # Drop rows with missing labels
        df = df.dropna(subset=[label_col])

        # Drop rows where any of the selected features are missing
        df = df.dropna(subset=features)

        # Optional: Convert balance_mismatch and label to integers if needed
        df['balance_mismatch'] = df['balance_mismatch'].astype(int)
        df['label'] = df['label'].astype(int)

        # Split into features and target
        X = df[features]
        y = df[label_col]

        return X, y

    def train_model(self, X, y):
        """
        Train a random forest (or any other classifier) on the data.
        """
        # Split the data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train the model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

        # Evaluate the model
        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        print("\nModel Performance on Test Set:")
        print(f"Accuracy: {acc:.2f}")
        print("Classification Report:")
        print(classification_report(y_test, y_pred))

        importances = self.model.feature_importances_
        feature_names = X.columns

        plt.figure(figsize=(10, 5))
        plt.barh(feature_names, importances)
        plt.title("Feature Importances")
        plt.xlabel("Relative Importance")
        plt.tight_layout()
        plt.show()

    def predict_label(self, feature_dict):
        """
        Given a dictionary of features (keys matching the columns used in training),
        predict whether the statement is legit (1) or not (0).
        """
        if not self.model:
            raise ValueError("No model found. Train the model before prediction.")

        # Convert the feature_dict to a DataFrame row
        df_input = pd.DataFrame([feature_dict])

        # Predict the label
        pred = self.model.predict(df_input)[0]
        return int(pred)

    def update_label_in_db(self, statement_id, predicted_label):
        # Update the label in the database for a given statement ID
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        update_query = """
            UPDATE statement_features
            SET label = ?
            WHERE id = ?
        """
        cursor.execute(update_query, (predicted_label, statement_id))
        conn.commit()
        conn.close()
        print(f"Updated record {statement_id} with label={predicted_label}.")

def extract_features_for_prediction(full_record):
    """
    Extract ML-ready features from a dictionary of PDF/AI data.
    Missing or null values are replaced with safe defaults and 
    cast to the correct types (int or float).
    """
    expected_features = [
        "pdf_page_count",
        "extracted_text_chars",
        "ai_word_similarity",
        "ai_numeric_match_ratio",
        "ai_numeric_count_diff",
        "opening_balance",
        "closing_balance",
        "transaction_count",
        "computed_vs_stated_diff",
        "balance_mismatch"
    ]

    feature_dict = {}

    float_keys = {
        "ai_word_similarity",
        "ai_numeric_match_ratio",
        "opening_balance",
        "closing_balance",
        "computed_vs_stated_diff",
    }
    int_keys = {
        "pdf_page_count",
        "extracted_text_chars",
        "transaction_count",
        "ai_numeric_count_diff",
        "balance_mismatch"
    }

    for key in expected_features:
        value = full_record.get(key)

        # Provide default if value is missing
        if value is None:
            if key in int_keys:
                value = 0
            elif key in float_keys:
                value = 0.0
            else:
                value = 0

        # Convert to correct type
        if key in int_keys:
            value = int(value)
        elif key in float_keys:
            value = float(value)

        feature_dict[key] = value

    return feature_dict

if __name__ == "__main__":
    
    # --- Config ---
    db_path = r"C:\Users\rokas\Documents\FinCheck\Versions\V5.4 Fixed Text Comp\statements_training.db"

    # --- Initialise classifier ---
    classifier = StatementClassifier(db_path)

    # --- Load and prepare labelled data ---
    df = classifier.load_data()
    X, y = classifier.preprocess_data(df)

    if len(X) == 0:
        print("No labelled data available for training.")
        exit()

    # --- Train the model ---
    classifier.train_model(X, y)

    # --- Retrieve JSON from SQLPreper ---
    sql_preper = SQLPreper()
    with open("output_logs/log.txt", "r", encoding="utf-8") as f:
        log_text = f.read()
    record_dict = sql_preper.parse_log_with_ai(log_text)
    #print("Raw content:", content_str)

    # Parse the JSON string into a Python dict
    #try:
        #record_dict = json.loads(content_str)
    #except json.JSONDecodeError as e:
        #print("Error parsing JSON from OpenAI content:", e)
        #record_dict = {}

    # --- Extract ML features from the record dict ---
    new_statement_features = extract_features_for_prediction(record_dict)

    # --- Predict label using the classifier ---
    predicted_label = classifier.predict_label(new_statement_features)
    label_name = "Legit" if predicted_label == 0 else "Fraudulent"
    print(f"\nFinal Prediction: {label_name} (Label: {predicted_label})")