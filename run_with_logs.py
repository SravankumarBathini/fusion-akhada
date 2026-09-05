"""Run the main app with detailed logging."""
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

print("Starting app with detailed logging...")
print("Check the terminal output for _load_user_data debug logs")
print("Then go to http://localhost:8501 in your browser")

# Run the app
import streamlit as st
import subprocess

# Run streamlit with the app
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])