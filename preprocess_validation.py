import pandas as pd

FILE = "roster_with_validations.csv"

# Load the file (read everything as string to avoid dtype issues)
df = pd.read_csv(FILE, dtype=str).fillna("")

# Function to lowercase only text values
def safe_lower(val):
    if pd.isna(val):
        return ""
    val_str = str(val)
    # If it's purely numeric, keep as-is
    if val_str.replace(".", "", 1).isdigit():
        return val_str
    return val_str.lower().strip()

# Apply to all columns
for col in df.columns:
    df[col] = df[col].map(safe_lower)

# Overwrite the same file
df.to_csv(FILE, index=False)

# print(f"✅ Saved normalized file: {FILE}")
