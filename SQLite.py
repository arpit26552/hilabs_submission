import sqlite3
import pandas as pd
import os

def csv_to_sqlite(csv_file, db_file="roster.db", table_name="roster"):
    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file '{csv_file}' not found!")

    # Load CSV into pandas DataFrame
    df = pd.read_csv(csv_file)
    
    # Connect to SQLite (creates file if it doesn’t exist)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Drop table if it already exists (optional, ensures fresh load)
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Write DataFrame to SQLite
    df.to_sql(table_name, conn, index=False, if_exists="replace")

    conn.commit()
    conn.close()
    print(f"✅ Data from '{csv_file}' has been loaded into '{db_file}' (table: {table_name})")

def run_query(db_file="roster.db", query="SELECT * FROM roster LIMIT 5;"):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Print column names + data
    col_names = [description[0] for description in cursor.description]
    print("Columns:", col_names)
    for row in rows:
        print(row)
    
    conn.close()

if __name__ == "__main__":
    # Example usage
    csv_file = "roster_with_validations.csv"  # received at runtime
    db_file = "roster.db"
    csv_to_sqlite(csv_file, db_file)
    # run_query(db_file, "SELECT COUNT(*) as total_rows FROM roster;")
    # run_query(db_file,"SELECT full_name, years_in_practice, license_number, license_expiration FROM roster WHERE years_in_practice > 20 AND license_expiration < '2026-01-01';")
    