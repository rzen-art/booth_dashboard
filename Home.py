import streamlit as st
import pandas as pd

# ---------------------------------------------------------------
# Page Setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Booth Dashboard – Select District", layout="wide")
st.title("🗳️ Tamil Nadu Booth Dashboard")

# 🚨 Access Control
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Please login to continue.")
    st.page_link("1_Login", label="🔐 Go to Login Page")
    st.stop()

# ---------------------------------------------------------------
# District–Constituency Mapping
# ---------------------------------------------------------------
district_data = pd.DataFrame([
    ["Ariyalur", "Jayankondam", "2019AC150MP.csv", "2021AC150MLA.csv", "2024AC150MP.csv"],
    ["Ariyalur", "Ariyalur", "2019AC149MP.csv", "2021AC149MLA.csv", "2024AC149MP.csv"],
], columns=["District", "Constituency", "2019", "2021", "2024"])

districts = sorted(district_data["District"].unique())
district = st.selectbox("📍 Select District / மாவட்டம்", districts)

if district:
    constituencies = sorted(
        district_data[district_data["District"] == district]["Constituency"].unique()
    )
    constituency = st.selectbox("🏛️ Select Constituency / தொகுதி", constituencies)
else:
    constituency = None

# ---------------------------------------------------------------
# Go to Booth Analysis
# ---------------------------------------------------------------
if constituency:
    if st.button("➡ Go to Booth Analysis / பூத் பகுப்பாய்வு பக்கத்திற்கு செல்ல"):
        st.session_state["district"] = district
        st.session_state["constituency"] = constituency
        st.session_state["district_data"] = district_data.to_dict()
        st.switch_page("2_Booth_Analysis")

# ---------------------------------------------------------------
# Sidebar Logout
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    if st.button("Logout"):
        st.switch_page("3_Logout")
