
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
    preserved_keys = {}
    if preserve_user:
        preserved_keys = {
            "user_name": st.session_state.get("user_name", ""),
            "user_email": st.session_state.get("user_email", ""),
            "claim_index": st.session_state.get("claim_index", 0),
            "user_submitted": True,
            "paused": False,
            "start_time": time.time()
        }

    keys_to_clear = [
        "sme_loss_cause", "sme_damage_items", "sme_place_occurrence",
        "sme_triage", "sme_triage_reasoning", "sme_prevailing_document",
        "sme_coverage_applicable", "sme_limit_applicable", "sme_reasoning",
        "sme_claim_prediction", "sme_ai_error", "sme_notes"
    ]
    for key in keys_to_clear:
        st.session_state[key] = "" if "limit" not in key else 0.0
        if "coverage" in key:
            st.session_state[key] = []

    for key, value in preserved_keys.items():
        st.session_state[key] = value

# ---------- Initialize session state ----------
for key in ["user_submitted", "claim_index", "start_time", "user_name", "user_email", "paused"]:
    if key not in st.session_state:
        st.session_state[key] = False if key in ["user_submitted", "paused"] else (0 if key == "claim_index" else "")

if "reset_flag" in st.session_state and st.session_state.reset_flag:
    reset_form_state()
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

        # Resume progress
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
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning", min_height=80, max_chars=322)

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
        "", 'Claim Reasoning KO', 'Document Analysis KO',
        'Dates Analysis KO', 'Automatic Extractions KO'
    ], key="sme_ai_error")
    st.text_area("SME Notes or Observations", key="sme_notes")

    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    if submitted:
        time_taken = round(time.time() - st.session_state.start_time, 2)
        st.session_state.start_time = time.time()

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
