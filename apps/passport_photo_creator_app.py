import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import rembg
import pathlib
import re

# --- Constants and Configuration ---
# Using a dictionary for passport photo sizes (mm)
# Source: Wikipedia and other official sources
PASSPORT_SPECS = {
    "United States": {"w_mm": 51, "h_mm": 51, "ppi": 300},
    "United Kingdom": {"w_mm": 35, "h_mm": 45, "ppi": 600},
    "Canada": {"w_mm": 50, "h_mm": 70, "ppi": 300},
    "Australia": {"w_mm": 35, "h_mm": 45, "ppi": 300},
    "Germany": {"w_mm": 35, "h_mm": 45, "ppi": 600},
    "India": {"w_mm": 51, "h_mm": 51, "ppi": 300},
    "Schengen Visa": {"w_mm": 35, "h_mm": 45, "ppi": 300},
    "Custom": {"w_mm": 50, "h_mm": 50, "ppi": 300} # Default custom
}

# --- Image Processing Functions ---

def mm_to_px(mm, ppi):
    """Converts millimeters to pixels based on PPI."""
    return int((mm / 25.4) * ppi)

@st.cache_data(show_spinner="Performing initial processing...")
def process_image(image_bytes, auto_contrast, brightness, sharpness, white_bg):
    """
    Performs the slow, one-time processing steps on an image's byte data.
    This function is cached to avoid re-running on every slider change.
    The input is bytes, not a file object, to ensure the cache works correctly.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
    if white_bg:
        try:
            image_no_bg = rembg.remove(image)
            white_background = Image.new("RGB", image_no_bg.size, (255, 255, 255))
            white_background.paste(image_no_bg, (0, 0), image_no_bg)
            image = white_background
        except Exception as e:
            st.error(f"Failed to apply white background: {e}")

    if auto_contrast:
        image = ImageOps.autocontrast(image)
        
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(brightness)
    
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(sharpness)
        
    return image

def frame_image(image, target_w_px, target_h_px, zoom, pan_x_percent, pan_y_percent):
    w, h = image.size
    target_aspect = target_w_px / target_h_px
    img_aspect = w / h

    if img_aspect > target_aspect:
        base_h = h
        base_w = h * target_aspect
    else:
        base_w = w
        base_h = w / target_aspect
    
    # This is the fix: Introduce a small margin (e.g., 90%) at 1x zoom
    # to ensure panning is always possible on both axes.
    zoom_factor = 0.9 / zoom 

    box_w = int(base_w * zoom_factor)
    box_h = int(base_h * zoom_factor)

    pannable_w = w - box_w
    pannable_h = h - box_h

    offset_x = (pannable_w / 2) * (pan_x_percent / 50.0)
    offset_y = (pannable_h / 2) * (pan_y_percent / 50.0)

    left = int((w - box_w) / 2 + offset_x)
    top = int((h - box_h) / 2 - offset_y)
    
    cropped_image = image.crop((left, top, left + box_w, top + box_h))

    final_image = cropped_image.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
    return final_image

def image_to_bytes(image: Image.Image):
    """Converts a PIL Image to a byte stream for downloading."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- Streamlit UI ---
st.set_page_config(layout="wide") # Use wide layout for two columns
st.title("Passport Photo Creator")

if 'stage' not in st.session_state:
    st.session_state.stage = 'capture'

# --- Stage 1: Capture ---
if st.session_state.stage == 'capture':
    col1, col2 = st.columns(2)
    with col1:
        st.header("1. Photo Specifications")
        country = st.selectbox(
            "Select Country (or Custom)",
            options=list(PASSPORT_SPECS.keys()),
            key='country_select'
        )
        spec = PASSPORT_SPECS[country]
        ppi = spec['ppi']
        if country == "Custom":
            c1, c2, c3 = st.columns(3)
            with c1: width_mm = st.number_input("Width (mm)", min_value=1, value=spec['w_mm'], key='custom_w')
            with c2: height_mm = st.number_input("Height (mm)", min_value=1, value=spec['h_mm'], key='custom_h')
            with c3: ppi = st.number_input("PPI (Pixels Per Inch)", min_value=72, value=spec['ppi'], key='custom_ppi')
        else:
            width_mm = spec['w_mm']
            height_mm = spec['h_mm']
            st.write(f"Dimensions: {width_mm}mm x {height_mm}mm at {ppi} PPI")
        target_w_px = mm_to_px(width_mm, ppi)
        target_h_px = mm_to_px(height_mm, ppi)
        st.write(f"Output size: {target_w_px}px x {target_h_px}px")
        st.markdown("---")
        st.header("2. Get Your Photo")
        img_file_buffer = st.camera_input("Take a picture")
        st.markdown('<div style="text-align:center; color:#fff; font-size:1.1em; margin-top:0.5em;">Take your picture in a well-lit environment and ensure there are no dark obstructions or clutter in the background for best results.</div>', unsafe_allow_html=True)
        if img_file_buffer:
            st.session_state.original_photo = img_file_buffer
            st.session_state.stage = 'process_and_frame'
            st.session_state['photo_specs'] = {
                'country': country,
                'width_mm': width_mm,
                'height_mm': height_mm,
                'ppi': ppi,
                'target_w_px': target_w_px,
                'target_h_px': target_h_px
            }
            st.rerun()
    with col2:
        st.info("After taking a photo, you will be able to process and frame it in the studio on the next screen.")

