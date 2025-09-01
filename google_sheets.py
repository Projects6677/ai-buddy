# google_sheets.py

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

def _get_or_create_spreadsheet(drive_service, sheets_service):
    """
    Checks if the 'AI Buddy Expenses' spreadsheet exists, creates it if not,
    and returns its ID and URL.
    """
    try:
        # 1. Use Drive service to search for the spreadsheet
        query = "mimeType='application/vnd.google-apps.spreadsheet' and name='AI Buddy Expenses' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink)').execute()
        files = response.get('files', [])

        if files:
            # File exists, return its info
            sheet_id = files[0].get('id')
            sheet_url = files[0].get('webViewLink')
            return sheet_id, sheet_url
        else:
            # 2. File does not exist, use Sheets service to create it
            spreadsheet = {
                'properties': {
                    'title': 'AI Buddy Expenses'
                }
            }
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')

            # 3. Add headers to the new sheet using sheets_service
            header_values = [['Date', 'Time', 'Item', 'Place', 'Cost (₹)']]
            body = {'values': header_values}
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return spreadsheet_id, spreadsheet.get('spreadsheetUrl')

    except HttpError as error:
        logger.error(f"An error occurred while checking/creating the spreadsheet: {error}")
        return None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_or_create_spreadsheet: {e}")
        return None, None

def append_expense_to_sheet(credentials, user_id, expense_data):
    """
    Appends a new row of expense data to the user's 'AI Buddy Expenses' sheet.
    
    Args:
        credentials: The user's Google API credentials.
        user_id: The unique identifier for the user.
        expense_data (dict): A dictionary containing the expense details.
                             Expected keys: 'timestamp', 'item', 'place', 'cost'.
    
    Returns:
        A confirmation message string.
    """
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)

        spreadsheet_id, spreadsheet_url = _get_or_create_spreadsheet(drive_service, sheets_service)

        if not spreadsheet_id:
            return "❌ Could not find or create your expense sheet in Google Drive."

        # Format the data for the new row
        new_row = [
            expense_data['timestamp'].strftime('%Y-%m-%d'),
            expense_data['timestamp'].strftime('%I:%M %p'),
            expense_data['item'].title(),
            expense_data['place'].title() if expense_data.get('place') else 'N/A',
            f"{expense_data['cost']:.2f}"
        ]
        
        body = {'values': [new_row]}
        
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        confirmation = (
            f"✅ Logged: *₹{expense_data['cost']:.2f}* for *{expense_data['item'].title()}* to your Google Sheet.\n\n"
            f"🔗 View Sheet: {spreadsheet_url}"
        )
        return confirmation

    except HttpError as error:
        logger.error(f"An HTTP error occurred while appending to the sheet: {error}")
        return "❌ Failed to log expense to Google Sheets due to an API error."
    except Exception as e:
        logger.error(f"An unexpected error occurred during sheet append: {e}")
        return "❌ An unexpected error occurred while logging your expense."

def get_sheet_link(credentials, user_id):
    """
    Gets the link to the 'AI Buddy Expenses' spreadsheet without adding data.
    """
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        query = "mimeType='application/vnd.google-apps.spreadsheet' and name='AI Buddy Expenses' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink)').execute()
        files = response.get('files', [])

        if files:
            spreadsheet_url = files[0].get('webViewLink')
            return f"📊 Here is the link to your expense sheet:\n\n🔗 {spreadsheet_url}"
        else:
            return "😕 I couldn't find your expense sheet. Try logging an expense first to create it."
    except Exception as e:
        logger.error(f"Error getting sheet link: {e}")
        return "❌ An error occurred while trying to find your expense sheet."
