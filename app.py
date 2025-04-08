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
    keys_to_clear = [
        "sme_loss_cause", "sme_damage_items", "sme_place_of_occurrence", "sme_triage",
        "sme_triage_reasoning", "sme_prevailing_document", "sme_coverage", "sme_limit",
        "sme_reasoning", "sme_prediction", "sme_ai_error", "sme_notes"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    for key, value in preserved.items():
        st.session_state[key] = value

# ---------- Initialize session state ----------
for key, default in {
    "user_submitted": False, "claim_index": 0, "paused": False,
    "start_time": time.time(), "user_name": "", "user_email": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "reset_flag" in st.session_state and st.session_state.reset_flag:
    reset_form_state()
    st.session_state.reset_flag = False

# ---------- Landing Page ----------
if not st.session_state.user_submitted:
    st.title("🧠 Human-Level Performance: Claim Review App")
    st.markdown("""
        Welcome to the HLP assessment pilot!  
        You'll review **one claim at a time**, complete a short form, and provide your expert input.  
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

# ---------- Pause Check ----------
if st.session_state.paused:
    st.warning("🟡 Session paused. Click below to resume.")
    st.info(f"Assessment paused at claim {st.session_state.claim_index + 1}")
    if st.button("🟢 Resume Assessment"):
        st.session_state.paused = False
        st.session_state.claim_index += 1
        reset_form_state()
        st.rerun()
    st.stop()

# ---------- Claim Handling ----------
if st.session_state.claim_index >= len(claims_df):
    st.success("🎉 All claims reviewed. You're a legend!")
    st.balloons()
    st.stop()

claim = claims_df.iloc[st.session_state.claim_index]

# ---------- Top Status ----------
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")
progress = int((st.session_state.claim_index + 1) / len(claims_df) * 100)
st.progress(progress, text=f"Progress: {progress}%")

# ---------- Milestones ----------
milestones = {
    1: "🎉 First claim! You’re off to a great start!", 3: "🔄 Rule of three: You’re on a roll now!",
    10: "🤘 Double digits already? Rock star!", 30: "🎯 Thirty and thriving!", 60: "🍕 Sixty claims?",
    90: "🚀 Ninety! That’s commitment!", 120: "🏃‍♂️ Half marathon done—keep that pace!",
    150: "🏅 Top 100? Nah, top 150 club!", 180: "🧠 Only 70 to go. You got this!",
    210: "🏁 Final stretch!", 250: "🎉 ALL DONE! You’re a legend!"
}
if (idx := st.session_state.claim_index + 1) in milestones:
    st.success(milestones[idx])

# ---------- Form ----------
with st.form("claim_form"):
    st.subheader("📄 Claim Summary")
    st.markdown(f"**Claim Number:** `{claim['claim_number']}`")
    st.markdown("**Loss Description:**")
    st.text_area("", value=claim["loss_description"], height=150, disabled=True)

    st.subheader("🔍 Triage")
    st.markdown(f"**AI Loss Cause:** `{claim['ai_loss_cause']}`")
    st.selectbox("SME Loss Cause", options=[
        'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
    ], key="sme_loss_cause")

    st.markdown(f"**AI Damage Items:** `{claim['ai_damage_items']}`")
    st.text_area("SME Damage Items", max_chars=108, key="sme_damage_items")

    st.markdown(f"**AI Place of Occurrence:** `{claim['ai_place_of_occurrence']}`")
    st.text_area("SME Place of Occurrence", max_chars=52, key="sme_place_of_occurrence")

    st.markdown(f"**AI Triage:** `{claim['ai_triage']}`")
    st.selectbox("SME Triage", options=['Enough information', 'More information needed'], key="sme_triage")

    st.markdown("**AI Triage Reasoning:**")
    st.text_area("", value=claim["ai_triage_reasoning"], height=160, disabled=True)
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning")

    st.subheader("🧾 Claim Prediction")
    st.markdown(f"**AI Prevailing Document:** `{claim['ai_prevailing_document']}`")
    st.selectbox("SME Prevailing Document", options=['Policy', 'Endorsement'], key="sme_prevailing_document")

    st.markdown("**AI Section/Page Document:**")
    st.text_area("", value=claim["ai_section/page_document"], height=160, disabled=True)

    st.markdown(f"**AI Coverage (applicable):** `{claim['ai_coverage_(applicable)']}`")
    st.multiselect("SME Coverage (applicable)", options=[
        'Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures',
        'Coverage C: Personal Property', 'No coverage at all', 'Liability claim'
    ], key="sme_coverage")

    st.markdown(f"**AI Limit (applicable):** `{claim['ai_limit_(applicable)']}`")
    st.number_input("SME Limit (applicable)", min_value=0.0, step=1000.0, key="sme_limit")

    st.markdown("**AI Reasoning:**")
    st.text_area("", value=claim["ai_reasoning"], height=200, disabled=True)
    st.text_area("SME Reasoning", key="sme_reasoning")

    st.markdown(f"**AI Claim Prediction:** `{claim['ai_claim_prediction']}`")
    st.selectbox("SME Claim Prediction", options=[
        'Covered - Fully', 'Covered - Likely',
        'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'
    ], key="sme_prediction")

    st.selectbox("SME AI Error", options=[
        'Claim Reasoning KO', 'Document Analysis KO',
        'Dates Analysis KO', 'Automatic Extractions KO'
    ], key="sme_ai_error")

    st.text_area("SME Notes or Observations", key="sme_notes")

    submit = st.form_submit_button("✅ Submit and Continue")
    pause = st.form_submit_button("🟡 Submit and Pause")

    if submit or pause:
        time_taken = round(time.time() - st.session_state.start_time, 2)
        st.session_state.start_time = time.time()
        row = [
            st.session_state.user_name,
            st.session_state.user_email,
            claim["claim_number"],
            st.session_state.sme_loss_cause,
            st.session_state.sme_damage_items,
            st.session_state.sme_place_occurrence,
            st.session_state.sme_triage,
            st.session_state.sme_triage_reasoning,
            st.session_state.sme_prevailing_document,
            "; ".join(st.session_state.sme_coverage),
            st.session_state.sme_limit,
            st.session_state.sme_reasoning,
            st.session_state.sme_prediction,
            st.session_state.sme_ai_error,
            st.session_state.sme_notes,
            time_taken
        ]
        sheet.append_row([str(x) for x in row])

        if submit:
            st.session_state.claim_index += 1
            reset_form_state()
            st.rerun()
        elif pause:
            st.session_state.paused = True
            reset_form_state()
            st.rerun()

# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")
st.progress(progress, text=f"Progress: {progress}%")
if idx in milestones:
    st.success(milestones[idx])
