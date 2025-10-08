import streamlit as st

def logout_button():
    """Reusable logout button that clears session and returns to login page."""
    with st.sidebar:
        st.markdown("---")
        if st.button("Logout"):
            for key in ["logged_in", "user", "district", "constituency", "district_data"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Logged out successfully!")
            st.switch_page("1_Login")
