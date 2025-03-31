# Human-Level Performance Claim Review App (Google Sheets Edition)
import streamlit as st
import pandas as pd
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- Google Sheets Setup ----------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(str(st.secrets["gcp_service_account"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gclient = gspread.authorize(creds)
sheet = gclient.open("HLP_Responses").sheet1

# ---------- Load and clean claims CSV ----------
claims_df = pd.read_csv("Claims.csv", encoding="utf-8", sep=";", engine="python")
claims_df.columns = (
    claims_df.columns
    .str.strip()
    .str.replace("\ufeff", "", regex=True)
    .str.lower()
    .str.replace(" ", "_")
)

# ---------- Initialize session state ----------
if "user_submitted" not in st.session_state:
    st.session_state.user_submitted = False
if "claim_index" not in st.session_state:
    st.session_state.claim_index = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "paused" not in st.session_state:
    st.session_state.paused = False

# ---------- Landing Page ----------
if not st.session_state.user_submitted:
    st.title("🧠 Human-Level Performance: Claim Review App_v0.7")
    st.markdown("""
    Welcome to the HLP assessment pilot!  
    You'll review **one claim at a time**, complete a short form, and provide your expert input.  
    Each entry will be timed to evaluate review speed and agreement levels, **but please don't rush**, take the necessary time to properly review each claim.

    ⏱️ The timer starts when you begin reviewing each claim. Let's begin by entering your name and email.
    """)

    name = st.text_input("Full Name")
    email = st.text_input("Email Address")

    if name and email:
        st.session_state.user_name = name
        st.session_state.user_email = email
        st.session_state.user_submitted = True
        st.session_state.start_time = time.time()
        st.rerun()
    else:
        st.warning("Please enter your name and email to continue.")
    st.stop()

# ---------- Pause check ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        st.session_state.claim_index += 1
        st.rerun()
    st.stop()

# ---------- Display Claim ----------
claim = claims_df.iloc[st.session_state.claim_index]
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")

progress = int((st.session_state.claim_index + 1) / len(claims_df) * 100)
st.progress(progress, text=f"Progress: {progress}%")

milestones = {
    1: "🎉 First claim! You’re off to a great start!",
    3: "🔄 Rule of three: You’re on a roll now!",
    10: "🤘 Double digits already? Rock star!",
    30: "🎯 Thirty and thriving!",
    60: "🍕 Sixty claims? You deserve a raise!",
    90: "🚀 Ninety! That’s commitment!",
    120: "🏃‍♂️ Half marathon done—keep that pace!",
    150: "🏅 Top 100? Nah, top 150 club!",
    180: "🧠 Only 70 to go. You got this!",
    210: "🏁 Final stretch!",
    250: "🎉 ALL DONE! You’re a legend!"
}
if (idx := st.session_state.claim_index + 1) in milestones:
    st.success(milestones[idx])

# ---------- Claim Summary ----------
with st.container():
    st.markdown("#### 📄 Claim Summary")
    st.markdown(f"**Claim Number:** `{claim['claim_number']}`")
    st.markdown(f"**Policy Number:** `{claim['policy_number']}`")
    st.markdown(f"**Policy Type:** `{claim['policy_type']}`")
    st.markdown("**Loss Description:**")
    st.text_area("", value=claim["loss_description"], height=200, disabled=True, key="loss_desc_box")

st.divider()

# ---------- Action Buttons ----------
with st.container():
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Submit and Continue"):
            time_taken = round(time.time() - st.session_state.start_time, 2)
            st.session_state.start_time = time.time()
            sheet.append_row([
                st.session_state.user_name,
                st.session_state.user_email,
                claim["claim_number"],
                claim["policy_number"],
                st.session_state.triage,
                st.session_state.loss_cause,
                "; ".join(st.session_state.coverage),
                st.session_state.init_determination,
                st.session_state.applicable_limit,
                st.session_state.damage_items,
                st.session_state.place_occurrence,
                st.session_state.notes,
                time_taken
            ])
            if st.session_state.claim_index < len(claims_df) - 1:
                st.session_state.claim_index += 1
                st.rerun()
            else:
                st.balloons()
                st.success("🎉 All claims reviewed. You’re a legend!")
                st.stop()
    with colB:
        if st.button("🟡 Submit and Pause"):
            time_taken = round(time.time() - st.session_state.start_time, 2)
            st.session_state.start_time = time.time()
            sheet.append_row([
                st.session_state.user_name,
                st.session_state.user_email,
                claim["claim_number"],
                claim["policy_number"],
                st.session_state.triage,
                st.session_state.loss_cause,
                "; ".join(st.session_state.coverage),
                st.session_state.init_determination,
                st.session_state.applicable_limit,
                st.session_state.damage_items,
                st.session_state.place_occurrence,
                st.session_state.notes,
                time_taken
            ])
            st.session_state.paused = True
            st.rerun()

# ---------- Assessment Form ----------
with st.form("claim_form"):
    st.subheader("📝 Your Assessment")
    st.session_state.triage = st.selectbox("Triage", ['Enough information', 'More information needed'])
    st.session_state.loss_cause = st.selectbox("Loss cause", [
        'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'])
    st.session_state.coverage = st.multiselect("Applicable coverage", [
        'Coverage A: Dwelling', 'Coverage C: Personal Property', 'Coverage D: Loss of use'])
    st.session_state.init_determination = st.selectbox("Initial coverage determination", ['Covered', 'Not covered/excluded'])
    st.session_state.applicable_limit = st.number_input("Applicable limit ($)", min_value=0.0, step=1000.0)
    st.session_state.damage_items = st.text_area("Damage items")
    st.session_state.place_occurrence = st.text_area("Place of occurrence")
    st.session_state.notes = st.text_area("Additional notes or observations")
    st.form_submit_button("🔝 Go to the top", on_click=lambda: st.markdown("""<script>window.scrollTo({top: 0, behavior: 'smooth'});</script>""", unsafe_allow_html=True))
