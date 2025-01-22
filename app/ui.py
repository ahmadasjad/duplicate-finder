import streamlit as st
from app.file_operations import scan_directory, delete_selected_files
from app.utils import get_file_info, human_readable_size
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
        if duplicates:
            st.success(f"Found {len(duplicates)} groups of duplicates.")
            display_file_groups(duplicates)
        else:
            st.info("No duplicate files found.")

def display_file_groups(duplicates):
    """
    Render duplicate file groups in the UI.
    :param duplicates: Dictionary of duplicate file groups
    """
    st.header("Duplicate Files")
    if not duplicates:
        st.write("No duplicates to display.")
        return

    selected_files = []  # Collect files marked for deletion

    for group_id, files in enumerate(duplicates.values(), start=1):
        st.subheader(f"Group {group_id}")

        for file in files:
            file_info = get_file_info(file)
            human_size = human_readable_size(file_info["size"])

            # File details
            st.markdown(
                f"""
                **File:** {file_info['name']}  
                **Extension:** {file_info['extension']}  
                **Size:** {human_size}
                """
            )

            # Preview option
            if st.button(f"Preview: {file_info['name']}", key=f"preview-{file}"):
                preview_file(file)

            # Checkbox for deletion
            if st.checkbox(f"Mark for deletion: {file_info['name']}", key=f"delete-{file}"):
                selected_files.append(file)

    # Perform deletion
    if selected_files:
        if st.button("Delete Selected Files"):
            delete_selected_files(selected_files)
            st.success(f"Deleted {len(selected_files)} files.")

