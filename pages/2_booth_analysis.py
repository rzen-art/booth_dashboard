# pages/booth_analysis.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict
import numpy as np
import tempfile, os, base64, time, re

import json


# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Booth Analysis", layout="wide")

# Require district & constituency from Home page
if "district" not in st.session_state or "constituency" not in st.session_state:
    st.error("⚠️ Please go back to the Dashboard page and select District & Constituency.")
    st.stop()

district = st.session_state["district"]
constituency = st.session_state["constituency"]
district_data = pd.DataFrame(st.session_state["district_data"])

st.title(f"🗳️ Booth Analysis – {district} District, {constituency} Constituency")
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# 🔐 Constituency-level Password Protection (Strict Enforcement)
# ---------------------------------------------------------------


passwords_file = os.path.join(os.path.dirname(__file__), "..", "data", "passwords.json")
passwords_file = os.path.abspath(passwords_file)

# Load password list safely
try:
    with open(passwords_file, "r") as f:
        passwords = json.load(f)
except Exception as e:
    st.error(f"❌ Cannot read passwords.json: {e}")
    st.stop()

# Expected password for selected constituency
expected_password = passwords.get(district, {}).get(constituency, None)

# If constituency is protected
if expected_password:
    # If not already unlocked in session
    if not st.session_state.get(f"unlocked_{district}_{constituency}", False):
        st.warning(f"🔒 Access to **{constituency}** constituency requires a password.")
        entered_password = st.text_input("Enter Constituency Password:", type="password")
        
        if st.button("🔓 Unlock Constituency"):
            if entered_password == expected_password:
                st.session_state[f"unlocked_{district}_{constituency}"] = True
                st.success("✅ Access granted! Loading booth data...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Incorrect password. Access denied.")
                st.stop()
        else:
            st.stop()  # ❗ Block CSV loading until button is pressed
else:
    # Constituency not protected, allow access
    st.session_state[f"unlocked_{district}_{constituency}"] = True

# Load CSV files for the constituency
# ---------------------------------------------------------------
if not st.session_state.get(f"unlocked_{district}_{constituency}", False):
    st.error("🔐 You must unlock this constituency before accessing data.")
    st.stop()

# File list (provided by Home page mapping)
# ---------------------------------------------------------------
row = district_data[
    (district_data["District"] == district) &
    (district_data["Constituency"] == constituency)
].iloc[0]

file_list = [
    ("2019", row["2019"]),
    ("2021", row["2021"]),
    ("2024", row["2024"]),
]

# ---------------------------------------------------------------
# Alliances & Colors
# ---------------------------------------------------------------
ALLIANCES_BY_YEAR = {
    "2019": {
        "AIADMK+ALLIANCE": ["AIADMK", "BJP", "PMK", "DMDK"],
        "DMK+ALLIANCE": ["DMK", "INC", "VCK", "CPI", "CPI(M)", "MDMK"],
        "NTK": ["NTK"],
    },
    "2021": {
        "AIADMK+ALLIANCE": ["AIADMK", "BJP", "PMK"],
        "DMK+ALLIANCE": ["DMK", "INC", "VCK", "CPI", "CPI(M)", "MDMK"],
        "NTK": ["NTK"],
    },
    "2024": {
        "AIADMK+ALLIANCE": ["AIADMK", "PMK"],
        "BJP+ALLIANCE": ["BJP", "IJK"],
        "DMK+ALLIANCE": ["DMK", "INC", "VCK", "CPI(M)"],
        "NTK": ["NTK"],
    },
}

party_color_map = {
    "DMK": "#d62728",
    "AIADMK": "#2ca02c",
    "BJP": "#ff9933",
    "PMK": "#d3ff0e",
    "INC": "#00bfff",
    "VCK": "#1f77b4",
    "NTK": "#9467bd",
    "OTHERS": "#c0c0c0",
    "NOTA": "#808080"
}

alliance_colors = {
    "DMK+ALLIANCE": party_color_map["DMK"],
    "AIADMK+ALLIANCE": party_color_map["AIADMK"],
    "BJP+ALLIANCE": party_color_map["BJP"],
    "NTK": party_color_map["NTK"],
    "NOTA": party_color_map["NOTA"],
    "OTHERS": party_color_map["OTHERS"]
}