# --- Stage 2: Processing and Framing Studio (Two-Column Layout) ---
elif st.session_state.stage == 'process_and_frame':
    st.header("Processing & Framing Studio")
    col1, col2 = st.columns(2)
    
    # --- All Controls in the Left Column ---
    with col1:
        st.subheader("1. Photo Specifications")
        country = st.session_state['photo_specs']['country']
        spec = PASSPORT_SPECS[country]
        ppi = spec['ppi']
        if country == "Custom":
            c1, c2, c3 = st.columns(3)
            with c1: width_mm = st.number_input("Width (mm)", min_value=1, value=spec['w_mm'], key='custom_w')
            with c2: height_mm = st.number_input("Height (mm)", min_value=1, value=spec['h_mm'], key='custom_h')
            with c3: ppi = st.number_input("PPI (Pixels Per Inch)", min_value=72, value=spec['ppi'], key='custom_ppi')
        else:
            width_mm = spec['w_mm']
            height_mm = spec['h_mm']
            st.write(f"Dimensions: {width_mm}mm x {height_mm}mm at {ppi} PPI")
        
        target_w_px = mm_to_px(width_mm, ppi)
        target_h_px = mm_to_px(height_mm, ppi)
        st.write(f"Output size: {target_w_px}px x {target_h_px}px")
        
        st.markdown("---")

        st.subheader("2. Image Enhancements")
        st.checkbox("Set White Background", value=True, key='white_bg')
        st.checkbox("Auto-Contrast", value=True, key='auto_contrast')
        st.slider("Brightness", 0.5, 2.0, 1.0, 0.05, key='brightness')
        st.slider("Sharpness", 0.0, 3.0, 1.0, 0.1, key='sharpness')
        
        st.markdown("---")

        st.subheader("3. Crop and Position")
        st.markdown('<div style="text-align:center; color:#fff; font-size:1.15em; font-weight:bold; margin-bottom:0.2em;">Use the sliders to zoom and position the final crop.</div>', unsafe_allow_html=True)
        zoom = st.slider("Zoom", 1.0, 2.0, 1.0, 0.05, key="zoom")
        pan_x = st.slider("Pan Horizontally", -50, 50, 0, key="pan_x")
        pan_y = st.slider("Pan Vertically", -50, 50, 0, key="pan_y")
        st.markdown('<div style="text-align:center; color:#fff; font-size:1.05em; font-weight:bold; margin-top:0.5em;">Use the sliders above to pan horizontally or vertically and align your face to the center.</div>', unsafe_allow_html=True)

    # --- Image Preview and Download in the Right Column ---
    with col2:
        st.subheader("Live Preview")
        image_bytes = st.session_state['original_photo'].getvalue()
        processed_image = process_image(
            image_bytes,
            st.session_state.get('auto_contrast', True),
            st.session_state.get('brightness', 1.0),
            st.session_state.get('sharpness', 1.0),
            st.session_state.get('white_bg', True)
        )
        
        final_image = frame_image(
            processed_image, 
            target_w_px, 
            target_h_px, 
            zoom, 
            pan_x, 
            pan_y
        )
        st.image(final_image, caption="Final Framed Photo", use_column_width=True)
        
        st.markdown("---")
        st.download_button(
            label="Download Photo",
            data=image_to_bytes(final_image),
            file_name=f"passport_photo_{country.replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True
        )

    if st.button("<< Start Over"):
        keys_to_delete = ['stage', 'original_photo', 'processed_image']
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

