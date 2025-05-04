# Human-Level Performance Claim Review App (Access-Controlled & Resumable) with Edit Mode and Navigation
import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- Access Control List ----------
ALLOWED_EMAILS = [
    'almodovar@mapfre.com', 'esgonza@mapfre.com', 'mchabot@mapfreusa.com', 'kmoon@mapfreusa.com',
    'cortega@mapfreusa.com', 'mtangel@mapfre.com', 'cmorte1@mapfre.com'
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
@st.cache_data(ttl=0)
def load_claims():
    df = pd.read_csv("Claims.csv", encoding="utf-8", sep=";")
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("/", "_")
    return df

claims_df = load_claims()

# ---------- Load responses and helper functions ----------
@st.cache_data(ttl=0)
def get_all_responses():
    responses = pd.DataFrame(sheet.get_all_records())
    return responses

def get_user_responses(email):
    responses = get_all_responses()
    user_responses = responses[responses['Email'].str.lower() == email.lower()]
    return user_responses

def get_previous_answers(claim_number, user_email):
    responses = get_all_responses()
    row = responses[responses['Email'].str.lower() == user_email.lower()]
    row = row[row['Claim Number'].astype(str) == str(claim_number)]
    return row.iloc[0] if not row.empty else None

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
    st.session_state.sme_loss_cause = "Choose an option:"
    st.session_state.sme_damaged_items = ""
    st.session_state.sme_place_occurrence = ""
    st.session_state.sme_triage = "Choose an option:"
    st.session_state.sme_triage_reasoning = ""
    st.session_state.sme_prevailing_document = "Choose an option:"
    st.session_state.sme_coverage_applicable = []
    st.session_state.sme_limit_applicable = 0.0
    st.session_state.sme_reasoning = ""
    st.session_state.sme_claim_prediction = "Choose an option:"
    st.session_state.sme_ai_error = []
    st.session_state.sme_notes = ""
    st.session_state.start_time = time.time()
    st.session_state.paused = False

if "reset_flag" in st.session_state and st.session_state.reset_flag:
    perform_reset()
    st.session_state.reset_flag = False

# ---------- Valid options for SME fields ----------
VALID_COVERAGE_OPTIONS = [
    'Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures',
    'Coverage C: Personal Property', 'No coverage at all', 'Liability claim'
]

VALID_AI_ERRORS = [
    'Claim Reasoning KO', 'Document Analysis KO', 'Dates Analysis KO', 'Automatic Extractions KO'
]

# ---------- Landing Page ----------
if not st.session_state.user_submitted:
    st.title("\U0001F9E0 Human-Level Performance: Claim Review App")
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
            st.error("❌ Access denied. Your email is not authorized.")
            st.stop()

        st.session_state.user_name = name
        st.session_state.user_email = email

        responses = get_all_responses()
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
    st.success("🎉 All claims reviewed. You're a legend!")
    st.balloons()
    st.stop()

# ---------- Claim ----------
claim = claims_df.iloc[st.session_state.claim_index]
claim_number = str(claim['claim_number'])

# ---------- Milestones ----------
milestones = {
    1: "🎉 First claim! You're off to a great start!",
    3: "🔄 Rule of three: You're on a roll now!",
    10: "🤘 Double digits already? Rock star!",
    30: "🎯 Thirty and thriving!",
    50: "🍕 Fifty claims? You deserve a raise!",
    90: "🚀 Ninety! That's commitment!",
    120: "🏃‍♂️ Half marathon done—keep that pace!",
    150: "🏅 Top 100? Nah, top 150 club!",
    180: "🧠 Only 70 to go. You got this!",
    210: "🏁 Final stretch!",
    250: "🎉 ALL DONE! You're a legend!"
}
idx = st.session_state.claim_index + 1
st.markdown(f"### Claim {idx} of {len(claims_df)}")
st.progress(int((idx) / len(claims_df) * 100), text=f"Progress: {int((idx) / len(claims_df) * 100)}%")
if idx in milestones:
    st.success(milestones[idx])

# ---------- Navigation ----------
col1, col2 = st.columns([1, 1])
with col1:
    if st.session_state.claim_index > 0:
        if st.button("⬅️ Previous"):
            st.session_state.claim_index -= 1
            queue_reset_form()
            st.rerun()
with col2:
    if st.session_state.claim_index < len(claims_df) - 1:
        if st.button("➡️ Next"):
            st.session_state.claim_index += 1
            queue_reset_form()
            st.rerun()

# ---------- Load Previous Answers If Any ----------
prior = get_previous_answers(claim_number, st.session_state.user_email)
if prior is not None:
    st.info("This claim was already reviewed. You may update your answers.")
    
    # Initialize from previous answers
    if "sme_loss_cause" not in st.session_state:
        st.session_state.sme_loss_cause = prior.get('SME Loss Cause', "Choose an option:")
    if "sme_damaged_items" not in st.session_state:
        st.session_state.sme_damaged_items = prior.get('SME Damaged Items', "")
    if "sme_place_occurrence" not in st.session_state:
        st.session_state.sme_place_occurrence = prior.get('SME Place of Occurrence', "")
    if "sme_triage" not in st.session_state:
        st.session_state.sme_triage = prior.get('SME Triage', "Choose an option:")
    if "sme_triage_reasoning" not in st.session_state:
        st.session_state.sme_triage_reasoning = prior.get('SME Triage Reasoning', "")
    if "sme_prevailing_document" not in st.session_state:
        st.session_state.sme_prevailing_document = prior.get('SME Prevailing Document', "Choose an option:")

    if "sme_coverage_applicable" not in st.session_state:
        raw_coverage = prior.get('SME Coverage (applicable)', "")
        st.session_state.sme_coverage_applicable = [c for c in raw_coverage.split("; ") if c in VALID_COVERAGE_OPTIONS] if raw_coverage else []

    if "sme_limit_applicable" not in st.session_state:
        st.session_state.sme_limit_applicable = float(prior.get('SME Limit (applicable)', 0.0))
    if "sme_reasoning" not in st.session_state:
        st.session_state.sme_reasoning = prior.get('SME Reasoning', "")
    if "sme_claim_prediction" not in st.session_state:
        st.session_state.sme_claim_prediction = prior.get('SME Claim Prediction', "Choose an option:")

    if "sme_ai_error" not in st.session_state:
        raw_ai_error = prior.get('SME AI Error', "")
        st.session_state.sme_ai_error = [e for e in raw_ai_error.split("; ") if e in VALID_AI_ERRORS] if raw_ai_error else []

    st.session_state.time_spent_edit = float(prior.get('Time Spent (s)', 0.0))
    st.session_state.original_timestamp = prior.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
else:
    st.session_state.time_spent_edit = None
    st.session_state.original_timestamp = None

# ---------- Claim Summary ----------
st.subheader("📄 Claim Summary")
st.markdown(f"**Claim Number:** {claim['claim_number']}")
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
    loss_cause_options = [
        'Choose an option:', 'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
        'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
        'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
    ]
    selected_loss_cause = st.session_state.get("sme_loss_cause", "Choose an option:")
    st.selectbox("SME Loss Cause", loss_cause_options, key="sme_loss_cause",
                 index=loss_cause_options.index(selected_loss_cause)
                 if selected_loss_cause in loss_cause_options else 0)

    ai_box("AI Damaged Items", claim['ai_damaged_items'])
    st.text_area("SME Damaged Items", max_chars=5000, key="sme_damaged_items")

    ai_box("AI Place of Occurrence", claim['ai_place_of_occurrence'])
    st.text_area("SME Place of Occurrence", max_chars=5000, key="sme_place_occurrence")

    ai_box("AI Triage", claim['ai_triage'])
    triage_options = ['Choose an option:', 'Enough information', 'More information needed']
    selected_triage = st.session_state.get("sme_triage", "Choose an option:")
    st.selectbox("SME Triage", triage_options, key="sme_triage",
                 index=triage_options.index(selected_triage)
                 if selected_triage in triage_options else 0,
                 help="**ENOUGH INFORMATION**: There is enough information in the description of the claim to move on to the analysis of the documents that may apply.\n\n"
                      "**MORE INFORMATION NEEDED**: There is not enough information in the loss description to proceed to the analysis of applicable documents.\n"
                      "   • AI process ends at this point.\n"
                      "   • The SME continues with the procedures manually.")

    ai_box("AI Triage Reasoning", claim['ai_triage_reasoning'])
    st.text_area("SME Triage Reasoning", key="sme_triage_reasoning", height=120, max_chars=5000,
                 help="Provide reasoning to support your triage decision:\n"
                      "• Why it considers there is not enough information to continue analyzing the claim, or\n\n"
                      "• Why it considers there is sufficient information to continue analyzing the claim through the applicable documents.")

    st.divider()
    st.subheader("📘 Claim Prediction")

    ai_box("AI Prevailing Document", claim['ai_prevailing_document'])
    document_options = ['Choose an option:', 'Policy', 'Endorsement']
    selected_doc = st.session_state.get("sme_prevailing_document", "Choose an option:")
    st.selectbox("SME Prevailing Document", document_options, key="sme_prevailing_document",
                 index=document_options.index(selected_doc)
                 if selected_doc in document_options else 0)

    ai_box("AI Section/Page Document", claim['ai_section_page_document'])

    ai_box("AI Coverage (applicable)", claim['ai_coverage_(applicable)'])
    st.multiselect("SME Coverage (applicable)", VALID_COVERAGE_OPTIONS,
                   key="sme_coverage_applicable",
                   help="• Based on the LOSS DESCRIPTION\n\n"
                        "• And in the document that, according to the adjuster's criteria, applies to the claim, the SME will select the coverage that applies from the following list.\n\n"
                        "• The selection can be multiple.")

    ai_box("AI Limit (applicable)", claim['ai_limit_(applicable)'])
    st.number_input("SME Limit (applicable)", min_value=0.0, step=1000.0, key="sme_limit_applicable")

    ai_box("AI Reasoning", claim['ai_reasoning'])
    st.text_area("SME Reasoning", key="sme_reasoning", max_chars=5000,
                 help="Based on the LOSS DESCRIPTION + PREVAILING DOCUMENT the SME explains:\n\n"
                      "• why he/she considers the claim is covered\n\n"
                      "• why he/she considers the claim is not covered/excluded.")

    ai_box("AI Claim Prediction", claim['ai_claim_prediction'])
    prediction_options = [
        'Choose an option:', 'Covered - Fully', 'Covered - Likely',
        'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'
    ]
    selected_prediction = st.session_state.get("sme_claim_prediction", "Choose an option:")
    st.selectbox("SME Claim Prediction", prediction_options, key="sme_claim_prediction",
                 index=prediction_options.index(selected_prediction)
                 if selected_prediction in prediction_options else 0,
                 help="COVERED:\n"
                      "- The SME will use FULLY if there is no doubt about the coverage\n"
                      "- The SME will use LIKELY when additional information is needed to confirm coverage.\n"
                      "NOT COVERED/EXCLUDED:\n"
                      "- The SME will use FULLY if there is no doubt about the exclusion\n"
                      "- The SME will use LIKELY when additional information is needed to confirm exclusion.")

    st.multiselect("SME AI Error", VALID_AI_ERRORS, key="sme_ai_error")

    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    if submitted:
        time_taken = st.session_state.time_spent_edit or round(time.time() - st.session_state.start_time, 2)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        claim_number = str(claim["claim_number"]) 
        row = [
            st.session_state.user_name, st.session_state.user_email, claim_number,
            st.session_state.sme_loss_cause, st.session_state.sme_damaged_items,
            st.session_state.sme_place_occurrence, st.session_state.sme_triage,
            st.session_state.sme_triage_reasoning, st.session_state.sme_prevailing_document,
            "; ".join(st.session_state.sme_coverage_applicable),
            st.session_state.sme_limit_applicable, st.session_state.sme_reasoning,
            st.session_state.sme_claim_prediction, "; ".join(st.session_state.sme_ai_error),
            time_taken, timestamp
        ]
        # Force everything to be string-safe
        row = [str(x) if x is not None else "" for x in row]
    
        # Optimized logic for updates
        all_responses = get_all_responses()
        # Find rows matching this user's email and the current claim number
        match_condition = ((all_responses['Email'].str.lower() == st.session_state.user_email.lower()) & 
                          (all_responses['Claim Number'].astype(str) == claim_number))
        
        if match_condition.any():
            # Getting the actual row number in Google Sheets (1-indexed with header)
            row_index = all_responses.index[match_condition][0] + 2  # +2 because: +1 for 0-indexing to 1-indexing, +1 for header row
            # Update the entire row in the sheet
            sheet.update(f'A{row_index}:P{row_index}', [row])
            st.success(f"Claim {claim_number} updated successfully!")
        else:
            # Append a new row if no match found
            sheet.append_row(row)
            st.success(f"Claim {claim_number} submitted successfully!")

        if submit_action == "Submit and Continue":
            st.session_state.claim_index += 1
            queue_reset_form()
            st.rerun()
        elif submit_action == "Submit and Pause":
            st.session_state.paused = True
            st.rerun()


# ---------- Bottom Status ----------
st.divider()
st.markdown(f"### Claim {idx} of {len(claims_df)}")
st.progress(int((idx) / len(claims_df) * 100), text=f"Progress: {int((idx) / len(claims_df) * 100)}%")
if idx in milestones:
    st.success(milestones[idx])