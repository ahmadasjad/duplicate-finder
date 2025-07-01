import os
import logging
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class GoogleAuthenticator:
    """Handles Google Drive OAuth2 authentication and user info retrieval."""
    def __init__(self):
        self.authenticated = False
        self.credentials = None
        self.service = None
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup Google Drive API credentials"""
        # Check if credentials are already stored in session state
        if 'gdrive_credentials' in st.session_state:
            self.credentials = st.session_state.gdrive_credentials
            self.authenticated = True
            self._build_service()

    def _build_service(self):
        """Build Google Drive API service"""
        try:
            from googleapiclient.discovery import build
            if self.credentials:
                self.service = build('drive', 'v3', credentials=self.credentials)
                return True
        except ImportError:
            return False
        return False

    def _perform_oauth_flow(self):
        """Perform OAuth flow directly in the application"""
        st.markdown("### 🔐 Google Drive Authentication")

        # Generate auth URL
        auth_url, error = self._generate_auth_url()
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
                    success, error = self._exchange_code_for_token(auth_code.strip())

                    if success:
                        st.success("🎉 Authentication successful!")
                        st.balloons()
                        st.session_state.gdrive_auth_flow = False
                        return True
                    st.error(f"❌ Authentication failed: {error}")
                    st.info("Please check the authorization code and try again.")
                    return False

        return False

    def _generate_auth_url(self):
        """Generate authentication URL for user to visit"""
        try:

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials_file = 'credentials.json'

            if not os.path.exists(credentials_file):
                return None, "credentials.json file not found"

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # For manual copy-paste flow

            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url, None

        except Exception as e:
            return None, str(e)

    def _exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        try:

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials_file = 'credentials.json'

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

            # Exchange code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials

            # Save token
            with open('token.json', 'w', encoding='utf-8') as token:
                token.write(creds.to_json())

            # Update instance
            self.credentials = creds
            st.session_state.gdrive_credentials = creds

            if self._build_service():
                self.authenticated = True
                return True, None
            return False, "Failed to build Google Drive service"

        except Exception as e:
            error_message = str(e)

            # Handle common OAuth errors with helpful messages
            if "access_denied" in error_message:
                return False, """
🚫 **Access Denied - OAuth Consent Screen Issue**

This error usually means your app is in testing mode and you need to add your email as a test user:

**Fix Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project 'duplicate-file-finder-464317'
3. Go to APIs & Services → OAuth consent screen
4. Scroll to "Test users" section
5. Click "+ ADD USERS"
6. Add your email address
7. Click Save and try again

**Alternative:** You can also publish your OAuth consent screen to make it available to all users.
"""
            if "invalid_grant" in error_message:
                return False, """
⏰ **Invalid Grant - Code Expired**

The authorization code has expired or was already used.

**Fix:** Click the authorization link again to get a new code.
"""
            if "invalid_request" in error_message:
                return False, """
📝 **Invalid Request - Code Format Issue**

The authorization code format is incorrect.

**Fix:** Make sure you copied the complete authorization code from Google.
"""

            return False, f"Authentication error: {error_message}"

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
            about = self.service.about().get(fields="user").execute()
            user = about.get('user', {})

            return {
                'name': user.get('displayName', 'Unknown User'),
                'email': user.get('emailAddress', 'Unknown Email'),
                'photo': user.get('photoLink', '')
            }
        except Exception:
            # Fallback: try to get info from OAuth2 userinfo API
            try:
                from googleapiclient.discovery import build
                userinfo_service = build('oauth2', 'v2', credentials=self.credentials)
                user_info = userinfo_service.userinfo().get().execute()

                return {
                    'name': user_info.get('name', 'Unknown User'),
                    'email': user_info.get('email', 'Unknown Email'),
                    'photo': user_info.get('picture', '')
                }
            except Exception:
                return None
