"""Check which secret sources are available."""
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from config.secrets import get_secret, load_dotenv_file
from config.settings import ENV_FILE

print("=== Secret Sources Check ===\n")

# Check Streamlit secrets
print("1. Checking Streamlit secrets...")
try:
    import streamlit as st
    print("   Streamlit is available")
    try:
        from streamlit import secrets
        print("   Streamlit secrets module is available")
        # Try to access secrets (this will only work in a Streamlit context)
        url = secrets.get("SUPABASE_URL", None)
        key = secrets.get("SUPABASE_KEY", None)
        print(f"   SUPABASE_URL from st.secrets: {url[:20] if url else 'None'}...")
        print(f"   SUPABASE_KEY from st.secrets: {key[:20] if key else 'None'}...")
    except Exception as e:
        print(f"   Cannot access st.secrets outside Streamlit context: {e}")
except ImportError:
    print("   Streamlit is not available")

# Check .env file
print(f"\n2. Checking .env file at: {ENV_FILE}")
env_values = load_dotenv_file(ENV_FILE)
if env_values:
    print(f"   .env file found with {len(env_values)} keys:")
    for key, value in env_values.items():
        if 'SECRET' in key.upper() or 'KEY' in key.upper() or 'TOKEN' in key.upper():
            print(f"     {key}: {value[:20]}...")
        else:
            print(f"     {key}: {value}")
else:
    print("   .env file not found or empty")

# Check environment variables
print("\n3. Checking environment variables...")
import os
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
print(f"   SUPABASE_URL from env: {supabase_url[:20] if supabase_url else 'None'}...")
print(f"   SUPABASE_KEY from env: {supabase_key[:20] if supabase_key else 'None'}...")

# Check what get_secret returns
print("\n4. Testing get_secret function...")
final_url = get_secret("SUPABASE_URL")
final_key = get_secret("SUPABASE_KEY")
print(f"   Final SUPABASE_URL: {final_url[:20] if final_url else 'None'}...")
print(f"   Final SUPABASE_KEY: {final_key[:20] if final_key else 'None'}...")