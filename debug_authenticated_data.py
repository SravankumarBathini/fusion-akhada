"""Debug data loading with authenticated user context."""
import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Authenticated Data Debug", page_icon="🔐", layout="wide")

st.title("🔐 Authenticated User Data Debug")

# Import after streamlit is configured
from infrastructure.storage import (
    _get_supabase_client, 
    is_supabase_available, 
    supabase_schema_ready,
    load_all_user_data_for
)
from application.data_loader import load_persistent_data

st.header("Step 1: Authentication")

# Add login functionality to this diagnostic
if "user" not in st.session_state:
    st.warning("🔐 Please log in to debug authenticated data loading")
    
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

user = st.session_state["user"]
# Handle both dict and User object
if isinstance(user, dict):
    email = user.get('email', 'Unknown')
    user_id = user.get("id")
else:
    email = getattr(user, 'email', 'Unknown')
    user_id = getattr(user, "id", None)

st.success(f"✅ User authenticated: {email}")
st.info(f"User ID: {user_id}")

# Check session
if "supabase_session" in st.session_state:
    session = st.session_state["supabase_session"]
    st.success(f"✅ Session exists with access_token: {session.get('access_token', 'None')[:20]}...")
else:
    st.warning("⚠️ No supabase_session in session_state")

st.header("Step 2: Check Supabase Status")

supabase_available = is_supabase_available()
schema_ready = supabase_schema_ready()

st.write(f"Supabase Available: {supabase_available}")
st.write(f"Schema Ready: {schema_ready}")

if not (supabase_available and schema_ready):
    st.error("❌ Supabase not ready - this is the problem!")
    st.stop()

st.header("Step 3: Test Direct Data Loading")

client = _get_supabase_client()
if client:
    st.success("✅ Supabase client created")
    
    # Test if we can query profiles for this user
    try:
        st.write("Testing profiles query for user_id...")
        response = client.table("profiles").select("*").eq("user_id", user_id).execute()
        st.write(f"Profiles found: {len(response.data)}")
        
        if response.data:
            for profile in response.data:
                st.write(f"Profile ID: {profile.get('id')}, Name: {profile.get('name')}")
        else:
            st.warning("⚠️ No profiles found for this user - you may need to create one")
    except Exception as e:
        st.error(f"❌ Error querying profiles: {e}")
        import traceback
        st.text(traceback.format_exc())
else:
    st.error("❌ Could not create Supabase client")

st.header("Step 4: Test Application Data Loading")

try:
    st.write("Calling load_persistent_data with user_id...")
    profile, workout_plan, workout_history, exercise_database, profile_id, storage_source = load_persistent_data(
        user_id=user_id,
        warning_callback=st.warning
    )
    
    st.write(f"Storage source: {storage_source}")
    st.write(f"Profile loaded: {bool(profile)}")
    st.write(f"Profile ID: {profile_id}")
    st.write(f"Workout plan loaded: {bool(workout_plan)}")
    st.write(f"Workout history loaded: {len(workout_history) if workout_history else 0} entries")
    
    if storage_source == "supabase":
        st.success("✅ Data loaded from Supabase successfully - this should work in main app!")
    elif storage_source == "unavailable":
        st.error("❌ Storage source is 'unavailable' - this is exactly the error you're seeing!")
        st.error("The main app will show the error message when storage_source != 'supabase'")
    else:
        st.warning(f"⚠️ Unexpected storage source: {storage_source}")
        
except Exception as e:
    st.error(f"❌ Error during data loading: {e}")
    import traceback
    st.text(traceback.format_exc())

st.header("Step 5: Test RPC Function (if available)")

try:
    st.write("Testing get_user_snapshot RPC...")
    snapshot = load_all_user_data_for(user_id)
    if snapshot:
        st.success("✅ RPC call succeeded")
        st.write(f"Profile ID from RPC: {snapshot.get('profile_id')}")
        st.write(f"Profile from RPC: {bool(snapshot.get('profile'))}")
    else:
        st.warning("⚠️ RPC call returned None - function might not be installed")
except Exception as e:
    st.warning(f"⚠️ RPC call failed (expected if not installed): {e}")