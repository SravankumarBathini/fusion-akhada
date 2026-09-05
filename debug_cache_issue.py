"""Debug cache issue in data loading."""
import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Cache Debug", page_icon="💾", layout="wide")

st.title("💾 Cache Issue Debug")

# Import after streamlit is configured
from infrastructure.storage import load_all_user_data_for, is_supabase_available, supabase_schema_ready, _get_supabase_client

st.header("Step 1: Authentication")

# Add login functionality
if "user" not in st.session_state:
    st.warning("🔐 Please log in to debug cache issue")
    
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

st.header("Step 2: Clear Streamlit Cache")

if st.button("Clear Cache"):
    st.cache_data.clear()
    st.success("✅ Cache cleared!")
    st.rerun()

st.header("Step 3: Test Direct RPC (No Cache)")

if "user" in st.session_state:
    user = st.session_state["user"]
    # Handle both dict and User object
    if isinstance(user, dict):
        user_id = user.get("id")
    else:
        user_id = getattr(user, "id", None)
    
    st.info(f"Testing with user_id: {user_id}")
    
    # Test direct RPC (no cache)
    try:
        st.write("Calling load_all_user_data_for directly...")
        snapshot = load_all_user_data_for(user_id)
        
        if snapshot:
            st.success("✅ RPC succeeded!")
            st.write(f"Profile ID: {snapshot.get('profile_id')}")
            st.write(f"Profile exists: {bool(snapshot.get('profile'))}")
            st.write(f"Workout plan exists: {bool(snapshot.get('workout_plan'))}")
            st.write(f"Workout history entries: {len(snapshot.get('workout_history', []))}")
        else:
            st.error("❌ RPC returned None")
    except Exception as e:
        st.error(f"❌ RPC failed: {e}")
        import traceback
        st.text(traceback.format_exc())
        
    st.header("Step 4: Test Cached Function")
    
    # Now test the cached version
    from application.data_loader import _load_user_data
    
    try:
        st.write("Calling _load_user_data (cached function)...")
        profile, workout_plan, workout_history, profile_id, storage_source = _load_user_data(
            user_id=user_id,
            _profile_file="unused",
            _workout_plan_file="unused", 
            _workout_history_file="unused"
        )
        
        st.write(f"Storage source: {storage_source}")
        st.write(f"Profile loaded: {bool(profile)}")
        st.write(f"Profile ID: {profile_id}")
        st.write(f"Workout plan loaded: {bool(workout_plan)}")
        st.write(f"Workout history loaded: {len(workout_history) if workout_history else 0} entries")
        
        if storage_source == "unavailable":
            st.error("❌ Cached function returned 'unavailable' - this is the bug!")
        else:
            st.success("✅ Cached function worked correctly")
            
    except Exception as e:
        st.error(f"❌ Cached function failed: {e}")
        import traceback
        st.text(traceback.format_exc())
else:
    st.warning("Please log in first")