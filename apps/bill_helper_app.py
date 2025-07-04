import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import tempfile
import fitz  # PyMuPDF for PDF
from PIL import Image
from io import BytesIO
from config.config import get_config
import openai
import pytesseract
import azure.cognitiveservices.speech as speechsdk
from gtts import gTTS
import re
import urllib.parse
from datetime import datetime, timedelta
import sqlite3
import bcrypt
import getpass
import importlib
import bill_helper.report
importlib.reload(bill_helper.report)
from bill_helper.report import process_bill
import base64

st.set_page_config(page_title="Bill Helper", layout="centered")

# --- Simple Password Protection ---
PASSWORD = os.getenv("BILL_HELPER_PASSWORD", "testpassword")

def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Password incorrect")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        st.stop()

check_password()

# --- Custom Navbar with Title (left, white) and Auth Button (right), no white background ---
st.markdown('''
    <style>
    .navbar-bh {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        padding: 0.7em 1.2em 0.7em 0.5em;
        background: transparent;
        border-bottom: none;
        margin-bottom: 0.5em;
    }
    .navbar-title-bh {
        font-size: 2.1em;
        font-weight: bold;
        color: #fff;
        letter-spacing: 0.5px;
    }
    .navbar-auth-btn-bh {
        font-size: 1.1em;
        color: #1a237e;
        background: #fff;
        border: 1.5px solid #1a237e;
        border-radius: 6px;
        padding: 0.3em 1.1em;
        cursor: pointer;
        font-weight: 500;
        margin-left: 1em;
    }
    .navbar-auth-btn-bh:hover {
        background: #e3e7fa;
    }
    .login-card-bh {
        max-width: 370px;
        margin: 5vh auto 0 auto;
        padding: 2.2em 2em 1.5em 2em;
        text-align: left;
    }
    .login-card-bh h2 {
        color: #1a237e;
        font-size: 1.5em;
        margin-bottom: 0.7em;
        text-align: center;
    }
    .login-card-bh .stTextInput>div>div>input {
        font-size: 1.1em;
    }
    </style>
    <div class="navbar-bh">
        <div class="navbar-title-bh">🤖 Bill Helper</div>
        <div>
            <span id="navbar-auth-anchor"></span>
        </div>
    </div>
''', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload or snap a photo of your bill (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])

language_options = [
    "English", "Spanish", "French", "German", "Hindi", "Chinese", "Arabic", "Russian", "Portuguese", "Japanese", "Italian", "Korean", "Turkish", "Vietnamese", "Bengali", "Urdu", "Tamil", "Telugu", "Gujarati", "Marathi", "Malayalam", "Kannada", "Punjabi", "Oriya", "Assamese"
]
selected_language = st.selectbox("Choose your report language:", language_options, index=0)

voiceover = st.checkbox("Generate voice-over (audio)")

process = st.button("Get My Bill Report")

# --- Maintain state for summary, due_date, days_before, and reminder_date ---
if 'summary' not in st.session_state:
    st.session_state['summary'] = None
if 'due_date' not in st.session_state:
    st.session_state['due_date'] = None
if 'days_before' not in st.session_state:
    st.session_state['days_before'] = 2
if 'reminder_date' not in st.session_state:
    st.session_state['reminder_date'] = None

if process:
    if not uploaded_file:
        st.error("Please upload a utility bill (PDF or image).")
        st.stop()
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    st.session_state['tmp_path'] = tmp_path  # Store for later PDF generation
    try:
        config = get_config()
        OPENAI_API_KEY = config.get('OPENAI_API_KEY')
        AZURE_SPEECH_KEY = config.get('AZURE_SPEECH_KEY')
        AZURE_SPEECH_REGION = config.get('AZURE_SPEECH_REGION')
        result = process_bill(
            tmp_path,
            file_type=uploaded_file.type,
            language=selected_language,
            generate_pdf_flag=False,  # PDF generated on demand below
            generate_audio=voiceover
        )
        audio_base64 = result.get('audio_base64') if isinstance(result, dict) else (result[2] if len(result) > 2 else None)
        audio_bytes = base64.b64decode(audio_base64) if audio_base64 else None
        summary = result['summary']
        due_date = result['due_date']
        st.session_state['summary'] = summary
        st.session_state['due_date'] = due_date
        st.session_state['days_before'] = 2
        st.session_state['reminder_date'] = None
        st.session_state['pdf_ready'] = False
        if voiceover and audio_bytes:
            st.session_state['audio_bytes'] = audio_bytes
    except Exception as e:
        st.error(f"Bill processing error: {e}")
        st.stop()

