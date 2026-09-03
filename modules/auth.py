import logging

import streamlit as st
from utils.storage import _get_supabase_client
from infrastructure.registration_notifications import record_registration

logger = logging.getLogger(__name__)


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
                            if res.session is not None:
                                st.session_state["supabase_session"] = {
                                    "access_token": res.session.access_token,
                                    "refresh_token": res.session.refresh_token,
                                }
                            logger.info("Authentication succeeded")
                            st.success("Authentication successful! Loading metrics...")
                            st.rerun()
                        except Exception as e:
                            logger.warning("Authentication failed: %s", e)
                            st.error("Authentication failed. Check your email and password.")
                            
        with tab2:
            st.write("")
            with st.form("signup_form"):
                new_email = st.text_input("Email Address", placeholder="new_athlete@example.com")
                new_password = st.text_input("Create Strong Password", type="password", placeholder="Minimum 12 characters")
                st.write("")
                submit_signup = st.form_submit_button(label="Create Account", use_container_width=True)
                
                if submit_signup:
                    if not new_email or not new_password:
                        st.error("Please provide both email and password values.")
                    elif len(new_password) < 12:
                        st.error("Password must be at least 12 characters long.")
                    else:
                        try:
                            res = client.auth.sign_up({"email": new_email, "password": new_password})
                            user_id = getattr(res.user, "id", None) if res.user else None
                            try:
                                record_registration(new_email.strip().lower(), user_id)
                            except Exception as error:
                                logger.exception("Registration audit failed: %s", error)
                            logger.info("Account registration requested")
                            st.info("Registration email transmitted! Check your inbox to confirm your profile.")
                        except Exception as e:
                            logger.warning("Account registration failed: %s", e)
                            st.error("Registration failed. Please verify your details and try again.")
