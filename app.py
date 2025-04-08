# Human-Level Performance Claim Review App (Access-Controlled & Resumable)
import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- Access Control List ----------
ALLOWED_EMAILS = [
    'almodovar@mapfre.com', 'esgonza@mapfre.com',
    'cortega@mapfreusa.com', 'cmorte1@mapfre.com'
]

# ---------- Google Sheets Setup ----------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = dict(st.secrets["gcp_service_account"])
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gclient = gspread.authorize(creds)
sheet = gclient.open("HLP_Responses").sheet1

# ---------- Load and clean claims CSV ----------
claims_df = pd.read_csv("Claims.csv", encoding="utf-8", sep=";")
claims_df.columns = claims_df.columns.str.strip().str.lower().str.replace(" ", "_")

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

sme_keys = [
    "sme_loss_cause", "sme_damage_items", "sme_place_occurrence", "sme_triage",
    "sme_triage_reasoning", "sme_prevailing_document", "sme_coverage_applicable",
    "sme_limit_applicable", "sme_reasoning", "sme_claim_prediction",
    "sme_ai_error", "sme_notes"
]

# ---------- Reset form inputs (deferred until rerun) ----------
def queue_reset_form():
    st.session_state.reset_flag = True

def perform_reset():
    for key in sme_keys:
        if "coverage" in key:
            st.session_state[key] = []
        elif "limit" in key:
            st.session_state[key] = 0.0
        else:
            st.session_state[key] = ""

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

    name = st.text_input("Full Name")
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
                st.session_state.claim_index = len(user_responses)
                st.info(f"Resuming from claim {st.session_state.claim_index + 1}")

        st.session_state.user_submitted = True
        st.rerun()
    st.stop()

# ---------- Resume ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        st.session_state.claim_index += 1
        queue_reset_form()
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
st.markdown(f"<span style='color:gold'>Loss Description:</span> {claim['loss_description']}", unsafe_allow_html=True)
st.divider()

# ---------- Form ----------
with st.form("claim_form"):
    st.subheader("🩺 Triage")
    st.markdown(f"<span style='color:gold'>AI Loss Cause:</span> {claim['ai_loss_cause']}", unsafe_allow_html=True)
    st.selectbox("SME Loss Cause", [
        'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
    ], key="sme_loss_cause")

    st.markdown(f"<span style='color:gold'>AI Damage Items:</span> {claim['ai_damage_items']}", unsafe_allow_html=True)
    st.text_area("SME Damage Items", max_chars=108, key="sme_damage_items")

    st.markdown(f"<span style='color:gold'>AI Place of Occurrence:</span> {claim['ai_place_of_occurrence']}", unsafe_allow_html=True)
    st.text_area("SME Place of Occurrence", max_chars=52, key="sme_place_occurrence")

    st.markdown(f"<span style='color:gold'>AI Triage:</span> {claim['ai_triage']}", unsafe_allow_html=True)
    st.selectbox("SME Triage", ['Enough information', 'More information needed'], key="sme_triage")

    st.markdown(f"<span style='color:gold'>AI Triage Reasoning:</span> {claim['ai_triage_reasoning']}", unsafe_allow_html=True)
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning", height=120, max_chars=322)

    st.divider()
    st.subheader("📘 Claim Prediction")
    st.markdown(f"<span style='color:gold'>AI Prevailing Document:</span> {claim['ai_prevailing_document']}", unsafe_allow_html=True)
    st.selectbox("SME Prevailing Document", ['Policy', 'Endorsement'], key="sme_prevailing_document")

    st.markdown(f"<span style='color:gold'>AI Section/Page Document:</span> {claim['ai_section_page_document']}", unsafe_allow_html=True)

    st.markdown(f"<span style='color:gold'>AI Coverage (applicable):</span> {claim['ai_coverage_applicable']}", unsafe_allow_html=True)
    st.multiselect("SME Coverage (applicable)", [
        'Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures',
        'Coverage C: Personal Property', 'No coverage at all', 'Liability claim'
    ], key="sme_coverage_applicable")

    st.markdown(f"<span style='color:gold'>AI Limit (applicable):</span> {claim['ai_limit_applicable']}", unsafe_allow_html=True)
    st.number_input("SME Limit (applicable)", min_value=0.0, step=1000.0, key="sme_limit_applicable")

    st.markdown(f"<span style='color:gold'>AI Reasoning:</span> {claim['ai_reasoning']}", unsafe_allow_html=True)
    st.text_area("SME Reasoning", key="sme_reasoning", max_chars=1760)

    st.markdown(f"<span style='color:gold'>AI Claim Prediction:</span> {claim['ai_claim_prediction']}", unsafe_allow_html=True)
    st.selectbox("SME Claim Prediction", [
        'Covered - Fully', 'Covered - Likely',
        'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'
    ], key="sme_claim_prediction")

    st.selectbox("SME AI Error", [
        "", 'Claim Reasoning KO', 'Document Analysis KO', 'Dates Analysis KO', 'Automatic Extractions KO'
    ], key="sme_ai_error")
    st.text_area("SME Notes or Observations", key="sme_notes")

    # Submission options
    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    if submitted:
        time_taken = round(time.time() - st.session_state.start_time, 2)

        sheet.append_row([
            st.session_state.user_name, st.session_state.user_email, claim["claim_number"],
            st.session_state.sme_loss_cause, st.session_state.sme_damage_items,
            st.session_state.sme_place_occurrence, st.session_state.sme_triage,
            st.session_state.sme_triage_reasoning, st.session_state.sme_prevailing_document,
            "; ".join(st.session_state.sme_coverage_applicable),
            st.session_state.sme_limit_applicable, st.session_state.sme_reasoning,
            st.session_state.sme_claim_prediction, st.session_state.sme_ai_error,
            st.session_state.sme_notes, time_taken
        ])

        if submit_action == "Submit and Continue":
            st.session_state.claim_index += 1
            queue_reset_form()
            st.rerun()
        else:
            st.session_state.paused = True
            queue_reset_form()
            st.rerun()

# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {idx} of {len(claims_df)}")
st.progress(progress, text=f"Progress: {progress}%")
if idx in milestones:
    st.success(milestones[idx])
