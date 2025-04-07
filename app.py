# Human-Level Performance Claim Review App (Access-Controlled & Resumable)
import streamlit as st
import pandas as pd
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- Access Control List ----------
ALLOWED_EMAILS = [
    'almodovar@mapfre.com',
    'esgonza@mapfre.com',
    'cortega@mapfreusa.com',
    'cmorte1@mapfre.com'
]

# ---------- Google Sheets Setup ----------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = {
    "type": st.secrets["gcp_service_account"]["type"],
    "project_id": st.secrets["gcp_service_account"]["project_id"],
    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
    "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
    "client_email": st.secrets["gcp_service_account"]["client_email"],
    "client_id": st.secrets["gcp_service_account"]["client_id"],
    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    "universe_domain": st.secrets["gcp_service_account"].get("universe_domain", "googleapis.com")
}
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

# ---------- Reset form inputs ----------
def reset_form_state():
    st.session_state.triage = None
    st.session_state.loss_cause = None
    st.session_state.coverage = []
    st.session_state.init_determination = None
    st.session_state.applicable_limit = 0.0
    st.session_state.damage_items = ""
    st.session_state.place_occurrence = ""
    st.session_state.notes = ""

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
if "reset_flag" in st.session_state and st.session_state.reset_flag:
    reset_form_state()
    st.session_state.reset_flag = False

# ---------- Landing Page ----------
if not st.session_state.user_submitted:
    st.title("🧠 Human-Level Performance: Claim Review App")
    st.markdown("""
    Welcome to the HLP assessment pilot!  
    You'll review **one claim at a time**, complete a short form, and provide your expert input.  
    Each entry will be timed to evaluate review speed and agreement levels, **but please don't rush**, take the necessary time to properly review each claim.

    ⏱️ The timer starts when you begin reviewing each claim.
    """)

    name = st.text_input("Full Name")
    email = st.text_input("Email Address")
    start_button = st.button("🚀 Start Reviewing")

    if start_button:
        if email not in ALLOWED_EMAILS:
            st.error("🚫 Access denied. Your email is not authorized.")
            st.stop()
        st.session_state.user_name = name
        st.session_state.user_email = email

        # Resume progress
        responses = pd.DataFrame(sheet.get_all_records())
        if not responses.empty:
            user_responses = responses[responses['Email'] == email]
            if not user_responses.empty:
                st.session_state.claim_index = len(user_responses)

        st.session_state.user_submitted = True
        st.session_state.start_time = time.time()
        st.rerun()
    st.stop()

# ---------- Pause check ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        st.session_state.claim_index += 1
        st.session_state.reset_flag = True
        st.rerun()
    st.stop()

# ---------- Display Claim ----------
claim = claims_df.iloc[st.session_state.claim_index]

# ---------- Top Status ----------
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

# ---------- Assessment Form ----------
with st.form("claim_form"):
    st.subheader("📝 Your Assessment")
    st.selectbox("Triage", ['Enough information', 'More information needed'], key="triage")
    st.selectbox("Loss cause", [
        'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
    ], key="loss_cause")
    st.multiselect("Applicable coverage", [
        'Coverage A: Dwelling', 'Coverage B: Other Structures', 'Coverage C: Personal Property'
    ], key="coverage")
    st.selectbox("Initial coverage determination", ['Covered', 'Not covered/excluded'], key="init_determination")
    st.number_input("Applicable limit ($)", min_value=0.0, step=1000.0, key="applicable_limit")
    st.text_area("Damage items", key="damage_items")
    st.text_area("Place of occurrence", key="place_occurrence")
    st.text_area("Additional notes or observations", key="notes")

# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")
st.progress(progress, text=f"Progress: {progress}%")
if (idx := st.session_state.claim_index + 1) in milestones:
    st.success(milestones[idx])

# ---------- Action Buttons ----------
st.divider()
colA, colB = st.columns(2)
with colA:
    if st.button("✅ Submit and Continue"):
        time_taken = round(time.time() - st.session_state.start_time, 2)
        st.session_state.start_time = time.time()
        sheet.append_row([
            str(st.session_state.user_name),
            str(st.session_state.user_email),
            str(claim["claim_number"]),
            str(claim["policy_number"]),
            str(st.session_state.triage),
            str(st.session_state.loss_cause),
            "; ".join([str(cov) for cov in st.session_state.coverage]),
            str(st.session_state.init_determination),
            str(st.session_state.applicable_limit),
            str(st.session_state.damage_items),
            str(st.session_state.place_occurrence),
            str(st.session_state.notes),
            str(time_taken)
        ])
        if st.session_state.claim_index < len(claims_df) - 1:
            reset_form_state()
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
            str(st.session_state.user_name),
            str(st.session_state.user_email),
            str(claim["claim_number"]),
            str(claim["policy_number"]),
            str(st.session_state.triage),
            str(st.session_state.loss_cause),
            "; ".join([str(cov) for cov in st.session_state.coverage]),
            str(st.session_state.init_determination),
            str(st.session_state.applicable_limit),
            str(st.session_state.damage_items),
            str(st.session_state.place_occurrence),
            str(st.session_state.notes),
            str(time_taken)
        ])
        st.session_state.paused = True
        st.rerun()
