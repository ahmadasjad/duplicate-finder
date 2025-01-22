import streamlit as st
from PIL import Image
import fitz  # PyMuPDF

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
