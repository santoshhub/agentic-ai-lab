# custom_tool.py
import os
import pickle
from typing import Type, List, Optional
from datetime import datetime, timedelta
from tzlocal import get_localzone

from pydantic import BaseModel, Field, EmailStr

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from crewai.tools import BaseTool

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.pickle")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")


def _connect_calendar_api():
    """Connect to Google Calendar API and return a service client."""
    creds: Optional[Credentials] = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                raise RuntimeError(
                    f"credentials.json not found at {CREDS_PATH}. "
                    "Place your OAuth credentials file there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as token_file:
            pickle.dump(creds, token_file)

    return build("calendar", "v3", credentials=creds)


# ----------------- Meeting Scheduler -----------------
class MeetingDetails(BaseModel):
    summary: str = Field(..., description="Meeting Title")
    location: Optional[str] = Field("", description="Location")
    description: Optional[str] = Field("", description="Description")
    start: str = Field(..., description="ISO start e.g. 2025-11-17T21:00:00")
    end: str = Field(..., description="ISO end e.g. 2025-11-17T22:00:00")
    attendees: List[EmailStr] = Field(default_factory=list)

class MeetingSchedulerTool(BaseTool):
    name: str = "create meetings"
    description: str = "Create Google Calendar events"
    args_schema: Type[BaseModel] = MeetingDetails
    return_direct: bool = True

    def _run(self, summary: str, location: Optional[str], description: Optional[str],
             start: str, end: str, attendees: List[str]) -> dict:  # <- return dict
        service = _connect_calendar_api()
        local_tz = str(get_localzone())

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        body = {
            "summary": summary,
            "location": location or "",
            "description": description or "",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": local_tz},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": local_tz},
            "attendees": [{"email": e} for e in attendees],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24*60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        event = service.events().insert(calendarId="primary", body=body).execute()
        return {
            "status": "success",
            "id": event.get("id"),
            "summary": event.get("summary"),
            "start": event["start"].get("dateTime"),
            "end": event["end"].get("dateTime"),
            "htmlLink": event.get("htmlLink"),
        }

        # try:
        #     event = service.events().insert(
        #         calendarId="primary", body=body, sendUpdates="all"
        #     ).execute()
        #     # Return a short JSON-ish summary string (crew expects a short message)
        #     return (
        #         "Event created successfully.\n"
        #         f"id: {event.get('id')}\n"
        #         f"summary: {event.get('summary')}\n"
        #         f"start: {event['start'].get('dateTime')}\n"
        #         f"end: {event['end'].get('dateTime')}\n"
        #         f"htmlLink: {event.get('htmlLink')}"
        #     )
        # except HttpError as e:
        #     return f"Error creating event: {e}"

# ----------------- Availability Checker -----------------
class TimeAvailability(BaseModel):
    start: str = Field(..., description="Month DD, YYYY, HH:MMAM/PM")
    end: str = Field(..., description="Month DD, YYYY, HH:MMAM/PM")

class TimeAvailabilityTool(BaseTool):
    name: str = "check availability"
    description: str = "Check user's available time on Google Calendar"
    args_schema: Type[BaseModel] = TimeAvailability

    def _run(self, start: str, end: str):
        service = _connect_calendar_api()
        local_zone = get_localzone()
        st = datetime.strptime(start, "%B %d, %Y, %I:%M%p").replace(tzinfo=local_zone)
        et = datetime.strptime(end, "%B %d, %Y, %I:%M%p").replace(tzinfo=local_zone)

        available_days = []
        current = st.date()
        end_date = et.date()

        while current <= end_date:
            day_start = datetime.combine(current, datetime.min.time()).replace(tzinfo=local_zone)
            day_end = datetime.combine(current, datetime.max.time()).replace(tzinfo=local_zone)

            if day_start < st:
                day_start = st
            if day_end > et:
                day_end = et

            body = {
                "timeMin": day_start.isoformat(),
                "timeMax": day_end.isoformat(),
                "timeZone": str(local_zone),
                "items": [{"id": "primary"}],
            }
            result = service.freebusy().query(body=body).execute()
            busy_times = result["calendars"]["primary"].get("busy", [])
            free_slots = []
            cursor = day_start
            for period in busy_times:
                bstart = datetime.fromisoformat(period["start"]).astimezone(local_zone)
                bend = datetime.fromisoformat(period["end"]).astimezone(local_zone)
                if bstart > cursor:
                    free_slots.append((cursor.time().isoformat(), bstart.time().isoformat()))
                cursor = max(cursor, bend)
            if cursor < day_end:
                free_slots.append((cursor.time().isoformat(), day_end.time().isoformat()))
            if free_slots:
                available_days.append({"date": current.isoformat(), "available": free_slots})
            current += timedelta(days=1)

        return available_days

# ----------------- Event Checker -----------------
class EventChecker(BaseModel):
    start: str = Field(..., description="Month DD, YYYY, HH:MMAM/PM")
    end: Optional[str] = Field(None, description="Month DD, YYYY, HH:MMAM/PM")

class EventCheckerTool(BaseTool):
    name: str = "event checker"
    description: str = "List events in a date range"
    args_schema: Type[BaseModel] = EventChecker

    def _run(self, start: str, end: Optional[str] = None):
        try:
            service = _connect_calendar_api()
            start_dt = datetime.strptime(start, "%B %d, %Y, %I:%M%p").date()
            end_dt = datetime.strptime(end, "%B %d, %Y, %I:%M%p").date() if end else None

            out = []
            page_token = None
            while True:
                resp = service.events().list(calendarId="primary", pageToken=page_token).execute()
                for ev in resp.get("items", []):
                    ev_start = ev["start"].get("dateTime", ev["start"].get("date"))
                    try:
                        ev_date = datetime.fromisoformat(ev_start).date()
                    except Exception:
                        continue
                    if end_dt:
                        if not (start_dt <= ev_date <= end_dt):
                            continue
                    else:
                        if ev_date < start_dt:
                            continue
                    out.append({"summary": ev.get("summary", "No Title"), "start": ev_start})
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return out
        except Exception as e:
            return [{"error": str(e)}]
