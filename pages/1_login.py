import streamlit as st

st.set_page_config(page_title="Login – Booth Dashboard", layout="centered")
st.title("🔐 Tamil Nadu Booth Dashboard – Login")

VALID_USERS = {"admin": "1234", "vinoth": "150"}

with st.form("login_form"):
    username = st.text_input("👤 Username / பயனர் பெயர்")
    password = st.text_input("🔑 Password / கடவுச்சொல்", type="password")
    submit = st.form_submit_button("Login / உள்நுழைய")

if submit:
    if username in VALID_USERS and VALID_USERS[username] == password:
        st.session_state["logged_in"] = True
        st.session_state["user"] = username
        st.success(f"Welcome {username}! Redirecting...")

        # ✅ Correct navigation to main file (one level up)
        st.switch_page("../Home.py")


    else:
        st.error("❌ Invalid username or password.")
