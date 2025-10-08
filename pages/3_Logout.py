import streamlit as st
import time

st.set_page_config(page_title="Logout – Booth Dashboard", layout="centered")

st.title("🚪 Logging out...")

# Clear session state completely
for key in list(st.session_state.keys()):
    del st.session_state[key]

st.success("✅ You have been logged out successfully!")
st.info("Redirecting to Login page...")

time.sleep(1.5)
st.switch_page("1_Login")  # redirect to login page
