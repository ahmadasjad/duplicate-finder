import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
import pdfplumber
import os


def preview_file(file_path):
    """
    Render file preview and metadata in Streamlit.
    """
    st.markdown(f"### Preview for: {os.path.basename(file_path)}")

    # Preview based on file type
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        image = Image.open(file_path)
        st.image(image, caption=os.path.basename(file_path), use_column_width=True)

    elif file_path.lower().endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages[:3]):  # Limit to first 3 pages
                st.image(page.to_image().render(), caption=f"Page {i + 1}", use_column_width=True)

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