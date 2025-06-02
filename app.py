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
    df = pd.read_csv("/mnt/data/Claims.csv", encoding="utf-8", sep=";")
    # Columns: 'Claim Number', 'Loss Description', 'Claim Created Time'
    df.columns = [c.strip() for c in df.columns]
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

def queue_reset_form():
    st.session_state.reset_flag = True

def perform_reset():
    st.session_state.loss_cause = "Choose an option:"
    st.session_state.damaged_items = ""
    st.session_state.place_occurrence = ""
    st.session_state.triage = "Choose an option:"
    st.session_state.triage_reasoning = ""
    st.session_state.prevailing_document = "Choose an option:"
    st.session_state.coverage_applicable = []
    st.session_state.limit_applicable = 0.0
    st.session_state.claim_decision = "Choose an option:"
    st.session_state.reasoning = ""
    st.session_state.start_time = time.time()
    st.session_state.paused = False

if "reset_flag" in st.session_state and st.session_state.reset_flag:
    perform_reset()
    st.session_state.reset_flag = False

# ---------- Valid options ----------
VALID_COVERAGE_OPTIONS = [
    'Advantage Elite', 'Coverage A: Dwelling', 'Coverage B: Other Structures',
    'Coverage C: Personal Property', 'No coverage at all', 'Liability claim', 'Other endorsement'
]
TRIAGE_OPTIONS = ['Choose an option:', 'Enough information', 'More information needed']
LOSS_CAUSE_OPTIONS = [
    'Choose an option:', 'Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
    'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
    'Water damage due to appliance failure', 'Water damage due to plumbing system', 'Other'
]
PREVAILING_DOC_OPTIONS = ['Choose an option:', 'Policy', 'Endorsement']
CLAIM_DECISION_OPTIONS = [
    'Choose an option:', 'Covered - Fully', 'Covered - Likely',
    'Not covered/Excluded - Fully', 'Not covered/Excluded – Likely'
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
claim_number = str(claim['Claim Number'])
claim_created_time = str(claim.get('Claim Created Time', ''))

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
    190: "🏁 Final stretch!",
    200: "🎉 ALL DONE! You're a legend!"
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
    if "loss_cause" not in st.session_state:
        st.session_state.loss_cause = prior.get('Loss Cause', "Choose an option:")
    if "damaged_items" not in st.session_state:
        st.session_state.damaged_items = prior.get('Damaged Items', "")
    if "place_occurrence" not in st.session_state:
        st.session_state.place_occurrence = prior.get('Place of Occurrence', "")
    if "triage" not in st.session_state:
        st.session_state.triage = prior.get('Triage', "Choose an option:")
    if "triage_reasoning" not in st.session_state:
        st.session_state.triage_reasoning = prior.get('Triage Reasoning', "")
    if "prevailing_document" not in st.session_state:
        st.session_state.prevailing_document = prior.get('Prevailing Document', "Choose an option:")
    if "coverage_applicable" not in st.session_state:
        raw_coverage = prior.get('Coverage (applicable)', "")
        st.session_state.coverage_applicable = [c for c in raw_coverage.split("; ") if c in VALID_COVERAGE_OPTIONS] if raw_coverage else []
    if "limit_applicable" not in st.session_state:
        try:
            st.session_state.limit_applicable = float(prior.get('Limit (applicable)', 0.0))
        except:
            st.session_state.limit_applicable = 0.0
    if "claim_decision" not in st.session_state:
        st.session_state.claim_decision = prior.get('Claim decision', "Choose an option:")
    if "reasoning" not in st.session_state:
        st.session_state.reasoning = prior.get('Reasoning', "")
    st.session_state.time_spent_edit = float(prior.get('Time Spent (s)', 0.0))
    st.session_state.original_timestamp = prior.get('timeStamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
else:
    st.session_state.time_spent_edit = None
    st.session_state.original_timestamp = None

# ---------- Claim Summary ----------
st.subheader("📄 Claim Summary")
st.markdown(f"**Claim Number:** {claim['Claim Number']}")
st.markdown(f"**Loss Description:** {claim['Loss Description']}")
st.markdown(f"**Claim Created Time:** {claim_created_time}")
st.divider()

# ---------- Form ----------
with st.form("claim_form"):
    st.subheader("📝 Triage")
    loss_cause = st.selectbox("Loss Cause (Required)", LOSS_CAUSE_OPTIONS, key="loss_cause")
    damaged_items = st.text_area("Damaged Items (Optional)", max_chars=5000, key="damaged_items")
    place_occurrence = st.text_area("Place of Occurrence (Optional)", max_chars=5000, key="place_occurrence")
    triage = st.selectbox("Triage (Required)", TRIAGE_OPTIONS, key="triage",
                 help="**ENOUGH INFORMATION**: There is enough information in the description of the claim to move on to the analysis of the documents that may apply.\n\n"
                      "**MORE INFORMATION NEEDED**: There is not enough information in the loss description to proceed to the analysis of applicable documents.\n"
                      "   • AI process ends at this point.\n"
                      "   • The SME continues with the procedures manually.")
    triage_reasoning = st.text_area("Triage Reasoning (Required)", key="triage_reasoning", height=120, max_chars=5000,
                 help="Provide reasoning to support your triage decision:\n"
                      "• Why it considers there is not enough information to continue analyzing the claim, or\n\n"
                      "• Why it considers there is sufficient information to continue analyzing the claim through the applicable documents.")

    st.divider()
    st.subheader("📘 Claim Decision")
    prevailing_document = st.selectbox("Prevailing Document (Required)", PREVAILING_DOC_OPTIONS, key="prevailing_document")
    coverage_applicable = st.multiselect("Coverage (applicable) (Required)", VALID_COVERAGE_OPTIONS, key="coverage_applicable",
                   help="• Based on the LOSS DESCRIPTION\n\n"
                        "• And in the document that, according to the adjuster's criteria, applies to the claim, select the coverage that applies from the list.\n\n"
                        "• The selection can be multiple.")
    limit_applicable = st.number_input("Limit (applicable) (Optional)", min_value=0.0, step=1000.0, key="limit_applicable")
    claim_decision = st.selectbox("Claim decision (Required)", CLAIM_DECISION_OPTIONS, key="claim_decision",
                 help="COVERED:\n"
                      "- Use FULLY if there is no doubt about the coverage\n"
                      "- Use LIKELY when additional information is needed to confirm coverage.\n"
                      "NOT COVERED/EXCLUDED:\n"
                      "- Use FULLY if there is no doubt about the exclusion\n"
                      "- Use LIKELY when additional information is needed to confirm exclusion.")
    reasoning = st.text_area("Reasoning (Required)", key="reasoning", max_chars=5000,
                 help="Based on the LOSS DESCRIPTION + PREVAILING DOCUMENT explain:\n\n"
                      "• why the claim is covered\n\n"
                      "• why the claim is not covered/excluded.")

    submit_action = st.radio("Choose your action:", ["Submit and Continue", "Submit and Pause"], horizontal=True)
    submitted = st.form_submit_button("Submit")

    # --- Minimal Required Field Validation (manual) ---
    required_fields = [
        ("Loss Cause", loss_cause != "Choose an option:"),
        ("Triage", triage != "Choose an option:"),
        ("Triage Reasoning", bool(triage_reasoning.strip())),
        ("Prevailing Document", prevailing_document != "Choose an option:"),
        ("Coverage (applicable)", bool(coverage_applicable)),
        ("Claim decision", claim_decision != "Choose an option:"),
        ("Reasoning", bool(reasoning.strip()))
    ]
    missing_fields = [field for field, ok in required_fields if not ok]

    if submitted:
        if missing_fields:
            st.error("Please fill in all required fields: " + ", ".join(missing_fields))
        else:
            time_taken = st.session_state.time_spent_edit or round(time.time() - st.session_state.start_time, 2)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Row order must match the sheet: 
            # 'SME Name', 'Email', 'Claim Number', 'Claim Created Time', 'Loss Cause', 'Damaged Items', 
            # 'Place of Occurrence', 'Triage', 'Triage Reasoning', 'Prevailing Document', 
            # 'Coverage (applicable)', 'Limit (applicable)', 'Claim decision', 'Reasoning', 
            # 'Time Spent (s)', 'timeStamp'
            row = [
                st.session_state.user_name, st.session_state.user_email, claim_number, claim_created_time,
                loss_cause, damaged_items, place_occurrence, triage, triage_reasoning,
                prevailing_document, "; ".join(coverage_applicable), limit_applicable,
                claim_decision, reasoning, time_taken, timestamp
            ]
            # Force string-safe
            row = [str(x) if x is not None else "" for x in row]

            all_responses = get_all_responses()
            match_condition = (
                (all_responses['Email'].str.lower() == st.session_state.user_email.lower()) &
                (all_responses['Claim Number'].astype(str) == claim_number)
            )
            if match_condition.any():
                row_index = all_responses.index[match_condition][0] + 2  # header is row 1
                sheet.update(f'A{row_index}:P{row_index}', [row])
                st.success(f"Claim {claim_number} updated successfully!")
            else:
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
