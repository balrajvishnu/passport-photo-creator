import os
import base64
from .config import get_config
from .utils import (
    extract_text_from_pdf, extract_text_from_image, summarize_bill_text, translate_summary,
    extract_due_date_gpt, extract_due_date, generate_pdf, synthesize_speech_gtts, clean_for_tts, language_code
)

def process_bill(file_path, file_type=None, language="English", generate_pdf_flag=False, generate_audio=False, config_path=None):
    config = get_config(config_path)
    OPENAI_API_KEY = config['OPENAI_API_KEY']
    # 1. Extract text
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    if not file_type:
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.pdf':
            file_type = 'application/pdf'
        elif ext in ['.jpg', '.jpeg', '.png']:
            file_type = 'image/jpeg'
        else:
            raise ValueError('Unsupported file type')
    if file_type == 'application/pdf':
        text = extract_text_from_pdf(file_bytes)
    elif file_type in ['image/jpeg', 'image/png', 'image/jpg']:
        text = extract_text_from_image(file_bytes)
    else:
        raise ValueError('Unsupported file type')
    if not text.strip():
        raise ValueError('No text could be extracted from the uploaded file.')
    # 2. Summarize
    summary = summarize_bill_text(text, OPENAI_API_KEY)
    if language != "English":
        summary = translate_summary(summary, language, OPENAI_API_KEY)
    # 3. Due date extraction (three-step)
    due_date_str = extract_due_date_gpt(summary, OPENAI_API_KEY)
    due_date = None
    if due_date_str and due_date_str.lower() != 'not found':
        try:
            from dateutil import parser
            due_date = parser.parse(due_date_str, fuzzy=True).date()
        except Exception:
            due_date = extract_due_date(summary)
    else:
        due_date = extract_due_date(summary)
    # 3b. If still not found, try extracting from the original bill text
    if not due_date:
        due_date = extract_due_date(text)
    # 4. PDF generation (optional)
    pdf_bytes = None
    if generate_pdf_flag:
        pdf_bytes = generate_pdf(summary, language)
    # 5. Voice-over (optional)
    audio_base64 = None
    if generate_audio:
        tts_text = clean_for_tts(summary)
        audio_fp = synthesize_speech_gtts(tts_text, language)  # Returns BytesIO
        audio_bytes = audio_fp.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    return {
        'summary': summary,
        'due_date': due_date,
        'pdf_bytes': pdf_bytes,
        'audio_base64': audio_base64
    }