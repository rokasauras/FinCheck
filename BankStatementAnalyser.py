import re


class BankStatementAnalyser:
    """
    Responsible for determining if a PDF is a bank statement,
    extracting key info like business name, address, balances, and transactions,
    then reconciling the statement.
    """

    def __init__(self, text):
        self.text = text.lower()
        self.business_name = ""
        self.business_address = ""
        self.opening_balance = None
        self.closing_balance = None
        self.transactions = []

    def is_bank_statement(self):
        """
        Basic keyword-based classification.
        Adjust to your real data for better accuracy.
        """
        keywords = ["statement date", "account number", "balance", "sort code", "account summary"]
        found = sum(1 for kw in keywords if kw in self.text)
        return found >= 2  # Arbitrary threshold for MVP

    def extract_business_details(self):
        """
        Naive approach:
        - If you suspect the business name or address has certain patterns (e.g., "Ltd", "Address:"),
          adapt the logic or add advanced text parsing.
        """
        lines = self.text.splitlines()

        # Attempt to find business name (look for 'ltd' or 'plc' in the first 10 lines)
        for line in lines[:10]:
            if "ltd" in line or "plc" in line:
                self.business_name = line.strip()
                break

        # Attempt to find an address using a naive postcode regex (UK example)
        postcode_regex = re.compile(r"[A-Z]{1,2}\d[A-Z\d]?\s?\d[ABD-HJLNP-UW-Z]{2}", re.IGNORECASE)
        for i, line in enumerate(lines):
            if postcode_regex.search(line):
                # We'll assume 2 lines before & after might be the address
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                address_lines = lines[start:end]
                self.business_address = "\n".join(line.strip() for line in address_lines)
                break

    def extract_balances_and_transactions(self):
        """
        Find 'Opening Balance' and 'Closing Balance'.
        Then parse possible lines of transactions with naive regex.
        """
        # Regex to find lines like "Opening Balance: 1234.56"
        opening_pattern = re.compile(r"(opening\s+balance)\D+([\d,.]+)", re.IGNORECASE)
        closing_pattern = re.compile(r"(closing\s+balance)\D+([\d,.]+)", re.IGNORECASE)

        open_match = opening_pattern.search(self.text)
        if open_match:
            self.opening_balance = float(open_match.group(2).replace(",", ""))

        close_match = closing_pattern.search(self.text)
        if close_match:
            self.closing_balance = float(close_match.group(2).replace(",", ""))

        # Parse transactions. 
        # Example line: "01/03/2025 Payment to X -50.00" or "2025-03-01 Cheque #123 100.00"
        transaction_lines = self.text.split('\n')
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(.+?)\s+([+-]?[\d,\.]+)")

        for line in transaction_lines:
            match = txn_pattern.search(line)
            if match:
                date_str = match.group(1)
                desc = match.group(2)
                amt_str = match.group(3).replace(",", "")
                try:
                    amount = float(amt_str)
                except:
                    amount = 0.0
                self.transactions.append({
                    "date": date_str,
                    "description": desc.strip(),
                    "amount": amount
                })

    def reconcile_statement(self):
        """
        Check if Opening + sum of transactions = Closing
        """
        if self.opening_balance is None or self.closing_balance is None:
            return False  # Not enough info

        total_movement = sum(t["amount"] for t in self.transactions)
        expected_closing = self.opening_balance + total_movement
        # Allow small float difference
        return abs(expected_closing - self.closing_balance) < 0.01