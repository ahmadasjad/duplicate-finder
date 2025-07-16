"""UI components and logic."""

import logging
import pandas as pd

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

        # Similarity Detection Section
        with st.expander("🔍 Similarity Detection", expanded=True):
            st.markdown("**Configure how similar files should be to be considered duplicates:**")

            enable_similarity = st.checkbox(
                "Enable similarity-based detection",
                value=False,
                help="Find files that are similar but not necessarily identical"
            )

            if enable_similarity:
                similarity_threshold = st.select_slider(
                    "Similarity threshold",
                    options=[1.0, 0.99, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70],
                    value=0.95,
                    format_func=lambda x: f"{x:.0%}" if x == 1.0 else f"{x:.0%}",
                    help="Higher values require more similarity to consider files as duplicates"
                )

                st.markdown("**Similarity methods to use:**")
                col1, col2 = st.columns(2)
                with col1:
                    enable_perceptual = st.checkbox(
                        "Visual similarity (images)",
                        value=True,
                        help="Compare images based on visual appearance"
                    )
                    enable_content = st.checkbox(
                        "Content similarity (text/binary)",
                        value=True,
                        help="Compare file content for text and binary files"
                    )
                with col2:
                    enable_image_structure = st.checkbox(
                        "Image structure similarity",
                        value=True,
                        help="Compare images based on structural features"
                    )
                    enable_filename = st.checkbox(
                        "Filename similarity",
                        value=False,
                        help="Consider files with similar names as potential duplicates"
                    )
            else:
                similarity_threshold = 1.0
                enable_perceptual = True
                enable_content = True
                enable_image_structure = True
                enable_filename = False

        # Advanced Filters Section
        with st.expander("⚙️ Advanced Filters", expanded=False):
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
            include_subfolders=include_subfolders,
            similarity_threshold=similarity_threshold,
            enable_similarity_detection=enable_similarity,
            enable_perceptual_hash=enable_perceptual,
            enable_content_similarity=enable_content,
            enable_image_similarity=enable_image_structure,
            enable_filename_similarity=enable_filename
        )

    def render_scan_statistics(self, duplicates):
        """Render the scan statistics in the sidebar."""
        with st.sidebar:
            st.markdown("---")
            scan_options = getattr(st.session_state, 'scan_options', None)

            if scan_options and scan_options.enable_similarity_detection and scan_options.similarity_threshold < 1.0:
                st.subheader(f"Similarity Results ({scan_options.similarity_threshold:.0%})")
            else:
                st.subheader("Scan Results")

            total_groups = len(duplicates)
            total_duplicates = sum(len(group) for group in duplicates.values())
            total_files = total_duplicates
            duplicate_files = total_files - total_groups

            st.metric("Similar/Duplicate Groups", total_groups)
            st.metric("Total Files", total_files)
            st.metric("Duplicate Files", duplicate_files)

            if total_files > 0:
                savings_percentage = (duplicate_files / total_files) * 100
                st.metric("Potential Savings", f"{savings_percentage:.1f}%")

    def render_file_group(self, group_idx, files, storage_provider):
        """Render a single group of duplicate files using a DataFrame with custom row rendering."""
        selected_files = []

        # Calculate group statistics
        total_files_in_group = len(files)
        group_file_info = storage_provider.get_file_info(files[0])
        group_size = human_readable_size(group_file_info["size"])
        wasted_space = human_readable_size(group_file_info['size'] * (total_files_in_group - 1))

        # Check if similarity detection was used
        scan_options = getattr(st.session_state, 'scan_options', None)
        similarity_info = ""
        if scan_options and scan_options.enable_similarity_detection and scan_options.similarity_threshold < 1.0:
            similarity_info = f" | 🔍 {scan_options.similarity_threshold:.0%} similarity"

        # expander_header = f"🗂️ {'Similar' if similarity_info else 'Duplicate'} Group {group_idx + 1} - {total_files_in_group} files ({group_size} each) | 💾 Total wasted space: {wasted_space}{similarity_info}"
        expander_header = f"🗂️ {'Similar' if similarity_info else 'Duplicate'} Group {group_idx + 1} - {total_files_in_group} files ({group_size} each) | 💾 Total wasted space: {wasted_space}"

        with st.expander(expander_header, expanded=True):
            # Show similarity explanation for the first pair if using similarity detection
            if similarity_info and len(files) >= 2 and hasattr(storage_provider, 'get_similarity_explanation'):
                try:
                    explanation = storage_provider.get_similarity_explanation(files[0], files[1], scan_options)
                    # if explanation and explanation != "Identical files (same hash)":
                    if explanation:
                        st.info(f"**Similarity reason:** {explanation}")
                except Exception as e:
                    logger.debug(f"Error getting similarity explanation: {e}")

            # Create DataFrame for organization
            file_data = []
            for file_idx, file in enumerate(files, 1):
                file.update({'group_id': group_idx})  # Add group ID to file for reference
                file_data.append({
                    'index': file_idx,
                    'file': file,
                })

            df = pd.DataFrame(file_data)

            # Render each row using the existing file_item layout
            for _, row in df.iterrows():
                if self.render_file_item(row['index'], row['file'], storage_provider, total_files_in_group):
                    selected_files.append(row['file'])

        return selected_files

    def render_file_item(self, file_idx, file, storage_provider, total_files):
        """Render a single file item within a group."""
        file_info = storage_provider.get_file_info(file)
        file.update(file_info)  # Update file with additional info
        human_size = human_readable_size(file_info["size"])

        with st.container():
            col1, col2, col3 = st.columns([2, 4, 6])

            with col1:
                st.badge(f"📄 File #{file_idx}")
                selected = st.checkbox(f"Delete this file", key=f"delete-{file}")

            with col2:
                storage_provider.preview_file(file)

            with col3:
                self.render_file_details(file, human_size, storage_provider)

            if file_idx < total_files:
                st.divider()

        return selected

    def render_file_details(self, file, human_size, storage_provider):
        """Render the details of a single file."""
        full_path = storage_provider.get_file_path(file)
        # Generate a unique identifier from file info
        file_id = f"{file.get('name', '')}_{file.get('modified', '')}_{full_path}"

        st.markdown(f"""
        <div style="margin: 0; line-height: 1.6;">
            <p style="margin-bottom: 10px; font-weight: bold; color: #1f2937; font-size: 16px;">📄 {file['name']}</p>
            <p style="margin-bottom: 10px; color: #6b7280; font-size: 12px; background-color: #f3f4f6; padding: 6px 10px; border-radius: 6px;">📁 {full_path}</p>
        </div>
        """, unsafe_allow_html=True)

        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.markdown(f"**📏 Size:** {human_size}")
            st.markdown(f"**🏷️ Type:** {file['extension']}")
        with meta_col2:
            st.markdown(f"**📅 Created:** {file['created']}")
            st.markdown(f"**✏️ Modified:** {file['modified']}")

        # Actions section
        st.markdown("**Actions:**")
        actions_cols = []

        # Start with standard provider-specific extra info
        if hasattr(storage_provider, 'get_file_extra_info'):
            extra_info = storage_provider.get_file_extra_info(file)
            if extra_info.get('links'):
                actions_cols.extend([f"**[{link['text']}]({link['url']})**" for link in extra_info.get('links', [])])

        # Add shortcut button if applicable
        if st.button("Create Shortcut", key=f"shortcut_{file_id}"):
            self.open_shortcut_modal(storage_provider, file)

        # Display all actions in columns
        if actions_cols:
            cols = st.columns(len(actions_cols))
            for col, action in zip(cols, actions_cols):
                with col:
                    st.markdown(action)

    @st.dialog("Create Shortcut")
    def open_shortcut_modal(self, storage_provider, file):
        target_path = storage_provider.get_file_path(file)
        group_files = self.get_files_by_group(file.get('group_id'))
        cleaned_files = [f for f in group_files if f.get('id') != file.get('id')]
        st.markdown(f"**{target_path}** will be deleted and a shortcut will be pointing to ")
        source_file = st.selectbox("Select source file:", label_visibility='collapsed', options=cleaned_files, format_func=lambda f: storage_provider.get_file_path(f))

        if st.button("Create Shortcut", type="primary"):
            if storage_provider.make_shortcut(source_file, file):
                st.success(f"Created shortcut for {file['name']}")
                st.rerun()  # This closes the dialog
            else:
                st.error(f"Failed to create shortcut for {file['name']}")

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
        # Store scan options in session state for later use
        st.session_state.scan_options = scan_options

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
                # else:
                #     st.info("No duplicates found in the selected directory.")
                #     st.session_state.duplicates = None
            except (NoDuplicateException, NoFileFoundException) as e:
                st.info(str(e))
                st.session_state.duplicates = None
            except Exception as e:
                st.error(f"Error during scan")
                st.error("Please check the logs for more details.")
                logger.error("Scan failed with error: %s", str(e), exc_info=True)
                st.session_state.duplicates = None


        if st.session_state.duplicates:
            self.render_scan_statistics(st.session_state.duplicates)
            self.display_file_groups(st.session_state.duplicates, selected_provider)

    def get_files_by_group(self, group_id):
        """Get files by group ID."""
        if 'duplicates' not in st.session_state or st.session_state.duplicates is None:
            logger.warning("No duplicates found in session state.")
            return []

        duplicates = list(st.session_state.duplicates.values())
        if not duplicates:
            logger.warning("No duplicate groups available.")
            return []

        logger.debug(duplicates)
        return duplicates[group_id]

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
