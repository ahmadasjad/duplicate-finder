"""UI components and logic."""

import logging

import streamlit as st

from app.utils import human_readable_size
from app.storage_providers import get_storage_providers, get_provider_info
from app.storage_providers.base import ScanFilterOptions
from app.storage_providers.exceptions import NoDuplicateException, NoFileFoundException

logger = logging.getLogger(__name__)


class DuplicateFinderUI:
    """UI class for rendering and managing the Duplicate File Finder app."""

    def __init__(self):
        self.setup_page_config()
        self.init_session_state()

    def setup_page_config(self):
        """Configure the Streamlit page settings."""
        st.set_page_config(
            page_title="Duplicate File Finder",
            page_icon="📂",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def init_session_state(self):
        """Initialize session state variables."""
        if 'duplicates' not in st.session_state:
            st.session_state.duplicates = None
        if 'selected_provider' not in st.session_state:
            st.session_state.selected_provider = None
        if 'previous_provider' not in st.session_state:
            st.session_state.previous_provider = None
        if 'per_page' not in st.session_state:
            st.session_state.per_page = 5
        if 'page' not in st.session_state:
            st.session_state.page = 0

    def render_sidebar(self, providers, provider_info):
        """Render the sidebar with provider selection and display settings."""
        with st.sidebar:
            st.header("Storage Provider")

            if not providers:
                st.error("No storage providers are currently enabled. Please check the configuration.")
                return None

            provider_names = list(providers.keys())
            selected_provider_name = st.selectbox(
                "Choose where to scan for duplicates:",
                provider_names,
                index=0,
                key="provider_selector"
            )

            # Reset duplicates if provider changes
            if (st.session_state.previous_provider is not None and
                st.session_state.previous_provider != selected_provider_name):
                st.session_state.duplicates = None
                st.session_state.page = 0
                if 'is_authenticated' in st.session_state:
                    del st.session_state.is_authenticated  # Clear authentication status

            st.session_state.previous_provider = selected_provider_name

            self.render_display_settings()

            # Show authentication status
            selected_provider = providers[selected_provider_name]
            info = provider_info.get(selected_provider_name, {})
            if info.get("requires_auth", False) and not selected_provider.authenticate():
                st.caption("⚠️ Authentication required")

            return selected_provider_name

    def render_display_settings(self):
        """Render the display settings in the sidebar."""
        st.subheader("Display Settings")
        per_page_options = [1, 5, 10, 20]
        st.selectbox(
            "Items per page",
            options=per_page_options,
            index=per_page_options.index(st.session_state.per_page),
            key="items_per_page",
            on_change=lambda: setattr(st.session_state, 'per_page', st.session_state.items_per_page)
        )

    def render_scan_options(self):
        """Render the scan options UI and return a ScanFilterOptions object."""
        st.subheader("Scan Options")
        with st.expander("Advanced Filters", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                include_subfolders = st.checkbox(
                    "🔄 Include subfolders (recursive scan)",
                    value=True,
                    help="Scan all subfolders within the selected folder"
                )
                exclude_shortcuts = st.checkbox("Exclude shortcuts and symlinks", value=True)
                exclude_hidden = st.checkbox("Exclude hidden files", value=True)
            with col2:
                exclude_system = st.checkbox("Exclude system files", value=True)
                min_size = st.number_input("Minimum file size (KB)", min_value=0, value=0)
                max_size = st.number_input("Maximum file size (KB)", min_value=0, value=0)

        return ScanFilterOptions(
            exclude_shortcuts=exclude_shortcuts,
            exclude_hidden=exclude_hidden,
            exclude_system=exclude_system,
            min_size_kb=min_size,
            max_size_kb=max_size,
            include_subfolders=include_subfolders
        )

    def render_scan_statistics(self, duplicates):
        """Render the scan statistics in the sidebar."""
        with st.sidebar:
            st.markdown("---")
            st.subheader("Scan Results")

            total_groups = len(duplicates)
            total_duplicates = sum(len(group) for group in duplicates.values())
            total_files = total_duplicates
            duplicate_files = total_files - total_groups

            st.metric("Duplicate Groups", total_groups)
            st.metric("Total Files", total_files)
            st.metric("Duplicate Files", duplicate_files)

            if total_files > 0:
                savings_percentage = (duplicate_files / total_files) * 100
                st.metric("Potential Savings", f"{savings_percentage:.1f}%")

    def render_file_group(self, group_idx, files, storage_provider):
        """Render a single group of duplicate files."""
        group_id = group_idx + 1
        selected_files = []

        # Calculate group statistics
        total_files_in_group = len(files)
        group_file_info = storage_provider.get_file_info(files[0])
        group_size = human_readable_size(group_file_info["size"])
        wasted_space = human_readable_size(group_file_info['size'] * (total_files_in_group - 1))

        expander_header = f"🗂️ Duplicate Group {group_id} - {total_files_in_group} files ({group_size} each) | 💾 Total wasted space: {wasted_space}"
        with st.expander(expander_header, expanded=True):
            total_files = len(files)
            for file_idx, file in enumerate(files, 1):
                if self.render_file_item(file_idx, file, storage_provider, total_files):
                    selected_files.append(file)

        return selected_files

    def render_file_item(self, file_idx, file, storage_provider, total_files):
        """Render a single file item within a group."""
        file_info = storage_provider.get_file_info(file)
        human_size = human_readable_size(file_info["size"])

        with st.container():
            col1, col2, col3 = st.columns([2, 4, 6])

            with col1:
                st.badge(f"📄 File #{file_idx}")
                selected = st.checkbox(f"Delete this file", key=f"delete-{file}")

            with col2:
                storage_provider.preview_file(file)

            with col3:
                self.render_file_details(file, file_info, human_size, storage_provider)

            if file_idx < total_files:
                st.divider()

        return selected

    def render_file_details(self, file, file_info, human_size, storage_provider):
        """Render the details of a single file."""
        full_path = storage_provider.get_file_path(file)
        st.markdown(f"""
        <div style="margin: 0; line-height: 1.6;">
            <p style="margin-bottom: 10px; font-weight: bold; color: #1f2937; font-size: 16px;">📄 {file_info['name']}</p>
            <p style="margin-bottom: 10px; color: #6b7280; font-size: 12px; background-color: #f3f4f6; padding: 6px 10px; border-radius: 6px;">📁 {full_path}</p>
        </div>
        """, unsafe_allow_html=True)

        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.markdown(f"**📏 Size:** {human_size}")
            st.markdown(f"**🏷️ Type:** {file_info['extension']}")
        with meta_col2:
            st.markdown(f"**📅 Created:** {file_info['created']}")
            st.markdown(f"**✏️ Modified:** {file_info['modified']}")

        # Provider-specific extra info
        if hasattr(storage_provider, 'get_file_extra_info'):
            self.render_extra_info(file, storage_provider)

    def render_extra_info(self, file, storage_provider):
        """Render provider-specific extra information."""
        extra_info = storage_provider.get_file_extra_info(file)
        if extra_info.get('links'):
            st.markdown("**Actions:**")
            action_cols = st.columns(len(extra_info.get('links', [])))
            for col, link in zip(action_cols, extra_info.get('links', [])):
                with col:
                    st.markdown(f"**[{link['text']}]({link['url']})**")

    def render_pagination(self, total_groups, position="top"):
        """Render pagination controls.

        Args:
            total_groups (int): Total number of groups
            position (str): Position of pagination controls ("top" or "bottom")
        """
        total_pages = (total_groups + st.session_state.per_page - 1) // st.session_state.per_page

        col1, col2 = st.columns([1, 3])
        with col1:
            st.write(f"Page {st.session_state.page + 1} of {total_pages}")
        with col2:
            if st.session_state.page > 0:
                if st.button("Previous", key=f"prev_{position}"):
                    st.session_state.page -= 1
                    st.rerun()

            if st.session_state.page < total_pages - 1:
                if st.button("Next", key=f"next_{position}"):
                    st.session_state.page += 1
                    st.rerun()

    def handle_file_deletion(self, selected_files, duplicates, storage_provider):
        """Handle the deletion of selected files."""
        if not selected_files:
            return

        if st.button("Delete Selected Files"):
            # Check if any group would be completely deleted
            deletion_allowed = True
            for group_id, files in duplicates.items():
                selected_in_group = sum(1 for f in files if f in selected_files)
                if selected_in_group == len(files):
                    st.error(f"Cannot delete all files in Group {group_id}. At least one file must remain.")
                    deletion_allowed = False
                    break

            if deletion_allowed:
                if storage_provider.delete_files(selected_files):
                    st.success(f"Deleted {len(selected_files)} files.")

                    # Update duplicates
                    for group_id, files in list(duplicates.items()):
                        duplicates[group_id] = [f for f in files if f not in selected_files]
                        if not duplicates[group_id] or len(duplicates[group_id]) == 1:
                            del duplicates[group_id]

                    st.session_state.duplicates = duplicates
                    st.rerun()
                else:
                    st.error("Failed to delete some files. Please check permissions.")

    def run(self):
        """Main method to run the Streamlit app."""
        st.title("Duplicate File Finder")

        providers = get_storage_providers()
        provider_info = get_provider_info()

        selected_provider_name = self.render_sidebar(providers, provider_info)
        if not selected_provider_name:
            return

        selected_provider = providers[selected_provider_name]
        st.session_state.selected_provider = selected_provider

        # Move authentication check to session state to avoid multiple checks
        if 'is_authenticated' not in st.session_state:
            st.session_state.is_authenticated = selected_provider.authenticate()

        if not st.session_state.is_authenticated:
            st.warning(f"Authentication required for {selected_provider_name}")
            if selected_provider.name != "Google Drive":
                return

        directory_widget = selected_provider.get_directory_input_widget()
        if directory_widget is None:
            return

        directory = directory_widget
        if not directory:
            st.warning("Please enter a directory to scan.")
            return

        scan_options = self.render_scan_options()
        # scan_options is now a ScanFilterOptions object
        if st.button("Scan for Duplicates", type="primary"):
            st.divider()
            try:
                with st.spinner("Scanning for duplicates..."):
                    st.session_state.duplicates = selected_provider.scan_directory(
                        directory,
                        scan_options
                    )

                if st.session_state.duplicates:
                    total_duplicates = sum(len(group) for group in st.session_state.duplicates.values())
                    st.success(selected_provider.get_scan_success_msg(
                        len(st.session_state.duplicates),
                        total_duplicates
                    ))
            except (NoDuplicateException, NoFileFoundException) as e:
                st.info(str(e))
                st.session_state.duplicates = None


        if st.session_state.duplicates:
            self.render_scan_statistics(st.session_state.duplicates)
            self.display_file_groups(st.session_state.duplicates, selected_provider)

    def display_file_groups(self, duplicates, storage_provider):
        """Display the duplicate file groups with pagination."""
        st.divider()
        st.header("Duplicate Files")
        if not duplicates:
            st.write("No duplicates to display.")
            return

        groups = list(duplicates.values())
        total_groups = len(groups)

        # Top pagination
        self.render_pagination(total_groups, "top")

        selected_files = []
        start_idx = st.session_state.page * st.session_state.per_page
        end_idx = min(start_idx + st.session_state.per_page, total_groups)

        for group_idx in range(start_idx, end_idx):
            selected = self.render_file_group(group_idx, groups[group_idx], storage_provider)
            selected_files.extend(selected)
            st.markdown("<br>", unsafe_allow_html=True)

        # Bottom pagination
        st.divider()
        self.render_pagination(total_groups, "bottom")

        self.handle_file_deletion(selected_files, duplicates, storage_provider)

def run_app():
    """Entry point for the Streamlit application."""
    app = DuplicateFinderUI()
    app.run()