# ---------------------------------------------------------------
# Helpers (robust)
# ---------------------------------------------------------------
def auto_detect_separator(file_path):
    try:
        df_comma = pd.read_csv(file_path, sep=",", nrows=10, dtype=str, header=None)
        df_tab = pd.read_csv(file_path, sep="\t", nrows=10, dtype=str, header=None)
        return "\t" if df_tab.shape[1] > df_comma.shape[1] else ","
    except Exception:
        return ","


def load_clean_csv(file_path):
    """
    Robust loader:
    - auto-detects separator
    - finds header row (SL. NO & POLLING)
    - builds column names
    - ensures unique column names (avoids duplicate-label DataFrame access)
    - converts numeric columns safely
    - extracts BoothGroup reliably (falls back to index if missing)
    Returns: df, candidate_columns_list, polling_col (or None)
    """
    sep = auto_detect_separator(file_path)
    df_raw = pd.read_csv(file_path, sep=sep, header=None, dtype=str, keep_default_na=False)

    # detect header row (more tolerant)
    header_row = None
    for i in range(min(30, len(df_raw))):
        row_text = " ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if (("SL. NO" in row_text) or ("SL NO" in row_text) or ("SL." in row_text)) and ("POLL" in row_text):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"Header not found in {file_path}")

    candidate_row = header_row + 1

    # build column names from header & candidate name row (like your original logic)
    cols = []
    for j in range(df_raw.shape[1]):
        hdr = str(df_raw.iloc[header_row, j]).strip()
        cand = str(df_raw.iloc[candidate_row, j]).strip() if candidate_row < len(df_raw) else ""
        if j < 2:
            cols.append(hdr or cand or f"col_{j}")
        else:
            # prefer candidate name if it's non-numeric (usual case)
            cols.append(cand if (cand and not cand.isdigit()) else (hdr or cand or f"col_{j}"))

    # get data rows after candidate row
    df = df_raw.iloc[candidate_row + 1 :].reset_index(drop=True).copy()
    df.columns = cols

    # make column names unique to prevent df['name'] returning DataFrame if duplicates exist
    counts = defaultdict(int)
    uniq_cols = []
    for c in df.columns:
        counts[c] += 1
        if counts[c] > 1:
            uniq_cols.append(f"{c}__dup{counts[c]-1}")
        else:
            uniq_cols.append(c)
    df.columns = uniq_cols

    # drop empty / SL. NO blanks
    if "SL. NO." in df.columns:
        df = df[df["SL. NO."].astype(str).str.strip() != ""].reset_index(drop=True)

    # find a polling column (first match)
    polling_candidates = [c for c in df.columns if "polling" in c.lower()]
    polling_col = polling_candidates[0] if polling_candidates else None

    # numeric columns detection: everything except SL. NO. and polling col
    numeric_cols = [c for c in df.columns if c not in ["SL. NO.", polling_col]]

    # convert numeric columns robustly (string -> remove commas/spaces -> to_numeric)
    for c in numeric_cols:
        s = df[c].astype(str)
        s = s.str.replace(",", "", regex=False).str.replace(" ", "", regex=False)
        # replace blank-only strings with "0"
        s = s.where(s.str.strip() != "", "0")
        s = s.replace("nan", "0")
        df[c] = pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

    # extract booth number safely (always operate on a Series)
    if polling_col is not None:
        ser = df[polling_col]
        # If multiple columns share same label (shouldn't after uniq), make sure we have a Series:
        if isinstance(ser, pd.DataFrame):
            ser = ser.iloc[:, 0].astype(str)
        else:
            ser = ser.astype(str)
        # extract numeric prefix if present, otherwise keep whole string
        extracted = ser.str.extract(r"(\d+)", expand=False)
        df["BoothGroup"] = extracted.fillna(ser)
    else:
        # fallback: use row index as booth
        df["BoothGroup"] = (df.index + 1).astype(str)

    # Candidate columns = numeric columns excluding any "TOTAL"/"TURNOVER" columns
    exclude_keywords = ["TOTAL", "TURNOVER"]
    candidate_cols = [c for c in numeric_cols if not any(k in c.upper() for k in exclude_keywords)]

    return df, candidate_cols, polling_col




