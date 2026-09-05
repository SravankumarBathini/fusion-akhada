"""Diagnostic script to check Supabase connection and schema status."""
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from config.secrets import get_secret
from infrastructure.storage import _get_supabase_client, is_supabase_available, supabase_schema_ready

def test_supabase_connection():
    """Test Supabase connection and schema."""
    print("=== Supabase Connection Diagnostic ===\n")
    
    # Check credentials
    print("1. Checking credentials...")
    supabase_url = get_secret("SUPABASE_URL")
    supabase_key = get_secret("SUPABASE_KEY")
    
    if not supabase_url:
        print("   [X] SUPABASE_URL is not configured")
        return False
    if not supabase_key:
        print("   [X] SUPABASE_KEY is not configured")
        return False
    
    print(f"   [OK] SUPABASE_URL: {supabase_url[:30]}...")
    print(f"   [OK] SUPABASE_KEY: {supabase_key[:20]}...")
    
    # Check client creation
    print("\n2. Testing Supabase client creation...")
    client = _get_supabase_client()
    if client is None:
        print("   [X] Failed to create Supabase client")
        return False
    print("   [OK] Supabase client created successfully")
    
    # Check availability
    print("\n3. Checking Supabase availability...")
    if not is_supabase_available():
        print("   [X] Supabase is not available")
        return False
    print("   [OK] Supabase is available")
    
    # Check schema readiness
    print("\n4. Checking schema readiness (profiles.user_id column)...")
    if not supabase_schema_ready():
        print("   [X] Schema is not ready - profiles.user_id column is missing")
        print("   [!] Please run database/001_add_profile_ownership.sql in Supabase SQL Editor")
        return False
    print("   [OK] Schema is ready")
    
    # Check tables exist
    print("\n5. Checking if required tables exist...")
    tables_to_check = ["profiles", "workout_plans", "workout_history", "exercises"]
    for table in tables_to_check:
        try:
            response = client.table(table).select("*").limit(1).execute()
            print(f"   [OK] Table '{table}' exists")
        except Exception as e:
            print(f"   [X] Table '{table}' does not exist or is not accessible: {e}")
            return False
    
    print("\n=== All checks passed! ===")
    return True

if __name__ == "__main__":
    try:
        success = test_supabase_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)