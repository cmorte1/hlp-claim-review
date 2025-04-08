
# Human-Level Performance Claim Review App (Access-Controlled & Resumable)
import streamlit as st
import pandas as pd
import time
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
def reset_form_state(preserve_user=True):
    if preserve_user:
        preserved = {
            "user_name": st.session_state.get("user_name", ""),
            "user_email": st.session_state.get("user_email", ""),
            "claim_index": st.session_state.get("claim_index", 0),
            "user_submitted": True,
            "paused": False,
            "start_time": time.time()
        }
    else:
        preserved = {}

    form_keys = [
        "sme_loss_cause", "sme_damage_items", "sme_place_occurrence", "sme_triage",
        "sme_triage_reasoning", "sme_prevailing_document", "sme_coverage_applicable",
        "sme_limit_applicable", "sme_reasoning", "sme_claim_prediction",
        "sme_ai_error", "sme_notes"
    ]
    for key in form_keys:
        if key in st.session_state:
            del st.session_state[key]

    for key, value in preserved.items():
        st.session_state[key] = value

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
                st.session_state.claim_index = len(user_responses)
                st.info(f"Resuming from claim {st.session_state.claim_index + 1}")

        st.session_state.user_submitted = True
        st.session_state.start_time = time.time()
        st.rerun()
    st.stop()

# ---------- Pause check ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    st.info(f"Assessment paused at claim {st.session_state.claim_index + 1}")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        reset_form_state()
        st.session_state.claim_index += 1
        st.rerun()
    st.stop()

# ---------- Prevent Claim Overflow ----------
if st.session_state.claim_index >= len(claims_df):
    st.success("🎉 All claims reviewed. You're a legend!")
    st.balloons()
    st.stop()

# ---------- Display Claim ----------
claim = claims_df.iloc[st.session_state.claim_index]

# ---------- Top Status ----------
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")
progress = int((st.session_state.claim_index + 1) / len(claims_df) * 100)
st.progress(progress, text=f"Progress: {progress}%")

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
if (idx := st.session_state.claim_index + 1) in milestones:
    st.success(milestones[idx])

# ---------- Claim Summary ----------
st.header("📄 Claim Summary")
st.markdown(f"**Claim Number:** `{claim['claim_number']}`")
st.markdown("**Loss Description:**")
st.text_area("Loss Description", value=claim["loss_description"], height=180, disabled=True)

# ---------- Assessment Form ----------
with st.form("claim_form"):
    st.subheader("🔍 Triage")
    st.markdown(f"**AI Loss Cause**: {claim['ai_loss_cause']}")
    st.selectbox("SME Loss Cause", ['Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane', 'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage', 'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'], key="sme_loss_cause")
    
    st.markdown(f"**AI Damage Items**: {claim['ai_damage_items']}")
    st.text_area("SME Damage Items", key="sme_damage_items", max_chars=108)
    
    st.markdown(f"**AI Place of Occurrence**: {claim['ai_place_of_occurrence']}")
    st.text_area("SME Place of Occurrence", key="sme_place_occurrence", max_chars=52)

    st.markdown(f"**AI Triage**: {claim['ai_triage']}")
    st.selectbox("SME Triage", ['Enough information', 'More information needed'], key="sme_triage")
    
    st.markdown("**AI Triage Reasoning**")
    st.text_area("AI Reasoning", value=claim['ai_triage_reasoning'], height=140, disabled=True)
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning")

    st.subheader("📘 Claim Prediction")
    st.markdown(f"**AI Prevailing Document**: {claim['ai_prevailing_document']}")
    st.selectbox("SME Prevailing Document", ['Policy', 'Endorsement'], key="sme_prevailing_document")

    st.markdown("**AI Section/Page Document**")
    st.text_area("AI Section/Page", value=claim['ai_section/page_document'], height=140, disabled=True)

    st.markdown(f"**AI Coverage (applicable)**: {claim['ai_coverage_(applicable)']}")
    st.multiselect("SME Coverage (applicable)", ['Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures', 'Coverage C: Personal Property', 'No coverage at all', 'Liability claim'], key="sme_coverage_applicable")

    st.markdown(f"**AI Limit (applicable)**: {claim['ai_limit_(applicable)']}")
    st.number_input("SME Limit (applicable)", min_value=0.0, step=1000.0, key="sme_limit_applicable")

    st.markdown("**AI Reasoning**")
    st.text_area("AI Prediction Reasoning", value=claim['ai_reasoning'], height=180, disabled=True)
    st.text_area("SME Reasoning", key="sme_reasoning")

    st.markdown(f"**AI Claim Prediction**: {claim['ai_claim_prediction']}")
    st.selectbox("SME Claim Prediction", ['Covered - Fully', 'Covered - Likely', 'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'], key="sme_claim_prediction")

    st.selectbox("SME AI Error", ['Claim Reasoning KO', 'Document Analysis KO', 'Dates Analysis KO', 'Automatic Extractions KO'], key="sme_ai_error")
    st.text_area("SME Notes or Observations", key="sme_notes")

    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    if submitted:
        time_taken = round(time.time() - st.session_state.start_time, 2)
        st.session_state.start_time = time.time()

        sheet.append_row([
            str(st.session_state.user_name),
            str(st.session_state.user_email),
            str(claim["claim_number"]),
            str(st.session_state.sme_loss_cause),
            str(st.session_state.sme_damage_items),
            str(st.session_state.sme_place_occurrence),
            str(st.session_state.sme_triage),
            str(st.session_state.sme_triage_reasoning),
            str(st.session_state.sme_prevailing_document),
            "; ".join(st.session_state.sme_coverage_applicable),
            str(st.session_state.sme_limit_applicable),
            str(st.session_state.sme_reasoning),
            str(st.session_state.sme_claim_prediction),
            str(st.session_state.sme_ai_error),
            str(st.session_state.sme_notes),
            str(time_taken)
        ])

        if submit_action == "Submit and Continue":
            if st.session_state.claim_index < len(claims_df) - 1:
                st.session_state.claim_index += 1
                reset_form_state()
                st.rerun()
            else:
                st.balloons()
                st.success("🎉 All claims reviewed. You’re a legend!")
                st.stop()
        elif submit_action == "Submit and Pause":
            st.session_state.paused = True
            reset_form_state()
            st.rerun()

# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")
st.progress(progress, text=f"Progress: {progress}%")
if (idx := st.session_state.claim_index + 1) in milestones:
    st.success(milestones[idx])
