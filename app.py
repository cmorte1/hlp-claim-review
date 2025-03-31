# Human-Level Performance Claim Review App (Full Upgrade Version)
import streamlit as st
import pandas as pd
import os
import time
import json

# ---------- File paths ----------
claims_path = "Claims.csv"
response_path = "responses.csv"
checkpoint_path = "checkpoint.json"

# ---------- Load and clean CSV ----------
claims_df = pd.read_csv(
    claims_path,
    encoding="utf-8",
    sep=";",
    engine="python"
)

claims_df.columns = (
    claims_df.columns
    .str.strip()
    .str.replace('\ufeff', '', regex=True)
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

# ---------- Load checkpoint ----------
if os.path.exists(checkpoint_path):
    with open(checkpoint_path, "r") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {}

# ---------- Resume Button Logic ----------
if not st.session_state.user_submitted:
    st.title("🧠 Human-Level Performance: Claim Review App")
    st.markdown("""
    Welcome to the HLP assessment pilot!  
    You'll review **one claim at a time**, complete a short form, and provide your expert input.  
    Each entry will be timed to evaluate review speed and agreement levels, **but please don't rush**, take the necessary time to properly review each claim.

    🟢 Use **Resume Assessment** to continue where you left off.  
    ✅ Use **Submit and Continue** to keep going.  
    🟡 Use **Submit and Pause** to stop your session.

    ⏱️ The timer starts when you begin reviewing each claim. Let's begin by entering your name and email.
    """)

    st.subheader("🔐 User Info")
    name = st.text_input("Full Name")
    email = st.text_input("Email Address")

    if name and email:
        st.session_state.user_name = name
        st.session_state.user_email = email
        user_key = f"{name}|{email}"
        if user_key in checkpoint:
            st.session_state.claim_index = checkpoint[user_key]
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

# ---------- Claim Display ----------
claim = claims_df.iloc[st.session_state.claim_index]
st.markdown(f"### Claim {st.session_state.claim_index + 1} of {len(claims_df)}")

progress = int((st.session_state.claim_index + 1) / len(claims_df) * 100)
st.progress(progress, text=f"Progress: {progress}%")

# 🎉 Motivational Messages
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

# Claim Summary
with st.container():
    st.markdown("#### 📄 Claim Summary")
    st.markdown(f"**Claim Number:** `{claim['claim_number']}`")
    st.markdown(f"**Policy Number:** `{claim['policy_number']}`")
    st.markdown(f"**Policy Type:** `{claim['policy_type']}`")

    st.markdown("**Loss Description:**")
    st.text_area(
        label="",
        value=claim["loss_description"],
        height=200,
        disabled=True,
        key="loss_desc_box"
    )

st.divider()

# ---------- Top Action Buttons ----------
with st.container():
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Submit and Continue"):
            time_taken = round(time.time() - st.session_state.start_time, 2)
            st.session_state.start_time = time.time()

            new_response = pd.DataFrame([{
                "SME Name": st.session_state.user_name,
                "Email": st.session_state.user_email,
                "Claim Number": claim["claim_number"],
                "Policy Number": claim["policy_number"],
                "Triage": st.session_state.triage,
                "Loss Cause": st.session_state.loss_cause,
                "Applicable Coverage": "; ".join(st.session_state.coverage),
                "Initial Determination": st.session_state.init_determination,
                "Applicable Limit": st.session_state.applicable_limit,
                "Damage Items": st.session_state.damage_items,
                "Place of Occurrence": st.session_state.place_occurrence,
                "Notes": st.session_state.notes,
                "Time Spent (s)": time_taken
            }])

            if os.path.exists(response_path):
                existing = pd.read_csv(response_path)
                combined = pd.concat([existing, new_response], ignore_index=True)
            else:
                combined = new_response

            combined.to_csv(response_path, index=False)

            user_key = f"{st.session_state.user_name}|{st.session_state.user_email}"
            checkpoint[user_key] = st.session_state.claim_index + 1
            with open(checkpoint_path, "w") as f:
                json.dump(checkpoint, f)

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

            new_response = pd.DataFrame([{
                "SME Name": st.session_state.user_name,
                "Email": st.session_state.user_email,
                "Claim Number": claim["claim_number"],
                "Policy Number": claim["policy_number"],
                "Triage": st.session_state.triage,
                "Loss Cause": st.session_state.loss_cause,
                "Applicable Coverage": "; ".join(st.session_state.coverage),
                "Initial Determination": st.session_state.init_determination,
                "Applicable Limit": st.session_state.applicable_limit,
                "Damage Items": st.session_state.damage_items,
                "Place of Occurrence": st.session_state.place_occurrence,
                "Notes": st.session_state.notes,
                "Time Spent (s)": time_taken
            }])

            if os.path.exists(response_path):
                existing = pd.read_csv(response_path)
                combined = pd.concat([existing, new_response], ignore_index=True)
            else:
                combined = new_response

            combined.to_csv(response_path, index=False)

            user_key = f"{st.session_state.user_name}|{st.session_state.user_email}"
            checkpoint[user_key] = st.session_state.claim_index
            with open(checkpoint_path, "w") as f:
                json.dump(checkpoint, f)

            st.session_state.paused = True
            st.rerun()

# ---------- Assessment Form ----------
with st.form("claim_form"):
    st.subheader("📝 Your Assessment")

    st.session_state.triage = st.selectbox("Triage", ['Enough information', 'More information needed'])
    st.session_state.loss_cause = st.selectbox("Loss cause", ['Flood', 'Freezing', 'Ice damage', 'Environment', 'Hurricane',
                                             'Mold', 'Sewage backup', 'Snow/Ice', 'Water damage',
                                             'Water damage due to appliance failure',
                                             'Water damage due to plumbing system', 'Other'])
    st.session_state.coverage = st.multiselect("Applicable coverage", [
        'Coverage A: Dwelling', 'Coverage C: Personal Property', 'Coverage D: Loss of use'
    ])
    st.session_state.init_determination = st.selectbox("Initial coverage determination", ['Covered', 'Not covered/excluded'])
    st.session_state.applicable_limit = st.number_input("Applicable limit ($)", min_value=0.0, step=1000.0)

    st.session_state.damage_items = st.text_area("Damage items")
    st.session_state.place_occurrence = st.text_area("Place of occurrence")
    st.session_state.notes = st.text_area("Additional notes or observations")

    if st.form_submit_button("🔝 Go to the top"):
        st.markdown("""<script>window.scrollTo({top: 0, behavior: 'smooth'});</script>""", unsafe_allow_html=True)
