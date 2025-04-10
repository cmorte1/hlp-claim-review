# Human-Level Performance Claim Review App (Access-Controlled & Resumable)
import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- Access Control List ----------
ALLOWED_EMAILS = [
    'almodovar@mapfre.com', 'esgonza@mapfre.com',
    'cortega@mapfreusa.com', 'cmorte1@mapfre.com'
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
claims_df = pd.read_csv("Claims.csv", encoding="utf-8", sep=";")
claims_df.columns = claims_df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("/", "_")

# ---------- Initialize session state ----------
defaults = {
    "user_submitted": False,
    "claim_index": 0,
    "start_time": time.time(),
    "user_name": "",
    "user_email": "",
    "paused": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------- Reset form inputs ----------
def queue_reset_form():
    st.session_state.reset_flag = True

def perform_reset():
    st.session_state.sme_loss_cause = "Other"
    st.session_state.sme_damage_items = ""
    st.session_state.sme_place_occurrence = ""
    st.session_state.sme_triage = "Enough information"
    st.session_state.sme_triage_reasoning = ""
    st.session_state.sme_prevailing_document = "Policy"
    st.session_state.sme_coverage_applicable = []
    st.session_state.sme_limit_applicable = 0.0
    st.session_state.sme_reasoning = ""
    st.session_state.sme_claim_prediction = "Covered - Fully"
    st.session_state.sme_ai_error = []  # Updated for multiselect
    st.session_state.sme_notes = ""
    st.session_state.start_time = time.time()
    st.session_state.paused = False

if "reset_flag" in st.session_state and st.session_state.reset_flag:
    perform_reset()
    st.session_state.reset_flag = False

# ---------- Landing Page ----------
if not st.session_state.user_submitted:
    st.title("🧠 Human-Level Performance: Claim Review App")
    st.markdown("""
    Welcome to the HLP assessment tool!  
    You'll review **one claim at a time**, complete a short form, and provide your expert input.  
    Each entry will be timed to evaluate review speed and agreement levels, **but please don't rush**, take the necessary time to properly review each claim.  

    ⏱️ The timer starts when you begin reviewing each claim.
    """)

    name = st.text_input("Name")
    email = st.text_input("Email Address")
    start_button = st.button("🚀 Start Reviewing")

    if start_button:
        if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
            st.error("🚫 Access denied. Your email is not authorized.")
            st.stop()

        st.session_state.user_name = name
        st.session_state.user_email = email

        responses = pd.DataFrame(sheet.get_all_records())
        if not responses.empty:
            user_responses = responses[responses['Email'].str.lower() == email.lower()]
            if not user_responses.empty:
                reviewed_claims = user_responses["Claim Number"].dropna().unique()
                st.session_state.claim_index = len(reviewed_claims)
                st.info(f"Resuming from claim {st.session_state.claim_index + 1}")
        st.session_state.user_submitted = True
        st.rerun()
    st.stop()

# ---------- Resume ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        queue_reset_form()
        st.session_state.claim_index += 1
        st.rerun()
    st.stop()

# ---------- Prevent Claim Overflow ----------
if st.session_state.claim_index >= len(claims_df):
    st.success("🎉 All claims reviewed. You’re a legend!")
    st.balloons()
    st.stop()

# ---------- Claim ----------
claim = claims_df.iloc[st.session_state.claim_index]

# ---------- Milestones ----------
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
idx = st.session_state.claim_index + 1
st.markdown(f"### Claim {idx} of {len(claims_df)}")
st.progress(int((idx) / len(claims_df) * 100), text=f"Progress: {int((idx) / len(claims_df) * 100)}%")
if idx in milestones:
    st.success(milestones[idx])

# ---------- Claim Summary ----------
st.subheader("📄 Claim Summary")
st.markdown(f"**Claim Number:** `{claim['claim_number']}`")
st.markdown(f"**Loss Description:** {claim['loss_description']}")
st.divider()

# ---------- Helper for AI field display ----------
def ai_box(label, value):
    st.markdown(f"**{label}:**", unsafe_allow_html=True)
    st.markdown(f"<div style='background-color:#f0f0f0; color:goldenrod; padding:8px; border-radius:4px'>{value}</div>", unsafe_allow_html=True)

# ---------- Form ----------
with st.form("claim_form"):
    st.subheader("📝 Triage")

    ai_box("AI Loss Cause", claim['ai_loss_cause'])
    st.selectbox("SME Loss Cause", [
        'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
    ], key="sme_loss_cause")

    ai_box("AI Damage Items", claim['ai_damage_items'])
    st.text_area("SME Damage Items", max_chars=108, key="sme_damage_items")

    ai_box("AI Place of Occurrence", claim['ai_place_of_occurrence'])
    st.text_area("SME Place of Occurrence", max_chars=52, key="sme_place_occurrence")

    ai_box("AI Triage", claim['ai_triage'])
    st.selectbox("SME Triage", ['Enough information', 'More information needed'], key="sme_triage")

    ai_box("AI Triage Reasoning", claim['ai_triage_reasoning'])
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning", height=120, max_chars=322)

    st.divider()
    st.subheader("📘 Claim Prediction")

    ai_box("AI Prevailing Document", claim['ai_prevailing_document'])
    st.selectbox("SME Prevailing Document", ['Policy', 'Endorsement'], key="sme_prevailing_document")

    ai_box("AI Section/Page Document", claim['ai_section_page_document'])

    ai_box("AI Coverage (applicable)", claim['ai_coverage_(applicable)'])
    st.multiselect("SME Coverage (applicable)", [
        'Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures',
        'Coverage C: Personal Property', 'No coverage at all', 'Liability claim'
    ], key="sme_coverage_applicable")

    ai_box("AI Limit (applicable)", claim['ai_limit_(applicable)'])
    st.number_input("SME Limit (applicable)", min_value=0.0, step=1000.0, key="sme_limit_applicable")

    ai_box("AI Reasoning", claim['ai_reasoning'])
    st.text_area("SME Reasoning", key="sme_reasoning", max_chars=1760)

    ai_box("AI Claim Prediction", claim['ai_claim_prediction'])
    st.selectbox("SME Claim Prediction", [
        'Covered - Fully', 'Covered - Likely',
        'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'
    ], key="sme_claim_prediction")

    st.multiselect("SME AI Error", [
        'Claim Reasoning KO', 'Document Analysis KO', 'Dates Analysis KO', 'Automatic Extractions KO'
    ], key="sme_ai_error")
    st.text_area("SME Notes or Observations", key="sme_notes")

    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    if submitted:
        time_taken = round(time.time() - st.session_state.start_time, 2)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sheet.append_row([
            st.session_state.user_name, st.session_state.user_email, claim["claim_number"],
            st.session_state.sme_loss_cause, st.session_state.sme_damage_items,
            st.session_state.sme_place_occurrence, st.session_state.sme_triage,
            st.session_state.sme_triage_reasoning, st.session_state.sme_prevailing_document,
            "; ".join(st.session_state.sme_coverage_applicable),
            st.session_state.sme_limit_applicable, st.session_state.sme_reasoning,
            st.session_state.sme_claim_prediction, "; ".join(st.session_state.sme_ai_error),
            st.session_state.sme_notes, time_taken, timestamp
        ])

        if submit_action == "Submit and Continue":
            st.session_state.claim_index += 1
            queue_reset_form()
            st.rerun()
        elif submit_action == "Submit and Pause":
            st.session_state.claim_index += 0  # Important: advance to next claim
            st.session_state.paused = True     # Set pause flag
            st.rerun()                          # No reset now, reset happens after resume


# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {idx} of {len(claims_df)}")
st.progress(int((idx) / len(claims_df) * 100), text=f"Progress: {int((idx) / len(claims_df) * 100)}%")
if idx in milestones:
    st.success(milestones[idx])
