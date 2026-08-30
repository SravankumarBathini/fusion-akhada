import streamlit as st
from utils.storage import _get_supabase_client

def render_login_interface():
    left_co, cent_co, last_co = st.columns([1, 2, 1])
    
    with cent_co:
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Personal Workout Trainer</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6B7280; font-size: 1.1em;'>Athletic Conditioning Gateway</p>", unsafe_allow_html=True)
        st.write("")
        
        tab1, tab2 = st.tabs(["Sign In to Dashboard", "Register New Account"])
        client = _get_supabase_client()
        
        if not client:
            st.error("⚠️ Database connection client unavailable. Verify environment credentials.")
            return

        with tab1:
            st.write("")
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="athlete@example.com")
                password = st.text_input("Account Password", type="password", placeholder="Enter your password")
                st.write("")
                submit = st.form_submit_button(label="Login", use_container_width=True)
                
                if submit:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        try:
                            res = client.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state["user"] = res.user
                            st.success("Authentication successful! Loading metrics...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Authentication Failed: {str(e)}")
                            
        with tab2:
            st.write("")
            with st.form("signup_form"):
                new_email = st.text_input("Email Address", placeholder="new_athlete@example.com")
                new_password = st.text_input("Create Strong Password", type="password", placeholder="Minimum 6 characters")
                st.write("")
                submit_signup = st.form_submit_button(label="Create Account", use_container_width=True)
                
                if submit_signup:
                    if not new_email or not new_password:
                        st.error("Please provide both email and password values.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        try:
                            res = client.auth.sign_up({"email": new_email, "password": new_password})
                            st.info("Registration email transmitted! Check your inbox to confirm your profile.")
                        except Exception as e:
                            st.error(f"Registration Error: {str(e)}")
