"""Preview utilities for files."""

import os
import io

import fitz  # PyMuPDF
from PIL import Image
import streamlit as st

def preview_file_inline(file_path):
    """
    Render file preview and metadata in Streamlit inline.
    """
    # st.markdown(f"#### Preview for: {os.path.basename(file_path)}")

    # Preview based on file type
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        image = Image.open(file_path)
        st.image(image, caption=os.path.basename(file_path), use_container_width=True)

    elif file_path.lower().endswith('.pdf'):
        with fitz.open(file_path) as pdf:
            if len(pdf) > 0:  # Make sure PDF has at least one page
                page = pdf[0]  # Get first page
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_bytes = io.BytesIO(pix.tobytes(output="png"))
                st.image(img_bytes, caption="First page", use_column_width=True)

    else:
        st.warning("Preview not available for this file type.")
