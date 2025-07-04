# Utility functions for bill_helper 

import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import pytesseract
import openai
import re
from gtts import gTTS
from weasyprint import HTML
import markdown as md

def extract_text_from_pdf(pdf_bytes):
    with BytesIO(pdf_bytes) as tmp:
        with fitz.open(stream=tmp.read(), filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text()
            return text

def extract_text_from_image(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    text = pytesseract.image_to_string(image)
    return text

def summarize_bill_text(text, openai_api_key):
    client = openai.OpenAI(api_key=openai_api_key)
    prompt = (
        "You are a helpful assistant. Read the following utility bill and provide a clear, concise summary for a general audience. "
        "Highlight the total amount due, due date, billing period, usage details, and any important notes or charges. "
        "Format the summary as a friendly, easy-to-read report.\n\n"
        "At the end of your summary, add a line in the format: 'Due Date: <date>'. Double-check that this is the correct due date from the bill. "
        "If you cannot find a due date, say 'Due Date: Not found'.\n\n"
        + text[:12000]
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    return response.choices[0].message.content.strip()

def translate_summary(summary, target_language, openai_api_key):
    client = openai.OpenAI(api_key=openai_api_key)
    prompt = (
        f"Translate the following bill summary into {target_language}. Keep the translation clear, friendly, and easy to understand.\n\n" + summary
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    return response.choices[0].message.content.strip()

def extract_due_date_gpt(summary, openai_api_key):
    client = openai.OpenAI(api_key=openai_api_key)
    prompt = (
        "Extract the due date from the following bill summary. "
        "Return only the due date in YYYY-MM-DD format if possible, or the exact date string as shown. "
        "If no due date is found, reply with 'Not found'.\n\n" + summary
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=30
    )
    return response.choices[0].message.content.strip()

def extract_due_date(text):
    from dateutil import parser
    lines = text.splitlines()
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}-\d{2}-\d{4})',
        r'([A-Za-z]+ \d{1,2}, \d{4})',
        r'(\d{1,2} [A-Za-z]+ \d{4})',
    ]
    due_keywords = ['due date', 'pay by', 'payment due', 'bill due', 'date due']
    for line in lines:
        if any(kw in line.lower() for kw in due_keywords):
            for pat in date_patterns:
                match = re.search(pat, line)
                if match:
                    try:
                        return parser.parse(match.group(1), fuzzy=True).date()
                    except Exception:
                        continue
    for pat in date_patterns:
        match = re.search(pat, text)
        if match:
            try:
                return parser.parse(match.group(1), fuzzy=True).date()
            except Exception:
                continue
    return None

def generate_pdf(summary, language):
    html_summary = md.markdown(summary, extensions=['extra', 'nl2br'])
    html = f'''
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; font-size: 16px; }}
        h1, h2, h3, h4 {{ color: #1a237e; margin-top: 1.2em; margin-bottom: 0.5em; }}
        ul, ol {{ margin-left: 1.5em; margin-bottom: 1em; }}
        li {{ margin-bottom: 0.4em; }}
        strong {{ font-weight: bold; }}
        em {{ font-style: italic; }}
        hr {{ border: none; border-top: 1.5px solid #888; margin: 1.2em 0; }}
        p {{ margin-bottom: 0.7em; }}
    </style>
    </head>
    <body>
        <h1 style="text-align:center; color:#1a237e;">Awesome Bill Report ({language})</h1>
        {html_summary}
    </body>
    </html>
    '''
    pdf_buffer = BytesIO()
    HTML(string=html).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

def language_code(lang_name):
    mapping = {
        'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Hindi': 'hi', 'Chinese': 'zh', 'Arabic': 'ar',
        'Russian': 'ru', 'Portuguese': 'pt', 'Japanese': 'ja', 'Italian': 'it', 'Korean': 'ko', 'Turkish': 'tr',
        'Vietnamese': 'vi', 'Bengali': 'bn', 'Urdu': 'ur', 'Tamil': 'ta', 'Telugu': 'te', 'Gujarati': 'gu',
        'Marathi': 'mr', 'Malayalam': 'ml', 'Kannada': 'kn', 'Punjabi': 'pa', 'Oriya': 'or', 'Assamese': 'as'
    }
    return mapping.get(lang_name, 'en')

def clean_for_tts(text):
    text = re.sub(r'[\*_#`~]', '', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def synthesize_speech_gtts(text, lang_name):
    lang = language_code(lang_name)
    clean_text = clean_for_tts(text)
    tts = gTTS(text=clean_text, lang=lang)
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)  # Ensure pointer is at the start
    return audio_fp  # Return BytesIO object, do not save to disk