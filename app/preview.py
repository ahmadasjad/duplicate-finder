import os
from PIL import Image
import pdfplumber
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
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages[:3]):  # Limit to first 3 pages
                # Convert page to image and get PNG bytes using BytesIO
                import io
                img_bytes = io.BytesIO()
                page.to_image().save(img_bytes, format='PNG')
                img_bytes.seek(0)
                st.image(img_bytes, caption=f"Page {i + 1}", use_container_width=True)

    else:
        st.warning("Preview not available for this file type.")
