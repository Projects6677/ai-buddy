# meeting_scheduler.py
from googleapiclient.discovery import build
from datetime import datetime, time, timedelta
import pytz
import logging
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

def find_common_free_time(credentials_list, duration_minutes, start_search_dt, end_search_dt):
    """
    Finds a common free time slot for a list of users within a given window.
    """
    if not credentials_list:
        return None
        
    try:
        service = build('calendar', 'v3', credentials=credentials_list[0])
        
        attendees = [{'id': creds.email_address} for creds in credentials_list]
        
        time_min = start_search_dt.isoformat()
        time_max = end_search_dt.isoformat()

        body = {
            "items": attendees,
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": 'Asia/Kolkata'
        }

        freebusy_result = service.freebusy().query(body=body).execute()
        
        # --- Algorithm to find a common slot ---
        tz = pytz.timezone('Asia/Kolkata')
        
        # Combine all busy intervals into one list
        all_busy_intervals = []
        for creds in credentials_list:
            email = creds.email_address
            for interval in freebusy_result['calendars'][email]['busy']:
                all_busy_intervals.append({
                    'start': date_parser.parse(interval['start']).astimezone(tz),
                    'end': date_parser.parse(interval['end']).astimezone(tz)
                })

        # Sort intervals by start time
        all_busy_intervals.sort(key=lambda x: x['start'])
        
        # Merge overlapping intervals
        merged_busy = []
        if all_busy_intervals:
            current_merge = all_busy_intervals[0]
            for next_interval in all_busy_intervals[1:]:
                if next_interval['start'] < current_merge['end']:
                    current_merge['end'] = max(current_merge['end'], next_interval['end'])
                else:
                    merged_busy.append(current_merge)
                    current_merge = next_interval
            merged_busy.append(current_merge)

        # Find a free slot of the required duration
        search_time = start_search_dt
        while search_time + timedelta(minutes=duration_minutes) <= end_search_dt:
            # Check if it's within working hours (e.g., 9 AM to 6 PM)
            if 9 <= search_time.hour < 18:
                is_free = True
                proposed_end = search_time + timedelta(minutes=duration_minutes)
                
                for busy_interval in merged_busy:
                    # Check for overlap
                    if max(search_time, busy_interval['start']) < min(proposed_end, busy_interval['end']):
                        is_free = False
                        search_time = busy_interval['end'] # Jump to the end of the busy slot
                        break
                
                if is_free:
                    return search_time # Found a free slot

            # Move to the next 15-minute interval
            search_time += timedelta(minutes=15)
            
        return None # No suitable slot found

    except Exception as e:
        logger.error(f"Error finding common free time: {e}")
        return None

def create_meeting_event(organizer_creds, attendees_emails, start_time, end_time, topic):
    """
    Creates a Google Calendar event with a Meet link and invites attendees.
    """
    try:
        service = build('calendar', 'v3', credentials=organizer_creds)
        
        event = {
            'summary': topic,
            'description': f"Meeting scheduled by AI Buddy.",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'attendees': [{'email': email} for email in attendees_emails],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"ai-buddy-{int(datetime.now().timestamp())}",
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            },
            'reminders': {
                'useDefault': True,
            },
        }

        created_event = service.events().insert(
            calendarId='primary', 
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()
        
        event_link = created_event.get('htmlLink')
        meet_link = created_event.get('hangoutLink')
        
        confirmation_message = (
            f"✅ Meeting successfully scheduled for *{topic}*!\n\n"
            f"🗓️ *When:* {start_time.strftime('%A, %b %d at %I:%M %p')}\n"
            f"👥 *Attendees:* {', '.join(attendees_emails)}\n\n"
            f"🔗 View on Calendar: {event_link}\n"
            f"📹 Join with Google Meet: {meet_link}"
        )
        return confirmation_message

    except Exception as e:
        logger.error(f"Google Calendar meeting creation error: {e}")
        return "❌ Failed to create the Google Calendar event. Please ensure all attendees have valid email addresses."
