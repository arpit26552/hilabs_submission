import subprocess, sys

# Step 1: run preprocessing
subprocess.run([sys.executable, "dedupe_providers.py"], check=True)
subprocess.run([sys.executable, "dashboard.py"], check=True)
subprocess.run([sys.executable, "verification.py"], check=True)
subprocess.run([sys.executable, "SQLite.py"], check=True)
subprocess.run([sys.executable, "preprocess_validation.py"], check=True)
subprocess.run(["streamlit", "run", "app.py"], check=True)