def get_alliance(party, year):
    alliances = ALLIANCES_BY_YEAR.get(str(year), {})
    for alliance, members in alliances.items():
        if party.upper() in [m.upper() for m in members]:
            return alliance
    return "OTHERS"


# ---------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------
def booth_pie_comparison(booth_number, all_data):
    alliance_trend = {}

    

    for year, info in sorted(all_data.items(), key=lambda x: int(x[0])):
        df = info["data"]
        candidate_cols = info["candidates"]
        polling_col = info.get("polling_col", None)

        booth_df = df[df["BoothGroup"].astype(str) == str(booth_number)]
        if booth_df.empty:
            st.warning(f"No data found for Booth {booth_number} in {year}")
            continue

        # sum candidate votes safely
        votes = booth_df[candidate_cols].apply(pd.to_numeric, errors="coerce").sum().astype(int)
        votes = votes[votes > 0]  # remove zeros

        # group into alliances (NOTA kept separately)
        alliance_votes = {}
        for name, val in votes.items():
            normalized = name.upper().replace("__DUP", "").strip()
            if normalized == "NOTA":
                alliance = "NOTA"
            else:
                alliance = get_alliance(name, year)
            alliance_votes[alliance] = alliance_votes.get(alliance, 0) + int(val)

        alliance_series = pd.Series(alliance_votes).sort_values(ascending=False)
        total_votes = int(alliance_series.sum())
        if total_votes == 0:
            st.warning(f"No vote values found for Booth {booth_number} in {year}")
            continue

        # If CSV also contains a "TOTAL VOTES" column, prefer it for turnout; else use total_votes
        total_votes_col = next((c for c in df.columns if "TOTAL" in c.upper() and ("VOTE" in c.upper() or "POLL" in c.upper())), None)
        total_voters_col = next((c for c in df.columns if any(k in c.upper() for k in ["TURNOVER", "REGISTERED", "ELECTORS", "TOTAL VOTERS"])), None)

        polled_votes = int(booth_df[total_votes_col].sum()) if total_votes_col else total_votes
        total_voters = int(booth_df[total_voters_col].sum()) if total_voters_col else polled_votes
        turnout_pct = round((polled_votes / total_voters) * 100, 2) if total_voters else 0

        winner = alliance_series.index[0]
        runner_up = alliance_series.index[1] if len(alliance_series) > 1 else None
        runner_up_votes = alliance_series.iloc[1] if len(alliance_series) > 1 else 0
        margin_votes = int(alliance_series.iloc[0] - runner_up_votes)
        margin_pct = round((margin_votes / polled_votes) * 100, 2) if polled_votes else 0

        # Summary box
        st.markdown(
            f"""
            <div style="text-align:center; font-size:16px; border:1px solid #ddd; border-radius:8px;
                        background:#fafafa; padding:10px; margin-bottom:10px;">
                🗳️ <b>{year} Election Summary</b><br>
                🏆 <b>Winning Alliance:</b> {winner}<br>
                📊 <b>Margin:</b> {margin_votes:,} votes ({margin_pct:.2f}%)<br>
                🗳️ <b>Total Votes Polled:</b> {polled_votes:,}<br>
                🎯 <b>Turnout:</b> {turnout_pct:.1f}%
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show pie chart (OTHERS grouped already in alliance mapping)
        colors = [alliance_colors.get(a, "#cccccc") for a in alliance_series.index]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=alliance_series.index,
                    values=alliance_series.values,
                    hole=0.35,
                    marker=dict(colors=colors, line=dict(color="white", width=2)),
                    texttemplate="%{label}<br>%{percent:.1%} (%{value:,} votes)",
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(title=dict(text=f"<b>{year} Election – Booth {booth_number}</b>", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

        # store for multi-year trend
        alliance_trend[year] = (alliance_series / alliance_series.sum()) * 100

    # Multi-year chart & booth history at the end
    if alliance_trend:
        alliance_df = pd.DataFrame(alliance_trend).fillna(0).T
        main_alliances = ["DMK+ALLIANCE", "AIADMK+ALLIANCE", "BJP+ALLIANCE", "NTK", "NOTA"]
        alliance_df["OTHERS"] = alliance_df.drop(columns=[c for c in alliance_df.columns if c in main_alliances], errors="ignore").sum(axis=1)
        # reorder: keep majors then OTHERS
        remain = [c for c in main_alliances if c in alliance_df.columns] + ["OTHERS"]
        alliance_df = alliance_df[[c for c in remain if c in alliance_df.columns]]

        # bar chart
        fig_bar = go.Figure()
        for alliance in alliance_df.columns:
            fig_bar.add_trace(
                go.Bar(
                    x=alliance_df.index,
                    y=alliance_df[alliance],
                    name=alliance,
                    marker_color=alliance_colors.get(alliance, "#cccccc"),
                    text=[f"{v:.1f}%" for v in alliance_df[alliance]],
                    textposition="outside",
                )
            )
        fig_bar.update_layout(title=dict(text=f"<b>📊 Multi-Year Comparison (2019–2024) – Booth {booth_number}</b>", x=0.5),
                              barmode="group", xaxis_title="Election Year", yaxis_title="Vote Share (%)")
        st.plotly_chart(fig_bar, use_container_width=True)

        # Booth historical summary
        avg_shares = alliance_df.mean().sort_values(ascending=False)
        dominant = avg_shares.index[0]
        volatility = alliance_df.diff().abs().mean().mean()
        last_votes = alliance_df.iloc[-1].sort_values(ascending=False)
        polarization_index = float(last_votes.iloc[0] - (last_votes.iloc[1] if len(last_votes) > 1 else 0))

        if avg_shares[dominant] >= 65:
            strength = "💪 Very Strong Booth"
        elif avg_shares[dominant] >= 55:
            strength = "🟢 Strong Booth"
        elif avg_shares[dominant] >= 45:
            strength = "🟠 Competitive Booth"
        else:
            strength = "🔴 Weak Booth"

        st.markdown(
            f"""
            <div style='border:1px solid #ddd;border-radius:10px;padding:15px;margin-top:20px;background:#f9f9f9;'>
            <h4>📍 Booth {booth_number} – Historical Summary (2019–2024)</h4>
            🏆 <b>Dominant Alliance:</b> {dominant}<br>
            📊 <b>Average Vote Share:</b> {avg_shares[dominant]:.1f}%<br>
            🔄 <b>Swing Volatility:</b> {volatility:.2f}%<br>
            ⚖️ <b>Polarization Index:</b> {polarization_index:.1f}%<br>
            {strength}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------
# Load CSV files for the constituency
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# Load CSV files for the constituency (with district/constituency path)
# ---------------------------------------------------------------
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
data_dir = os.path.abspath(data_dir)

# Full directory for this district + constituency
folder_path = os.path.join(data_dir, district, constituency)
if not os.path.exists(folder_path):
    st.error(f"❌ Data folder not found: {folder_path}")
    st.stop()


all_data = {}
for year, filename in file_list:
    file_path = os.path.join(folder_path, filename)
    if not os.path.exists(file_path):
        st.warning(f"⚠️ Missing file: {file_path}")
        continue
    try:
        df, candidate_cols, polling_col = load_clean_csv(file_path)
        all_data[year] = {
            "data": df,
            "candidates": candidate_cols,
            "polling_col": polling_col,
        }
    except Exception as e:
        st.warning(f"⚠️ {file_path} → {e}")


# UI: booth selector and run
if all_data:
    booths_all = sorted(set(sum([info["data"]["BoothGroup"].astype(str).tolist() for info in all_data.values()], [])))
    selected_booth = st.selectbox("Select Booth Number / பூத் எண்:", booths_all)
    if st.button("Analyze Booth / பகுப்பாய்வு செய்யவும்"):
        booth_pie_comparison(selected_booth, all_data)
else:
    st.error("No CSV data available. Please check file paths and CSV format.")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Please login to continue.")
    st.switch_page("1_Login.py")
# Sidebar logout button
with st.sidebar:
    st.markdown("---")
    if st.button("Logout"):
        st.switch_page("3_Logout.py")


