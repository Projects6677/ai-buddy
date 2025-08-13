# google_drive.py

import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

# Local application imports
from document_processor import get_text_from_file
from grok_ai import analyze_document_context

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
        
        folder_id = _get_or_create_folder(service)
        if not folder_id:
            return "❌ Could not create or find the 'AI Buddy' folder in your Google Drive."

        file_metadata = {
            'name': original_filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        file_link = file.get('webViewLink')
        return f"✅ File uploaded successfully to your 'AI Buddy' folder!\n\n🔗 View File: {file_link}"

    except HttpError as error:
        print(f"An HTTP error occurred during file upload: {error}")
        return "❌ Failed to upload file to Google Drive due to an API error."
    except Exception as e:
        print(f"An unexpected error occurred during file upload: {e}")
        return "❌ An unexpected error occurred while uploading the file."

def search_files_in_drive(credentials, search_query):
    """Searches for files in the user's Google Drive."""
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        query = f"name contains '{search_query}' and trashed=false"
        
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink, iconLink)', pageSize=10).execute()
        files = response.get('files', [])

        if not files:
            return f"😕 No files found matching your search for '*{search_query}*'."

        results_message = f"🔎 Here are the top results for '*{search_query}*':\n\n"
        for file in files:
            file_name = file.get('name')
            file_link = file.get('webViewLink')
            results_message += f"📄 *{file_name}*\n🔗 [View File]({file_link})\n\n"
        
        return results_message.strip()

    except HttpError as error:
        print(f"An HTTP error occurred during file search: {error}")
        return "❌ Failed to search for files due to an API error."
    except Exception as e:
        print(f"An unexpected error occurred during file search: {e}")
        return "❌ An unexpected error occurred while searching for files."

def download_file_from_drive(credentials, file_name):
    """Finds a file by name and downloads its content."""
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        query = f"name = '{file_name}' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, mimeType)', pageSize=1).execute()
        files = response.get('files', [])

        if not files:
            return None, None, f"😕 Couldn't find a file named '*{file_name}*'. Please check the name and try again."

        file_info = files[0]
        file_id = file_info.get('id')
        original_mime_type = file_info.get('mimeType')

        # Handle Google Docs, Sheets, etc. by exporting them to a standard format
        if 'google-apps' in original_mime_type:
            request_mime_type = 'application/pdf' # Export as PDF for text extraction
            request = service.files().export_media(fileId=file_id, mimeType=request_mime_type)
            final_mime_type = request_mime_type
        else:
            # For other file types, download directly
            request = service.files().get_media(fileId=file_id)
            final_mime_type = original_mime_type

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        
        # Save to a temporary local file to be processed
        temp_file_path = os.path.join("uploads", file_name)
        with open(temp_file_path, "wb") as f:
            f.write(fh.read())

        return temp_file_path, final_mime_type, None # No error

    except HttpError as error:
        print(f"An HTTP error occurred during file download: {error}")
        return None, None, "❌ Failed to download the file due to an API error."
    except Exception as e:
        print(f"An unexpected error occurred during file download: {e}")
        return None, None, "❌ An unexpected error occurred while accessing the file."

def analyze_drive_file_content(credentials, file_name):
    """Orchestrates downloading, processing, and analyzing a file from Drive."""
    downloaded_path, mime_type, error = download_file_from_drive(credentials, file_name)
    if error:
        return {"error": error}
        
    try:
        if not downloaded_path:
            return {"error": "Failed to save the downloaded file locally."}

        extracted_text = get_text_from_file(downloaded_path, mime_type)
        if not extracted_text:
            return {"error": "❌ I couldn't find any readable text in that file."}

        analysis = analyze_document_context(extracted_text)
        if not analysis:
            return {"error": "🤔 I analyzed the document, but I'm not sure what to do with it."}
            
        return {
            "document_text": extracted_text,
            "doc_type": analysis.get("doc_type"),
            "data": analysis.get("data", {}),
            "error": None
        }
    finally:
        # Clean up the temporary file
        if downloaded_path and os.path.exists(downloaded_path):
            os.remove(downloaded_path)
