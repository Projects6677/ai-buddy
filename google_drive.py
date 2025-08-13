# google_drive.py

import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def _get_or_create_folder(service):
    """Checks for the 'AI Buddy' folder and creates it if it doesn't exist."""
    try:
        # Search for the folder
        query = "mimeType='application/vnd.google-apps.folder' and name='AI Buddy' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Folder exists, return its ID
            return files[0].get('id')
        else:
            # Folder does not exist, create it
            file_metadata = {
                'name': 'AI Buddy',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    except HttpError as error:
        print(f"An error occurred while checking/creating the folder: {error}")
        return None

def upload_file_to_drive(credentials, file_path, original_filename, mime_type):
    """Uploads a file to the user's Google Drive in a specific folder."""
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        # Get the ID of the 'AI Buddy' folder
        folder_id = _get_or_create_folder(service)
        if not folder_id:
            return "❌ Could not create or find the 'AI Buddy' folder in your Google Drive."

        # Define the file's metadata
        file_metadata = {
            'name': original_filename,
            'parents': [folder_id]
        }
        
        # Create a media upload object
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        # Upload the file
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        file_link = file.get('webViewLink')
        return f"✅ File uploaded successfully to your 'AI Buddy' folder!\n\n🔗 View File: {file_link}"

    except HttpError as error:
        print(f"An HTTP error occurred during file upload: {error}")
        return "❌ Failed to upload file to Google Drive due to an API error."
    except Exception as e:
        print(f"An unexpected error occurred during file upload: {e}")
        return "❌ An unexpected error occurred while uploading the file."
