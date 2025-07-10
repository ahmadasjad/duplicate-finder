"""Preview utilities for files."""

import os
import io
import mimetypes

import fitz  # PyMuPDF
from PIL import Image
import streamlit as st

def analyze_file_type(content):
    """
    Analyze and determine the file type from content using file signatures.

    Args:
        content (bytes): File content as bytes

    Returns:
        str: Normalized file extension (e.g., '.pdf', '.png') or None if unknown
    """
    if not content:
        return None

    try:
        import magic
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(content)
        return mimetypes.guess_extension(mime_type)
    except ImportError:
        st.error("python-magic is not installed. Please install it for proper file type detection.")
        return None
    except Exception as e:
        st.warning(f"Error detecting file type: {str(e)}")
        return None

def preview_file_inline(file_path, *, title=None):
    """
    Render file preview and metadata in Streamlit inline.
    """

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
                caption = title if title else "First page"
                st.image(img_bytes, caption=caption, use_container_width=True)

    else:
        st.warning("Preview not available for this file type.")

def preview_blob_inline(blob_content, file_type=None, *, title=None):
    """
    Render file preview from blob content (bytes) in Streamlit inline.

    Args:
        blob_content (bytes): The file content as bytes
        file_type (str, optional): File type/extension (e.g., 'pdf', 'png').
            If not provided, will attempt to guess from content.
    """
    if not blob_content:
        st.warning("No content to preview.")
        return

    # Get or guess file type and remove any leading dot
    file_type = (file_type.lower() if file_type else analyze_file_type(blob_content))
    if file_type:
        file_type = file_type.lstrip('.')

    try:
        # Handle images
        if file_type in ('png', 'jpg', 'jpeg'):
            image = Image.open(io.BytesIO(blob_content))
            st.image(image, use_container_width=True)

        # Handle PDFs
        elif file_type == 'pdf':
            # Create a memory buffer for the PDF
            pdf_stream = io.BytesIO(blob_content)

            with fitz.open(stream=pdf_stream, filetype="pdf") as pdf:
                if len(pdf) > 0:  # Make sure PDF has at least one page
                    page = pdf[0]  # Get first page
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                    img_bytes = io.BytesIO(pix.tobytes(output="png"))
                    caption = title if title else "First page"
                    st.image(img_bytes, caption=caption, use_container_width=True)

        else:
            st.warning("Preview not available for this file type.")

    except Exception as e:
        st.error(f"Error previewing content: {str(e)}")
