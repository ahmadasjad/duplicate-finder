import streamlit as st
from app.file_operations import scan_directory, delete_selected_files
from app.preview import preview_file

def run_app():
    """
    Main function to run the Streamlit app.
    """
    st.title("Duplicate File Finder")

    # Input directory for scanning
    directory = st.text_input("Enter directory path:")
    if not directory:
        st.warning("Please enter a directory to scan.")
        return

    # Scan for duplicates
    if st.button("Scan for Duplicates"):
        duplicates = scan_directory(directory)
        display_file_groups(duplicates)

    if st.button("Delete Selected"):
        selected_files = collect_selected_files(duplicates)  # Collect files marked for deletion
        delete_selected_files(selected_files)

def display_file_groups(duplicates):
    """Render duplicate file groups."""
    for group_id, files in enumerate(duplicates.values(), start=1):
        st.markdown(f"### Group {group_id}")
        for file in files:
            if st.checkbox(file, key=f"{group_id}-{file}"):
                st.button("Preview", on_click=preview_file, args=(file,))
