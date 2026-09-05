"""Check if secrets.toml file has valid format."""
import sys
from pathlib import Path

secrets_file = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"

print(f"Checking secrets file: {secrets_file}")
print(f"File exists: {secrets_file.exists()}")

if secrets_file.exists():
    try:
        content = secrets_file.read_text(encoding="utf-8")
        print(f"\nFile size: {len(content)} bytes")
        print("\nFile content (first 500 chars):")
        print(content[:500])
        
        # Check for common issues
        print("\n\nChecking for common issues:")
        
        # Check for quotes around values
        if 'SUPABASE_URL =' in content:
            print("[OK] SUPABASE_URL is defined")
        else:
            print("[X] SUPABASE_URL is not defined")
            
        if 'SUPABASE_KEY =' in content:
            print("[OK] SUPABASE_KEY is defined")
        else:
            print("[X] SUPABASE_KEY is not defined")
            
        # Check for placeholder values
        if "your-project.supabase.co" in content or "your-supabase-anon-key" in content:
            print("[X] Contains placeholder values - needs real credentials")
        else:
            print("[OK] Does not contain obvious placeholder values")
            
    except Exception as e:
        print(f"Error reading file: {e}")
else:
    print("File does not exist!")