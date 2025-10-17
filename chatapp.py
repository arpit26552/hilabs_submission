# chatbot/chatapp.py
import sqlite3
import pandas as pd
import os
from queries import parse_query

class NL2SQLConverter:
    def __init__(self, db_path: str, csv_path: str = None):
        """
        Initialize the NL2SQL converter with a SQLite database path.
        If csv_path is provided, load CSV data into the roster table if it's empty.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

        if csv_path:
            self.ensure_roster_table(csv_path)

        self.columns = self.get_table_columns()

    def ensure_roster_table(self, csv_path: str):
        """Create 'roster' table from CSV if it doesn't exist or is empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roster'")
        table_exists = cursor.fetchone()

        if not table_exists:
            print("⚠️ Roster table not found. Creating from CSV...")
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            df.to_sql("roster", self.conn, if_exists="replace", index=False)
            print("✅ Roster table created.")
        else:
            # Check if table is empty
            cursor.execute("SELECT COUNT(*) FROM roster")
            count = cursor.fetchone()[0]
            if count == 0:
                print("⚠️ Roster table is empty. Loading from CSV...")
                df = pd.read_csv(csv_path, dtype=str).fillna("")
                df.to_sql("roster", self.conn, if_exists="replace", index=False)
                print("✅ Roster table populated from CSV.")

    def get_table_columns(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(roster)")
        return [col[1] for col in cursor.fetchall()]

    def execute_nl_query(self, natural_language_query: str):
        sql_query = parse_query(natural_language_query)
        try:
            df = pd.read_sql_query(sql_query, self.conn)
            if df.shape == (1, 1):  # aggregate result (COUNT, AVG, etc.)
                return df.iloc[0, 0], sql_query
            return df, sql_query
        except Exception as e:
            return None, f"Error executing query: {str(e)}"

    def close(self):
        self.conn.close()


# ✅ Example usage (run chatbot standalone)
if __name__ == "__main__":
    db_file = "roster.db"
    csv_file = os.path.join("data", "provider_roster_with_errors.csv")

    converter = NL2SQLConverter(db_path=db_file, csv_path=csv_file)

    while True:
        user_query = input("Ask me about providers (or type 'exit'): ")
        if user_query.lower() in ["exit", "quit"]:
            break

        result, sql_or_error = converter.execute_nl_query(user_query)
        print("Generated SQL:", sql_or_error)

        if isinstance(result, pd.DataFrame):
            print(result.head())
        else:
            print("Result:", result)

    converter.close()
