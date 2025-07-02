"""Google Drive authentication handler for OAuth2 flow.

This module handles the authentication process with Google Drive API,
including token generation, refresh, and validation.
"""

import logging
import os
from abc import ABC

import streamlit as st
from googleapiclient.discovery import build

from .google_utils import GoogleService

logger = logging.getLogger(__name__)


class GoogleAuthenticator(ABC):
    """Handles Google Drive OAuth2 authentication and user info retrieval."""
    def __init__(self):
        self.google_service = GoogleService()

    def _perform_oauth_flow(self):
        """Perform OAuth flow directly in the application"""
        st.markdown("### 🔐 Google Drive Authentication")

        # Generate auth URL
        auth_url, error = self.google_service.generate_auth_url()
        if error:
            st.error(f"Failed to generate authentication URL: {error}")
            return False

        if auth_url:
            # Step 1: Show authorization URL
            st.markdown("**Step 1:** Click the link below to authorize access:")
            st.markdown(f"🔗 **[Authorize Google Drive Access]({auth_url})**")

            # Important note about OAuth consent screen
            st.info("""
            💡 **Important**: If you get an "access_denied" error, you need to add your email as a test user:

            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Select your project → APIs & Services → OAuth consent screen
            3. Add your email to "Test users" section
            """)

            # Step 2: Get authorization code
            st.markdown("**Step 2:** Copy the authorization code and paste it below:")

            auth_code = st.text_input(
                "Authorization Code:",
                placeholder="Paste the authorization code here...",
                help="After clicking the link above, Google will show you an authorization code. Copy and paste it here.",
                key="gdrive_auth_code"
            )

            if auth_code and st.button("✅ Complete Authentication", type="primary"):
                with st.spinner("Completing authentication..."):
                    success, error = self.google_service.exchange_code_for_token(auth_code.strip())

                    if success:
                        st.success("🎉 Authentication successful!")
                        st.balloons()
                        st.session_state.gdrive_auth_flow = False
                        return True
                    st.error(f"❌ Authentication failed: {error}")
                    st.info("Please check the authorization code and try again.")
                    return False

        return False

    def _handle_authentication_flow(self):
        """Handle authentication UI and logic."""
        token_file = 'token.json'
        if not os.path.exists(token_file):
            st.info("🔐 **Easy Authentication Setup**")
            if 'gdrive_auth_flow' not in st.session_state:
                st.session_state.gdrive_auth_flow = False
            if not st.session_state.gdrive_auth_flow:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🚀 Start Authentication", type="primary", help="Click to start the OAuth flow"):
                        st.session_state.gdrive_auth_flow = True
                        st.rerun()
                with col2:
                    if st.button("🔄 Check Status", help="Check if authentication is complete"):
                        st.rerun()
                st.markdown("---")
                st.markdown("**Alternative: Upload Token File**")
                st.caption("If you have a token.json file from a previous authentication:")
                uploaded_token = st.file_uploader(
                    "Upload token.json file",
                    type=['json'],
                    help="Upload a previously saved token.json file"
                )
                if uploaded_token is not None:
                    try:
                        with open('token.json', 'wb') as f:
                            f.write(uploaded_token.getbuffer())
                        st.success("Token file uploaded successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save token file: {e}")
            else:
                if self._perform_oauth_flow():
                    st.session_state.gdrive_auth_flow = False
                    st.rerun()
                if st.button("⬅️ Back"):
                    st.session_state.gdrive_auth_flow = False
                    st.rerun()
            return True
        if st.button("🔄 Refresh Authentication", type="primary"):
            st.rerun()
        return True

    def _get_user_info(self):
        """Get user information from Google Drive API"""
        try:
            # Get user info from the Drive API
            about = self.google_service.service.about().get(fields="user").execute()
            user = about.get('user', {})

            return {
                'name': user.get('displayName', 'Unknown User'),
                'email': user.get('emailAddress', 'Unknown Email'),
                'photo': user.get('photoLink', '')
            }
        except Exception:
            # Fallback: try to get info from OAuth2 userinfo API
            try:
                userinfo_service = build('oauth2', 'v2', credentials=self.google_service.credentials)
                user_info = userinfo_service.userinfo().get().execute()

                return {
                    'name': user_info.get('name', 'Unknown User'),
                    'email': user_info.get('email', 'Unknown Email'),
                    'photo': user_info.get('picture', '')
                }
            except Exception:
                return None