st.markdown("---")

# --- Footer with clickable links for Privacy Policy and Disclaimer ---
ROOT_DIR = pathlib.Path(__file__).parent.parent
PRIVACY_PATH = ROOT_DIR / "PRIVACY.md"
LICENSE_PATH = ROOT_DIR / "LICENSE"
try:
    PRIVACY_TEXT = PRIVACY_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    PRIVACY_TEXT = "Privacy policy file not found."
try:
    LICENSE_TEXT = LICENSE_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    LICENSE_TEXT = "MIT license file not found."

# Remove the styled links from the footer. Only show thin buttons for Privacy Policy and Disclaimer, side by side, centered. Copyright is centered below.
footer_button_css = """
<style>
.thin-footer-btn button {
    padding: 0.2em 1.2em !important;
    font-size: 0.95em !important;
    min-width: 110px !important;
    margin: 0 8px 0 0 !important;
}
.footer-copyright {
    text-align: center;
    color: #888;
    font-size: 0.95em;
    margin-top: 0.7em;
}
</style>
"""
st.markdown(footer_button_css, unsafe_allow_html=True)

colA, colB, colC = st.columns([4,1,4])
with colB:
    btn_col1, btn_col2 = st.columns([1,1])
    with btn_col1:
        with st.container():
            st.markdown('<div class="thin-footer-btn">', unsafe_allow_html=True)
            if st.button("Privacy Policy", key="privacy_btn", help="Show Privacy Policy"):
                st.session_state['show_privacy'] = True
            st.markdown('</div>', unsafe_allow_html=True)
    with btn_col2:
        with st.container():
            st.markdown('<div class="thin-footer-btn">', unsafe_allow_html=True)
            if st.button("Disclaimer", key="disclaimer_btn", help="Show Disclaimer"):
                st.session_state['show_disclaimer'] = True
            st.markdown('</div>', unsafe_allow_html=True)

# Centered copyright below the buttons
st.markdown('<div class="footer-copyright">© 2025 Vishnu Balraj</div>', unsafe_allow_html=True)

if 'show_privacy' not in st.session_state:
    st.session_state['show_privacy'] = False
if 'show_disclaimer' not in st.session_state:
    st.session_state['show_disclaimer'] = False

# Add custom CSS for uniform heading styles in expanders
st.markdown('''<style>
.privacy-main-title, .disclaimer-main-title {
    font-size: 1.7em;
    font-weight: bold;
    margin-bottom: 0.5em;
}
.privacy-expander-content h2, .disclaimer-expander-content h2 {
    font-size: 1.25em !important;
    font-weight: bold !important;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
}
.privacy-expander-content h3, .disclaimer-expander-content h3 {
    font-size: 1.1em !important;
    font-weight: bold !important;
    margin-top: 1em;
    margin-bottom: 0.4em;
}
.privacy-expander-content, .disclaimer-expander-content {
    font-size: 1em;
    color: #fff;
    max-width: 800px;
    margin: auto;
}
</style>''', unsafe_allow_html=True)

if st.session_state.get('show_privacy', False):
    with st.expander("Privacy Policy", expanded=True):
        privacy_md = PRIVACY_TEXT
        privacy_md = re.sub(r'^#+\s*Privacy Policy\s*\n', '', privacy_md, flags=re.IGNORECASE)
        st.markdown('<div class="privacy-main-title">Privacy Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="privacy-expander-content">', unsafe_allow_html=True)
        st.markdown(privacy_md, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Close", key="close_privacy"):
            st.session_state['show_privacy'] = False
            st.rerun()

if st.session_state.get('show_disclaimer', False):
    with st.expander("Disclaimer", expanded=True):
        disclaimer_md = """
**Disclaimer:**

The creators of this tool do not guarantee that photos generated will be accepted by any passport-issuing agency or government. Official passport photo requirements may change and can vary by country or application. It is the user's responsibility to verify that their final photo meets the current official requirements for their specific use case. The creators are not liable for any rejection, loss, or damages resulting from use of this software.
"""
        st.markdown('<div class="disclaimer-main-title">Disclaimer</div>', unsafe_allow_html=True)
        st.markdown('<div class="disclaimer-expander-content">', unsafe_allow_html=True)
        st.markdown(disclaimer_md, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Close", key="close_disclaimer"):
            st.session_state['show_disclaimer'] = False
            st.rerun()