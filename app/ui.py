import streamlit as st
from app.file_operations import scan_directory, delete_selected_files
from app.utils import get_file_info, human_readable_size
from app.preview import preview_file_inline
from app.storage_providers import get_storage_providers, get_provider_info

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

        # Show provider description
        info = provider_info.get(selected_provider_name, {})
        description = info.get("description", "No description available")
        st.info(description)

        # Show provider status/requirements
        if info.get("requires_auth", False):
            st.caption("⚠️ Requires authentication")
        else:
            st.caption("✅ No authentication required")

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
            st.success(f"Found {len(st.session_state.duplicates)} groups of duplicates.")
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
        # Per page selection
        per_page_options = [1, 5, 10, 20]
        new_per_page = st.selectbox(
            "Items per page",
            options=per_page_options,
            index=per_page_options.index(st.session_state.per_page)
        )

        # Reset page if per_page changes
        if new_per_page != st.session_state.per_page:
            st.session_state.per_page = new_per_page
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

        st.subheader(f"Group {group_id}")

        for file in files:
            file_info = storage_provider.get_file_info(file)
            human_size = human_readable_size(file_info["size"])

            # Create 3-column layout: checkbox, preview, details
            col1, col2, col3 = st.columns([2, 4, 6])

            with col1:
                # Checkbox for deletion
                if st.checkbox(f"Delete", key=f"delete-{file}"):
                    selected_files.append(file)

            with col2:
                # Inline preview
                storage_provider.preview_file(file)

            with col3:
                # File details
                full_path = storage_provider.get_file_path(file)
                st.markdown(f"""
                <div style="margin: 0; line-height: 1;">
                <p style="margin-bottom: 2px;"><b>File:</b> {file_info['name']}</p>
                <p style=""><b>Path:</b> {full_path}</p>
                </div>
                """, unsafe_allow_html=True)
                size_col, ext_col = st.columns(2)
                with size_col:
                    st.write(f"**Size:** {human_size}")
                with ext_col:
                    st.write(f"**Ext:** {file_info['extension']}")
                st.markdown(f"""
                <div style="margin: 0; line-height: 1;">
                <p style="margin-bottom: 2px;"><b>Created at:</b> {file_info['created']}</p>
                <p><b>Last modified at:</b> {file_info['modified']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Add provider-specific extra info and action links
                if hasattr(storage_provider, 'get_file_extra_info'):
                    extra_info = storage_provider.get_file_extra_info(file)
                    for link in extra_info.get('links', []):
                        st.markdown(f"**[{link['text']}]({link['url']})**")


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
