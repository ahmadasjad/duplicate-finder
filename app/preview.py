import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
import pdfplumber
import os

def preview_file(file_path):
    """Render file preview and metadata."""
    st.markdown(f"### File: {file_path}")
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        image = Image.open(file_path)
        st.image(image)
    elif file_path.lower().endswith('.pdf'):
        doc = fitz.open(file_path)
        for page in doc:
            st.image(page.get_pixmap().get_image_data())
    else:
        st.warning("Preview not available for this file type.")

def generate_preview(file_path):
    extension = os.path.splitext(file_path)[-1].lower()

    if extension in ['.jpg', '.jpeg', '.png']:
        return Image.open(file_path)  # PIL Image object for Streamlit
    elif extension == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            first_page = pdf.pages[0]
            return first_page.to_image()  # Convert first page to image
    else:
        return None  # No preview available