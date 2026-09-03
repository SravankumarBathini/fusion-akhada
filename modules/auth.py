import logging

import streamlit as st
from utils.storage import _get_supabase_client
from infrastructure.registration_notifications import record_registration

logger = logging.getLogger(__name__)


def render_login_interface():
    st.markdown(
        """
        <style>
        .login-shell {
            max-width: 680px;
            margin: 2rem auto 0;
            padding: 2.5rem 2.75rem 2rem;
            border: 1px solid rgba(255, 138, 61, 0.28);
            border-radius: 24px;
            background: linear-gradient(145deg, rgba(32, 42, 61, 0.96), rgba(18, 24, 37, 0.98));
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
            text-align: center;
        }
        .login-mark {
            display: inline-block;
            margin-bottom: 0.75rem;
            padding: 0.55rem 0.8rem;
            border-radius: 14px;
            background: rgba(255, 138, 61, 0.14);
            font-size: 2.4rem;
        }
        .login-subtitle {
            color: #ffb27a;
            font-size: 1.05rem;
            letter-spacing: 0.04em;
        }
        .login-value {
            margin: 1.35rem auto 0;
            color: #cbd5e1;
            font-size: 0.98rem;
            line-height: 1.6;
        }
        </style>
        <div class="login-shell">
            <div class="login-mark">🏋️</div>
            <h1>Fusion Akhada</h1>
            <div class="login-subtitle">Ancient discipline. Modern performance.</div>
            <div class="login-value">
                Personalized training that brings Indian movement traditions
                together with modern strength and conditioning.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left_co, cent_co, last_co = st.columns([1, 2, 1])
    
    with cent_co:
        st.markdown(
            "<p style='text-align: center; color: #9aa8bd; font-size: 0.95em;'>"
            "Your training journey starts here.</p>",
            unsafe_allow_html=True,
        )
        st.warning(
            "Disclaimer: This app provides general fitness guidance, not medical advice. "
            "Consult a qualified professional before starting a new program, especially "
            "if you have an injury or medical condition. Stop if you feel pain, dizziness, "
            "or discomfort."
        )
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
