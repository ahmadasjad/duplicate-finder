import streamlit as st
from app.file_operations import scan_directory, delete_selected_files
from app.utils import get_file_info, human_readable_size
from app.preview import preview_file_inline

def run_app():
    """
    Main function to run the Streamlit app.
    """
    st.title("Duplicate File Finder")

    # Initialize session state
    if 'duplicates' not in st.session_state:
        st.session_state.duplicates = None

    # Input directory for scanning
    directory = st.text_input("Enter directory path:")
    if not directory:
        st.warning("Please enter a directory to scan.")
        return

    # Scan for duplicates
    if st.button("Scan for Duplicates"):
        st.session_state.duplicates = scan_directory(directory)
        if st.session_state.duplicates:
            st.success(f"Found {len(st.session_state.duplicates)} groups of duplicates.")
        else:
            st.info("No duplicate files found.")

    # Display duplicates if they exist
    if st.session_state.duplicates:
        display_file_groups(st.session_state.duplicates)

def display_file_groups(duplicates):
    """
    Render duplicate file groups in the UI.
    :param duplicates: Dictionary of duplicate file groups
    """
    st.header("Duplicate Files")
    if not duplicates:
        st.write("No duplicates to display.")
        return

    # Initialize pagination state
    if 'page' not in st.session_state:
        st.session_state.page = 0
        
    # Pagination controls
    groups = list(duplicates.values())
    total_groups = len(groups)
    groups_per_page = 1
    total_pages = (total_groups + groups_per_page - 1) // groups_per_page
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.write(f"Page {st.session_state.page + 1} of {total_pages}")
    with col2:
        # Only show Previous button if not on first page
        if st.session_state.page > 0:
            if st.button("Previous"):
                st.session_state.page -= 1
                st.rerun()
        
        # Only show Next button if not on last page
        if st.session_state.page < total_pages - 1:
            if st.button("Next"):
                st.session_state.page += 1
                st.rerun()

    selected_files = []  # Collect files marked for deletion

    # Display groups for current page
    start_idx = st.session_state.page * groups_per_page
    end_idx = min(start_idx + groups_per_page, total_groups)
    
    for group_idx in range(start_idx, end_idx):
        files = groups[group_idx]
        group_id = group_idx + 1
        
        st.subheader(f"Group {group_id}")

        for file in files:
            file_info = get_file_info(file)
            human_size = human_readable_size(file_info["size"])

            # Create 3-column layout
            col1, col2, col3 = st.columns([0.5, 1, 2])
            
            with col1:
                # Checkbox for deletion
                if st.checkbox(f"Delete", key=f"delete-{file}"):
                    selected_files.append(file)
                    
            with col2:
                # Inline preview
                preview_file_inline(file)
                
            with col3:
                # File details in single line
                st.markdown(f"**File:** {file_info['name']} \n\n **Path:** {file} \n\n **Ext:** {file_info['extension']} \n\n **Size:** {human_size} \n\n **Created:** {file_info['created']} \n\n **Modified:** {file_info['modified']}")

    # Perform deletion
    if selected_files:
        if st.button("Delete Selected Files"):
            # Check if any group would be completely deleted
            deletion_allowed = True
            for group_id, files in duplicates.items():
                # Count how many files in this group are selected for deletion
                selected_in_group = sum(1 for f in files if f in selected_files)
                if selected_in_group == len(files):
                    st.error(f"Cannot delete all files in Group {group_id}. At least one file must remain.")
                    deletion_allowed = False
                    break
            
            if deletion_allowed:
                delete_selected_files(selected_files)
                st.success(f"Deleted {len(selected_files)} files.")
                
                # Remove deleted files from duplicates
                for group_id, files in list(duplicates.items()):
                    duplicates[group_id] = [f for f in files if f not in selected_files]
                    if not duplicates[group_id] or len(duplicates[group_id]) == 1:  # Remove empty groups
                        del duplicates[group_id]
                
                # Update session state and trigger rerun
                st.session_state.duplicates = duplicates
                st.rerun()
