"""Debug data loading in the main app context."""
import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Data Loading Debug", page_icon="🔍", layout="wide")

st.title("🔍 Data Loading Debug")

# Import after streamlit is configured
from infrastructure.storage import is_supabase_available, supabase_schema_ready
from application.data_loader import load_persistent_data

st.header("Storage Status Check")

# Check Supabase availability
supabase_available = is_supabase_available()
st.write(f"Supabase Available: {supabase_available}")

# Check schema readiness  
schema_ready = supabase_schema_ready()
st.write(f"Schema Ready: {schema_ready}")

if supabase_available and schema_ready:
    st.success("✅ Both checks passed - should be able to load from Supabase")
else:
    st.error("❌ One or more checks failed")
    if not supabase_available:
        st.error("Supabase is not available")
    if not schema_ready:
        st.error("Schema is not ready")

st.header("Data Loading Test")

# Test data loading with a dummy user_id
test_user_id = "test-user-id"
st.write(f"Testing data loading with user_id: {test_user_id}")

try:
    profile, workout_plan, workout_history, exercise_database, profile_id, storage_source = load_persistent_data(
        user_id=test_user_id,
        warning_callback=st.warning
    )
    
    st.write(f"Storage source: {storage_source}")
    st.write(f"Profile loaded: {bool(profile)}")
    st.write(f"Profile ID: {profile_id}")
    st.write(f"Workout plan loaded: {bool(workout_plan)}")
    st.write(f"Workout history loaded: {len(workout_history) if workout_history else 0} entries")
    st.write(f"Exercise database loaded: {len(exercise_database) if exercise_database else 0} exercises")
    
    if storage_source == "supabase":
        st.success("✅ Data loaded from Supabase successfully")
    elif storage_source == "unavailable":
        st.error("❌ Storage source is 'unavailable' - this is the problem!")
    else:
        st.warning(f"⚠️ Unexpected storage source: {storage_source}")
        
except Exception as e:
    st.error(f"❌ Error during data loading: {e}")
    import traceback
    st.text(traceback.format_exc())

st.header("Session State Check")
st.write("Current session state keys:", list(st.session_state.keys()))
if "user" in st.session_state:
    st.write("User in session_state:", st.session_state["user"])
else:
    st.write("No user in session_state")