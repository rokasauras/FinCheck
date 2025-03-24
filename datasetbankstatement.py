import sqlite3

def main():
    db_path = "statements_training.db" 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a new table for storing the features of bank statements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS statement_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pdf_page_count INTEGER,
        pdf_title TEXT,
        pdf_author TEXT,
        pdf_creator TEXT,
        pdf_producer TEXT,
        pdf_creation_date TEXT,
        pdf_mod_date TEXT,
        extracted_text_chars INTEGER,
        ai_word_similarity REAL,
        ai_numeric_match_ratio REAL,
        ai_numeric_count_diff INTEGER,
        opening_balance REAL,
        closing_balance REAL,
        transaction_count INTEGER,
        computed_vs_stated_diff REAL,
        balance_mismatch INTEGER,
        label INTEGER DEFAULT NULL,
        scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cases = [
        # Legitimate Cases
        (61, "Verified_2024_Jan.pdf", "VeriBank", "Acrobat DC", "Adobe PDF Library", "D:20240105090000", "D:20240105100000", 2200, 0.96, 0.99, 0, 1800.00, 2000.00, 3, 0.00, 0, 0),
        (62, "Loan_Tracker.pdf", "LoanTrust", "Acrobat", "Distiller", "D:20240110083000", "D:20240110090000", 2100, 0.91, 0.97, 1, 250000.00, 249800.00, 5, 0.00, 0, 0),
        (63, "Daily_Usage.pdf", "EverydayBank", "Acrobat", "Distiller", "D:20240115093000", "D:20240115103000", 1800, 0.93, 1.00, 0, 325.00, 500.00, 6, 0.00, 0, 0),
        (64, "Home_Savings.pdf", "SafeHome", "PDFGen 5", "Adobe", "D:20231101080000", "D:20231101100000", 1600, 0.89, 0.98, 0, 10000.00, 10450.00, 4, 0.00, 0, 0),
        (65, "Payroll_Statement.pdf", "PayCorp", "Acrobat", "Distiller", "D:20240301090000", "D:20240301091500", 2050, 0.95, 1.00, 0, 3500.00, 3700.00, 2, 0.00, 0, 0),

        # Clear Fraud Cases
        (66, "Glitched_Data.pdf", "ScamCo", "DocEditor", "GhostWriter", "D:20230301000000", "D:20240301000000", 1200, 0.38, 0.25, 12, 100.00, 9200.00, 1, 9100.00, 1, 1),
        (67, "Empty_Body.pdf", "", "FakeGen", "PDFEdit", "D:20221201000000", "D:20221201000000", 0, 0.00, 0.00, 0, 0.00, 0.00, 0, 0.00, 1, 1),
        (68, "Balance_Conflict.pdf", "FraudulentBank", "ForgePro", "UnverifiedPDF", "D:20240101000000", "D:20240102000000", 1450, 0.49, 0.50, 4, 10.00, 9999.00, 1, 9989.00, 1, 1),
        (69, "Placeholder_Text.pdf", "TemplateCo", "BlankGen", "BlankDistiller", "D:20220101000000", "D:20230101000000", 1100, 0.20, 0.33, 6, 500.00, 10500.00, 2, 10000.00, 1, 1),
        (70, "Mismatch_Amounts.pdf", "FalseBank", "DocForge", "GhostLib", "D:20240115000000", "D:20240116000000", 1700, 0.60, 0.45, 8, 250.00, 7250.00, 2, 7000.00, 1, 1),

        # Edge/Unclear Cases
        (71, "Rounded_Balance.pdf", "TrustedCo", "Acrobat", "Distiller", "D:20240101000000", "D:20240101000000", 1850, 0.89, 0.90, 1, 1999.99, 2000.00, 1, 0.01, 0, 0),
        (72, "Transaction_Only.pdf", "SimpleBank", "Acrobat", "Adobe", "D:20240301000000", "D:20240301000000", 1440, 0.87, 0.91, 0, 0.00, 123.45, 1, 123.45, 0, 0),
        (73, "Silent_Fields.pdf", "NoMetaBank", "", "", "", "", 1450, 0.71, 0.72, 3, 300.00, 600.00, 1, 300.00, 1, 1),
        (74, "TyposInAmounts.pdf", "SloppyBank", "Acrobat", "Distiller", "D:20240101111111", "D:20240101111112", 1700, 0.69, 0.55, 7, 123.00, 789.00, 2, 666.00, 1, 1),
        (75, "Same_Opening_Closing.pdf", "StableBank", "Acrobat", "Distiller", "D:20240305000000", "D:20240305000000", 2000, 0.90, 0.95, 0, 900.00, 900.00, 0, 0.00, 0, 0),

        # Historical Edge Cases
        (76, "Archive_1999.pdf", "OldBank", "Acrobat 4", "Distiller 4", "D:19991201000000", "D:19991201000000", 1100, 0.80, 0.88, 2, 450.00, 950.00, 3, 500.00, 0, 0),
        (77, "Legacy_Structure.pdf", "Historic", "Acrobat 5", "Distiller", "D:20000201000000", "D:20000202000000", 950, 0.74, 0.79, 3, 600.00, 1000.00, 2, 400.00, 0, 0),
        (78, "Early_2000s_Format.pdf", "RetroBank", "OldGen", "OldLib", "D:20030301000000", "D:20030301000000", 1150, 0.81, 0.83, 1, 1200.00, 1200.00, 0, 0.00, 0, 0),
        (79, "OldTemplate_2005.pdf", "TemplateCorp", "DocGen", "Distiller", "D:20050505000000", "D:20050506000000", 1300, 0.70, 0.68, 4, 450.00, 1950.00, 3, 1500.00, 1, 1),
        (80, "Weird_Structure.pdf", "AbstractBank", "Unknown", "Unknown", "D:20240101101010", "D:20240101101011", 1800, 0.69, 0.72, 5, 300.00, 5000.00, 4, 4700.00, 1, 1),

        # Very Low Text or Noise
        (81, "GarbageText.pdf", "NoiseGen", "NoiseTool", "FakePDF", "D:20240201000000", "D:20240201000000", 100, 0.10, 0.00, 20, 0.00, 10000.00, 1, 10000.00, 1, 1),
        (82, "AllCapsText.pdf", "CapsBank", "AllCAPSGen", "Distiller", "D:20240205000000", "D:20240205000000", 1300, 0.40, 0.50, 6, 600.00, 1600.00, 2, 1000.00, 1, 1),
        (83, "NumbersOnly.pdf", "DigitsBank", "NumGen", "NumPDF", "D:20240208000000", "D:20240208000000", 1500, 0.30, 0.45, 9, 123.45, 9123.45, 1, 9000.00, 1, 1),
        (84, "AllMatchPerfect.pdf", "IdealBank", "Acrobat", "Adobe", "D:20240301000000", "D:20240301000000", 2400, 1.00, 1.00, 0, 1500.00, 1800.00, 3, 0.00, 0, 0),
        (85, "RealisticPattern.pdf", "AverageBank", "Acrobat", "Distiller", "D:20240305000000", "D:20240305000000", 2300, 0.89, 0.92, 1, 950.00, 1230.00, 4, 280.00, 0, 0)
    ]

    # Insert the sample data into the table
    cursor.executemany("""
        INSERT INTO statement_features (
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
            label
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cases)

    conn.commit()
    conn.close()

    print(f"Inserted {len(cases)} new sample rows into 'statement_features' table.")

if __name__ == "__main__":
    main()
