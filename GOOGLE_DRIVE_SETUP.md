# Google Drive Integration Setup Guide

This guide will help you set up Google Drive integration for the Duplicate File Finder with **improved browser-based authentication**.

## ✨ **New Features**
- 🚀 **No more terminal commands required!**
- 🎯 **Direct browser authentication**
- 📁 **Token file upload option**
- 🎉 **User-friendly step-by-step process**Drive Setup Guide

Follow these steps to connect your Google Drive account to the Duplicate File Finder.

## What You'll Get
- 🚀 **Easy browser-based authentication**
- 🎯 **No terminal commands needed**
- 📁 **Option to upload saved credentials**
- � **Scan your Google Drive for duplicate files**

## Prerequisites

The Google Drive integration requires additional Python packages that are automatically installed when using Docker.

For local development, install them manually:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Google Cloud Console Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name your project (e.g., "Duplicate File Finder")
4. Click "Create"

### 2. Enable Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and click "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" for user type
   - Fill in required fields (App name, User support email, Developer contact)
   - **⚠️ IMPORTANT: Add your email to "Test users" section** (this prevents Error 403: access_denied)
4. For Application type, select "Desktop application"
5. Name it (e.g., "Duplicate Finder Desktop")
6. Click "Create"

### 4. Download Credentials

1. Click the download button (⬇️) next to your newly created OAuth client
2. Rename the downloaded file to `credentials.json`
3. Place it in the project root directory (same level as `docker-compose.yml`)

## 🚀 **New Authentication Process**

### **Method 1: Direct Browser Authentication** (Recommended)

1. **Start the Application**
   ```bash
   docker compose up -d
   ```
   Open: http://localhost:8501

2. **Select "Google Drive"** from the storage provider dropdown

3. **Click "🚀 Start Authentication"** button

4. **Click the authorization link** that appears in the app

5. **Sign in to Google** and grant permissions to your app

6. **Copy the authorization code** shown by Google

7. **Paste the code** in the application input field

8. **Click "✅ Complete Authentication"**

9. **Success! 🎉** You can now scan your Google Drive

### **Method 2: Upload Token File** (For Returning Users)

1. If you have a `token.json` file from previous authentication
2. **Click "📁 Upload token.json file"** button
3. **Select your token file**
4. **Automatically authenticated!**

### For Docker Users (Legacy Method)

If you prefer the command-line approach:

1. Ensure `credentials.json` is in the project root
2. Start the application: `docker compose up -d`
3. Select "Google Drive" from the storage provider dropdown
4. Follow the manual authentication instructions in the app
5. Run the provided Python command in your terminal
6. Complete the OAuth flow in your browser
7. Return to the app and refresh the page

## 🎯 **User Experience Features**

- **✅ Visual feedback**: Progress indicators and success animations
- **✅ Error handling**: Clear error messages with solutions
- **✅ Intuitive UI**: Step-by-step guidance
- **✅ Multiple options**: Choose the authentication method that works for you
- **✅ Session persistence**: Stay authenticated across app restarts
- **✅ No terminal required**: Everything happens in the browser

## 🛡️ **Security & Privacy**

- **Read-only access**: The application only reads file metadata for duplicate detection
- **Local storage**: Credentials are stored securely on your machine only
- **No data sharing**: Your Google Drive files never leave your local environment
- **Standard OAuth**: Uses Google's official authentication protocols
- **Safe operations**: File "deletion" moves files to trash, not permanent deletion
- **Sensitive files**: Add `credentials.json` and `token.json` to your `.gitignore` file
- **Production deployments**: Use proper credential management (environment variables, secret stores)

## Troubleshooting

### **Error 403: access_denied** (Most Common Issue)
This happens when your email isn't added as a test user:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project → **APIs & Services** → **OAuth consent screen**
3. Scroll to **"Test users"** section
4. Click **"+ ADD USERS"**
5. Add your email address
6. Save and try authentication again

### "Missing Dependencies" Error
Install the required packages:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### "Setup Required" Error
You need to create and download the `credentials.json` file from Google Cloud Console.

### Authentication Issues
1. **Make sure you've added your email as a test user** in the OAuth consent screen (see above)
2. Try deleting `token.json` and re-authenticating
3. Check that the Google Drive API is enabled in your project
4. Verify `credentials.json` is in the project root directory

### Permission Errors
The app only has read-only access to prevent accidental data loss. File "deletion" moves files to trash.

### Token File Issues
- If uploading `token.json` fails, try the browser authentication method
- Make sure the token file is from the same `credentials.json`
- Delete old `token.json` files if you recreated credentials

## File Limitations

- Google Workspace files (Docs, Sheets, Slides) are excluded from scanning as they don't have traditional file hashes
- Very large files may take longer to process
- The app processes files in batches to avoid API rate limits

## Privacy

- Your Google Drive data never leaves your local environment
- The app only accesses file metadata and checksums for duplicate detection
- No file content is read or stored

---

## 🎉 **Ready to Use!**

The Google Drive integration is now **production-ready** with:

- ✅ **User-friendly browser-based authentication**
- ✅ **Complete file scanning capabilities**
- ✅ **Duplicate detection and management**
- ✅ **Safe file operations** (trash, not delete)
- ✅ **Comprehensive error handling**
- ✅ **Professional user interface**

**Get started now**:
1. Make sure you have `credentials.json` in your project root
2. Run `docker compose up -d`
3. Open http://localhost:8501
4. Select "Google Drive" and experience the streamlined authentication!

*No more terminal commands, no more complex setup - just click, authenticate, and scan!* 🚀
