"""Debug the _load_user_data function internally."""
import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Load User Data Debug", page_icon="🔬", layout="wide")

st.title("🔬 _load_user_data Internal Debug")

# Import after streamlit is configured
from infrastructure.storage import (
    _get_supabase_client, 
    is_supabase_available, 
    supabase_schema_ready,
    _profiles_support_user_id
)

st.header("Step 1: Authentication")

# Add login functionality
if "user" not in st.session_state:
    st.warning("🔐 Please log in to debug _load_user_data")
    
    client = _get_supabase_client()
    if not client:
        st.error("❌ Cannot create Supabase client for login")
        st.stop()
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your-email@example.com")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")
        
        if login_button:
            try:
                res = client.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["user"] = res.user
                if res.session is not None:
                    st.session_state["supabase_session"] = {
                        "access_token": res.session.access_token,
                        "refresh_token": res.session.refresh_token,
                    }
                st.success("✅ Logged in successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Login failed: {e}")
    st.stop()

st.header("Step 2: Replicate _load_user_data Logic")

if "user" in st.session_state:
    user = st.session_state["user"]
    # Handle both dict and User object
    if isinstance(user, dict):
        user_id = user.get("id")
    else:
        user_id = getattr(user, "id", None)
    
    st.info(f"Testing with user_id: {user_id}")
    
    # Step by step replication of _load_user_data logic
    st.subheader("Step 2.1: Check is_supabase_available()")
    available = is_supabase_available()
    st.write(f"is_supabase_available(): {available}")
    if not available:
        st.error("❌ This is why it returns 'unavailable'!")
        st.stop()
    
    st.subheader("Step 2.2: Check supabase_schema_ready()")
    schema_ready = supabase_schema_ready()
    st.write(f"supabase_schema_ready(): {schema_ready}")
    if not schema_ready:
        st.error("❌ This is why it returns 'unavailable'!")
        st.stop()
    
    st.subheader("Step 2.3: Check combined condition")
    combined = is_supabase_available() and supabase_schema_ready()
    st.write(f"Combined check: {combined}")
    if not combined:
        st.error("❌ Combined check failed - this is the problem!")
        st.stop()
    
    st.success("✅ All checks passed - should be able to proceed")
    
    st.subheader("Step 2.4: Call load_all_user_data_for()")
    try:
        from infrastructure.storage import load_all_user_data_for
        snapshot = load_all_user_data_for(user_id)
        
        if snapshot is None:
            st.error("❌ load_all_user_data_for returned None")
            st.stop()
        
        st.success("✅ load_all_user_data_for succeeded")
        st.write(f"Profile ID: {snapshot.get('profile_id')}")
        st.write(f"Profile exists: {bool(snapshot.get('profile'))}")
        
        # Now test the actual _load_user_data function
        st.subheader("Step 2.5: Call actual _load_user_data()")
        from application.data_loader import _load_user_data
        
        profile, workout_plan, workout_history, profile_id, storage_source = _load_user_data(
            user_id=user_id,
            _profile_file="unused",
            _workout_plan_file="unused",
            _workout_history_file="unused"
        )
        
        st.write(f"Storage source: {storage_source}")
        if storage_source == "unavailable":
            st.error("❌ _load_user_data still returns 'unavailable' despite all checks passing!")
        else:
            st.success("✅ _load_user_data worked correctly")
            
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.text(traceback.format_exc())