# --- Display the report and controls if summary is available ---
if st.session_state.get('summary'):
    summary = st.session_state['summary']
    due_date = st.session_state['due_date']
    st.subheader(f"Awesome Bill Report ({selected_language})")
    st.markdown(f"<div style='font-size: 1.7em;'>{summary}</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<span style='font-size:1.5em;'>### 📅 Set a Google Calendar Reminder for Your Bill Due Date</span>", unsafe_allow_html=True)
    if due_date:
        st.markdown(f"<div style='background-color:#d4edda; color:#155724; border-radius:4px; padding:0.75em 1em; font-size:1.3em; margin-bottom:0.5em;'>✅ Detected due date: {due_date}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background-color:#fff3cd; color:#856404; border-radius:4px; padding:0.75em 1em; font-size:1.3em; margin-bottom:0.5em;'>⚠️ Could not detect a due date. Please enter it manually.</div>", unsafe_allow_html=True)
    due_date_str = st.text_input("Bill Due Date (YYYY-MM-DD)", value=str(due_date) if due_date else "")
    try:
        due_date_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        st.session_state['due_date'] = due_date_obj
    except Exception:
        due_date_obj = None
    # Calculate default reminder date
    reminder_date = None
    if due_date_obj:
        # Use 3 days before as a default, but not shown to user
        reminder_date = due_date_obj - timedelta(days=3)
    # Allow user to pick a custom reminder date
    today = datetime.today().date()
    default_reminder = reminder_date if reminder_date and reminder_date >= today else today
    custom_reminder_date = st.date_input(
        "Or pick a custom reminder date:",
        value=default_reminder,
        min_value=today,
        key='custom_reminder_date_input'
    )
    # Use custom date if changed, otherwise use calculated
    final_reminder_date = custom_reminder_date if custom_reminder_date != reminder_date else reminder_date
    st.session_state['reminder_date'] = final_reminder_date
    event_title = "Bill Payment Reminder"
    event_details = f"Don't forget to pay your bill due on {due_date_str}. Generated by Bill Helper."
    if final_reminder_date:
        start_dt = datetime.combine(final_reminder_date, datetime.min.time())
        end_dt = start_dt + timedelta(hours=1)
        start_str = start_dt.strftime("%Y%m%dT%H%M%SZ")
        end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
        gcal_url = (
            "https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={urllib.parse.quote(event_title)}"
            f"&dates={start_str}/{end_str}"
            f"&details={urllib.parse.quote(event_details)}"
        )
        st.markdown(f"<span style='font-size:1.3em;'>[➕ Add to Google Calendar]({gcal_url})</span>", unsafe_allow_html=True)
    # --- PDF Download Button ---
    if 'pdf_ready' not in st.session_state:
        st.session_state['pdf_ready'] = False
    if st.button("Generate PDF Report"):
        try:
            tmp_path = st.session_state.get('tmp_path')
            if not tmp_path:
                st.error("No bill file available for PDF generation. Please upload and process a bill first.")
            elif not uploaded_file:
                st.error("No uploaded file found. Please upload a bill.")
            else:
                result = process_bill(
                    tmp_path,
                    file_type=uploaded_file.type,
                    language=selected_language,
                    generate_pdf_flag=True,
                    generate_audio=False
                )
                pdf_bytes = result.get('pdf_bytes')
                if not pdf_bytes:
                    st.error("PDF generation failed: No PDF bytes returned.")
                else:
                    st.session_state['pdf_bytes'] = pdf_bytes
                    st.session_state['pdf_ready'] = True
        except Exception as e:
            st.error(f"PDF generation error: {e}")
    if st.session_state.get('pdf_ready', False) and st.session_state.get('pdf_bytes'):
        st.download_button(
            label="Download PDF Report",
            data=st.session_state['pdf_bytes'],
            file_name="bill_report.pdf",
            mime="application/pdf",
        )
    if voiceover and st.session_state.get('audio_bytes'):
        st.audio(BytesIO(st.session_state['audio_bytes']), format='audio/mp3')
        st.success("Voice-over generated!")

# NOTE: Requires 'weasyprint' and 'markdown' packages. Install with:
# pip install weasyprint markdown
# (WeasyPrint also requires system dependencies: see https://weasyprint.readthedocs.io/en/stable/install.html) 