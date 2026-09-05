"""Clear Streamlit session state to force fresh login."""
import streamlit as st

st.set_page_config(page_title="Clear Session", page_icon="🧹", layout="centered")

st.title("🧹 Clear Session State")

st.write("This will clear your Streamlit session state and force a fresh login.")

if st.button("Clear Session State"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Session state cleared! Please go back to the main app.")
    st.info("The main app should now show the login interface.")

st.write("Current session state keys:", list(st.session_state.keys()))