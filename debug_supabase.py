"""Streamlit-based Supabase diagnostic tool."""
import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Supabase Debug", page_icon="🔧", layout="wide")

st.title("🔧 Supabase Connection Diagnostic")

# Import after streamlit is configured
from config.secrets import get_secret
from infrastructure.storage import (
    _get_supabase_client,
    is_supabase_available,
    supabase_schema_ready,
    _profiles_support_user_id
)

# Check credentials
st.header("1. Credentials Check")
supabase_url = get_secret("SUPABASE_URL")
supabase_key = get_secret("SUPABASE_KEY")
supabase_service_role = get_secret("SUPABASE_SERVICE_ROLE_KEY")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Streamlit Secrets Status")
    if supabase_url:
        st.success(f"✅ SUPABASE_URL: {supabase_url[:30]}...")
    else:
        st.error("❌ SUPABASE_URL not found")
    
    if supabase_key:
        st.success(f"✅ SUPABASE_KEY: {supabase_key[:20]}...")
    else:
        st.error("❌ SUPABASE_KEY not found")
    
    if supabase_service_role:
        st.success(f"✅ SUPABASE_SERVICE_ROLE_KEY: {supabase_service_role[:20]}...")
    else:
        st.warning("⚠️ SUPABASE_SERVICE_ROLE_KEY not found (optional)")

with col2:
    st.subheader("Environment Variables")
    import os
    st.text(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'Not set')[:30]}...")
    st.text(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY', 'Not set')[:20]}...")

# Test client creation
st.header("2. Supabase Client Test")
client = _get_supabase_client()
if client:
    st.success("✅ Supabase client created successfully")
else:
    st.error("❌ Failed to create Supabase client")
    st.stop()

# Test connection
st.header("3. Connection Test")
try:
    # Try a simple query to test connection
    response = client.table("profiles").select("id").limit(1).execute()
    st.success("✅ Successfully connected to Supabase")
    st.info(f"Query result: {len(response.data)} profile(s) found")
except Exception as e:
    st.error(f"❌ Connection failed: {e}")
    st.stop()

# Schema check
st.header("4. Schema Check")
schema_ready = supabase_schema_ready()
if schema_ready:
    st.success("✅ Schema is ready (profiles.user_id column exists)")
else:
    st.error("❌ Schema not ready - profiles.user_id column missing")
    st.warning("Please run database/001_add_profile_ownership.sql in Supabase SQL Editor")

# Detailed schema check
st.header("5. Detailed Schema Check")
try:
    # Check if user_id column exists
    response = client.table("profiles").select("user_id").limit(1).execute()
    st.success("✅ profiles.user_id column exists and is accessible")
except Exception as e:
    st.error(f"❌ profiles.user_id column issue: {e}")

# Tables check
st.header("6. Required Tables Check")
tables = ["profiles", "workout_plans", "workout_history", "exercises"]
for table in tables:
    try:
        response = client.table(table).select("*").limit(1).execute()
        st.success(f"✅ Table '{table}' exists and is accessible")
    except Exception as e:
        st.error(f"❌ Table '{table}' issue: {e}")

# RLS Policies check
st.header("7. Row Level Security (RLS) Check")
try:
    # Try to query without user_id to see if RLS is blocking
    response = client.table("profiles").select("*").limit(1).execute()
    if response.data:
        st.warning("⚠️ RLS might not be properly configured - data returned without user filter")
    else:
        st.info("✅ RLS appears to be working (no data returned without user filter)")
except Exception as e:
    st.error(f"❌ RLS check failed: {e}")

# Authentication check
st.header("8. Authentication Check")
if "user" in st.session_state:
    user = st.session_state["user"]
    st.success(f"✅ User authenticated: {user.get('email', 'Unknown')}")
    user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    if user_id:
        st.info(f"User ID: {user_id}")
        
        # Try to query user's data
        try:
            response = client.table("profiles").select("*").eq("user_id", user_id).execute()
            if response.data:
                st.success(f"✅ Found {len(response.data)} profile(s) for this user")
            else:
                st.warning("⚠️ No profiles found for this user - you may need to create one")
        except Exception as e:
            st.error(f"❌ Failed to query user data: {e}")
    else:
        st.error("❌ No user ID found in session")
else:
    st.warning("⚠️ No user authenticated - this might be expected depending on your app flow")

st.header("Summary")
if is_supabase_available() and schema_ready:
    st.success("🎉 All critical checks passed! The issue might be elsewhere in the application logic.")
else:
    st.error("❌ Critical issues found. Please address the errors above.")