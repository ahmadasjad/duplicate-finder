import streamlit as st
from app.file_operations import scan_directory, delete_selected_files
from app.utils import get_file_info, human_readable_size
from app.preview import preview_file_inline
from app.storage_providers import get_storage_providers, get_provider_info

# Set page configuration to wide mode
st.set_page_config(
    page_title="Duplicate File Finder",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

def run_app():
    """
    Main function to run the Streamlit app.
    """
    st.title("Duplicate File Finder")

    # Initialize session state
    if 'duplicates' not in st.session_state:
        st.session_state.duplicates = None
    if 'selected_provider' not in st.session_state:
        st.session_state.selected_provider = None

    # Sidebar for storage provider selection
    with st.sidebar:
        st.header("Storage Provider")
        providers = get_storage_providers()
        provider_info = get_provider_info()

        if not providers:
            st.error("No storage providers are currently enabled. Please check the configuration.")
            return

        provider_names = list(providers.keys())

        selected_provider_name = st.selectbox(
            "Choose where to scan for duplicates:",
            provider_names,
            index=0,
            key="provider_selector"
        )

        # Initialize pagination settings
        if 'per_page' not in st.session_state:
            st.session_state.per_page = 5

        # Per page selection
        st.subheader("Display Settings")
        per_page_options = [1, 5, 10, 20]
        st.selectbox(
            "Items per page",
            options=per_page_options,
            index=per_page_options.index(st.session_state.per_page),
            key="items_per_page",
            on_change=lambda: setattr(st.session_state, 'per_page', st.session_state.items_per_page)
        )

        # Show provider description
        info = provider_info.get(selected_provider_name, {})
        # description = info.get("description", "No description available")
        # st.info(description)

        # Get the selected provider instance to check authentication status
        selected_provider = providers[selected_provider_name]

        # Show authentication status only if not authenticated
        if info.get("requires_auth", False) and not selected_provider.authenticate():
            st.caption("⚠️ Authentication required")
        # else:
        #     st.caption("✅ No authentication required")

    # Get the selected provider instance
    selected_provider = providers[selected_provider_name]
    st.session_state.selected_provider = selected_provider

    # Show provider-specific authentication if needed
    if not selected_provider.authenticate():
        st.warning(f"Authentication required for {selected_provider_name}")
        # For Google Drive, still show the directory widget to handle auth UI
        if selected_provider.name != "Google Drive":
            return

    # Get directory input widget from provider
    directory_widget = selected_provider.get_directory_input_widget()
    if directory_widget is None:
        return  # Provider not ready (e.g., needs authentication)

    directory = directory_widget
    if not directory:
        st.warning("Please enter a directory to scan.")
        return

    # Filter options
    st.subheader("Scan Options")
    with st.expander("Advanced Filters", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            exclude_shortcuts = st.checkbox("Exclude shortcuts and symlinks", value=True)
            exclude_hidden = st.checkbox("Exclude hidden files", value=True)
        with col2:
            exclude_system = st.checkbox("Exclude system files", value=True)
            min_size = st.number_input("Minimum file size (KB)", min_value=0, value=0)
            max_size = st.number_input("Maximum file size (KB)", min_value=0, value=0)

    # Scan for duplicates
    if st.button("Scan for Duplicates", type="primary"):
        with st.spinner("Scanning for duplicates..."):
            st.session_state.duplicates = selected_provider.scan_directory(
                directory,
                exclude_shortcuts=exclude_shortcuts,
                exclude_hidden=exclude_hidden,
                exclude_system=exclude_system,
                min_size_kb=min_size,
                max_size_kb=max_size
            )
        if st.session_state.duplicates:
            # Get total duplicate count
            total_duplicates = sum(len(group) for group in st.session_state.duplicates.values())

            # Use custom success message if provider implements it
            # if hasattr(selected_provider, 'get_scan_success_msg'):
            st.success(selected_provider.get_scan_success_msg(
                len(st.session_state.duplicates),
                total_duplicates
            ))
            # else:
            #     st.success(f"Found {len(st.session_state.duplicates)} groups of duplicates.")
        else:
            st.info("No duplicate files found.")

    # Add scan statistics to sidebar
    if st.session_state.duplicates:
        with st.sidebar:
            st.markdown("---")
            st.subheader("Scan Results")

            # Calculate statistics
            total_groups = len(st.session_state.duplicates)
            total_duplicates = sum(len(group) for group in st.session_state.duplicates.values())
            total_files = total_duplicates
            duplicate_files = total_files - total_groups  # Subtract one original per group

            st.metric("Duplicate Groups", total_groups)
            st.metric("Total Files", total_files)
            st.metric("Duplicate Files", duplicate_files)

            if total_files > 0:
                savings_percentage = (duplicate_files / total_files) * 100
                st.metric("Potential Savings", f"{savings_percentage:.1f}%")

    # Display duplicates if they exist
    if st.session_state.duplicates:
        display_file_groups(st.session_state.duplicates, selected_provider)

def display_file_groups(duplicates, storage_provider):
    """
    Render duplicate file groups in the UI.
    :param duplicates: Dictionary of duplicate file groups
    :param storage_provider: Storage provider instance
    """
    st.divider()
    st.header("Duplicate Files")
    if not duplicates:
        st.write("No duplicates to display.")
        return

    # Initialize pagination state
    if 'page' not in st.session_state:
        st.session_state.page = 0
    if 'per_page' not in st.session_state:
        st.session_state.per_page = 5

    # Pagination controls
    groups = list(duplicates.values())
    total_groups = len(groups)

    # Sidebar controls
    with st.sidebar:
        # Per page selection - Removed from here since it's now in the sidebar at the top
        # Reset page if per_page changes
        if 'per_page' in st.session_state and st.session_state.get('items_per_page') != st.session_state.per_page:
            st.session_state.per_page = st.session_state.items_per_page
            st.session_state.page = 0
            st.rerun()

    total_pages = (total_groups + st.session_state.per_page - 1) // st.session_state.per_page

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
    start_idx = st.session_state.page * st.session_state.per_page
    end_idx = min(start_idx + st.session_state.per_page, total_groups)

    for group_idx in range(start_idx, end_idx):
        files = groups[group_idx]
        group_id = group_idx + 1

        # Calculate group statistics
        total_files_in_group = len(files)
        group_file_info = storage_provider.get_file_info(files[0])
        group_size = human_readable_size(group_file_info["size"])
        wasted_space = human_readable_size(group_file_info['size'] * (total_files_in_group - 1))

        # Use Streamlit's expander for a clear group container with info styling
        st.markdown(
            """
            <style>
            .stExpander summary {
                background-color: rgb(187, 222, 251); /* Change this to your desired color */
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        expander_header = f"🗂️ Duplicate Group {group_id} - {total_files_in_group} files ({group_size} each) | 💾 Total wasted space: {wasted_space}"
        with st.expander(expander_header, expanded=True,):
            # Display as info message
            # st.info(expander_header)

            # Files in this group with numbered display
            for file_idx, file in enumerate(files, 1):
                file_info = storage_provider.get_file_info(file)
                human_size = human_readable_size(file_info["size"])

                # Create a container for each file with bottom border only
                with st.container():
                    # Create 3-column layout: checkbox, preview, details
                    col1, col2, col3 = st.columns([2, 4, 6])

                    with col1:
                        st.badge(f"📄 File #{file_idx}")
                        # Checkbox for deletion
                        if st.checkbox(f"Delete this file", key=f"delete-{file}"):
                            selected_files.append(file)

                    with col2:
                        # Inline preview
                        storage_provider.preview_file(file)

                    with col3:
                        # File details
                        full_path = storage_provider.get_file_path(file)
                        st.markdown(f"""
                        <div style="margin: 0; line-height: 1.6;">
                            <p style="margin-bottom: 10px; font-weight: bold; color: #1f2937; font-size: 16px;">📄 {file_info['name']}</p>
                            <p style="margin-bottom: 10px; color: #6b7280; font-size: 12px; background-color: #f3f4f6; padding: 6px 10px; border-radius: 6px;">📁 {full_path}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # File metadata in a compact layout
                        meta_col1, meta_col2 = st.columns(2)
                        with meta_col1:
                            st.markdown(f"**📏 Size:** {human_size}")
                            st.markdown(f"**🏷️ Type:** {file_info['extension']}")
                        with meta_col2:
                            st.markdown(f"**📅 Created:** {file_info['created']}")
                            st.markdown(f"**✏️ Modified:** {file_info['modified']}")

                        # Add provider-specific extra info and action links
                        if hasattr(storage_provider, 'get_file_extra_info'):
                            extra_info = storage_provider.get_file_extra_info(file)
                            if extra_info.get('links'):
                                st.markdown("**Actions:**")
                                action_cols = st.columns(len(extra_info.get('links', [])))
                                for col, link in zip(action_cols, extra_info.get('links', [])):
                                # for link in extra_info.get('links', []):
                                    with col:
                                        st.markdown(f"**[{link['text']}]({link['url']})**")

                    # Add divider only if not the last file in the group
                    if file_idx < len(files):
                        st.divider()

        # Add spacing between groups
        st.markdown("<br>", unsafe_allow_html=True)


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
                success = storage_provider.delete_files(selected_files)
                if success:
                    st.success(f"Deleted {len(selected_files)} files.")

                    # Remove deleted files from duplicates
                    for group_id, files in list(duplicates.items()):
                        duplicates[group_id] = [f for f in files if f not in selected_files]
                        if not duplicates[group_id] or len(duplicates[group_id]) == 1:  # Remove empty groups
                            del duplicates[group_id]

                    # Update session state and trigger rerun
                    st.session_state.duplicates = duplicates
                    st.rerun()
                else:
                    st.error("Failed to delete some files. Please check permissions.")
