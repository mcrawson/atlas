"""Google Calendar integration for ATLAS - events and reminders."""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
import logging

from .google_auth import GoogleAuth

logger = logging.getLogger("atlas.integrations.calendar")


class CalendarClient:
    """Google Calendar API client for ATLAS."""

    def __init__(self, auth: GoogleAuth = None):
        """Initialize calendar client.

        Args:
            auth: GoogleAuth instance for authentication
        """
        self.auth = auth or GoogleAuth()
        self._service = None

    def is_available(self) -> bool:
        """Check if calendar is available.

        Returns:
            True if authenticated
        """
        return self.auth.is_authenticated()

    def _get_service(self):
        """Get or create Calendar API service."""
        if self._service is None:
            self._service = self.auth.build_service("calendar", "v3")
        return self._service

    async def get_today_events(self) -> List[Dict[str, Any]]:
        """Get today's calendar events.

        Returns:
            List of event dictionaries
        """
        today = date.today()
        start = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
        end = datetime.combine(today, datetime.max.time()).isoformat() + "Z"

        return await self._get_events(start, end)

    async def get_upcoming(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get events in the next N hours.

        Args:
            hours: Number of hours to look ahead

        Returns:
            List of event dictionaries
        """
        now = datetime.utcnow()
        end = now + timedelta(hours=hours)

        return await self._get_events(
            now.isoformat() + "Z",
            end.isoformat() + "Z",
        )

    async def _get_events(
        self,
        time_min: str,
        time_max: str,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get events in a time range.

        Args:
            time_min: Start time (ISO format with Z)
            time_max: End time (ISO format with Z)
            max_results: Maximum events to return

        Returns:
            List of event dictionaries
        """
        service = self._get_service()
        if not service:
            return []

        try:
            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = result.get("items", [])
            return [self._parse_event(e) for e in events]

        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def _parse_event(self, event: dict) -> Dict[str, Any]:
        """Parse a Google Calendar event.

        Args:
            event: Raw event from API

        Returns:
            Simplified event dictionary
        """
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle all-day vs timed events
        if "dateTime" in start:
            start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
            all_day = False
        else:
            start_dt = datetime.strptime(start.get("date", ""), "%Y-%m-%d")
            end_dt = datetime.strptime(end.get("date", ""), "%Y-%m-%d")
            all_day = True

        return {
            "id": event.get("id"),
            "title": event.get("summary", "Untitled"),
            "start": start_dt,
            "end": end_dt,
            "all_day": all_day,
            "location": event.get("location"),
            "description": event.get("description"),
            "attendees": [
                a.get("email") for a in event.get("attendees", [])
            ],
            "meeting_link": event.get("hangoutLink"),
            "status": event.get("status"),
        }

    async def get_next_meeting(self) -> Optional[Dict[str, Any]]:
        """Get the next upcoming meeting.

        Returns:
            Next event or None
        """
        events = await self.get_upcoming(hours=8)

        # Filter to meetings with attendees or locations
        meetings = [
            e for e in events
            if e.get("attendees") or e.get("location") or e.get("meeting_link")
        ]

        return meetings[0] if meetings else None

    async def get_events_with_reminder(
        self,
        reminder_minutes: List[int] = [15, 5],
    ) -> List[Dict[str, Any]]:
        """Get events that need reminders.

        Args:
            reminder_minutes: List of minutes before event to remind

        Returns:
            List of events needing reminders
        """
        now = datetime.now()
        max_reminder = max(reminder_minutes)
        events = await self.get_upcoming(hours=1)

        needs_reminder = []
        for event in events:
            if event["all_day"]:
                continue

            start = event["start"]
            if not start.tzinfo:
                # Assume local time
                start = start.replace(tzinfo=now.astimezone().tzinfo)

            minutes_until = (start - now.astimezone()).total_seconds() / 60

            for reminder_min in reminder_minutes:
                if reminder_min - 1 <= minutes_until <= reminder_min + 1:
                    event["reminder_minutes"] = reminder_min
                    needs_reminder.append(event)
                    break

        return needs_reminder

    def format_event_for_briefing(self, event: Dict[str, Any]) -> str:
        """Format an event for display in briefing.

        Args:
            event: Event dictionary

        Returns:
            Formatted string
        """
        if event["all_day"]:
            time_str = "All day"
        else:
            start = event["start"]
            end = event["end"]
            duration = (end - start).total_seconds() / 60
            time_str = f"{start.strftime('%I:%M %p')} ({int(duration)} min)"

        result = f"{time_str} - {event['title']}"

        if event.get("location"):
            result += f" @ {event['location'][:30]}"

        return result

    async def get_schedule_summary(self) -> str:
        """Get a summary of today's schedule for briefing.

        Returns:
            Formatted schedule summary
        """
        events = await self.get_today_events()

        if not events:
            return "No events scheduled for today, sir."

        lines = []
        for event in events[:5]:  # Limit to 5
            lines.append(f"  {self.format_event_for_briefing(event)}")

        if len(events) > 5:
            lines.append(f"  ...and {len(events) - 5} more")

        return "\n".join(lines)


class Event:
    """Calendar event dataclass."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize from dictionary."""
        self.id = data.get("id")
        self.title = data.get("title", "Untitled")
        self.start = data.get("start")
        self.end = data.get("end")
        self.all_day = data.get("all_day", False)
        self.location = data.get("location")
        self.description = data.get("description")
        self.attendees = data.get("attendees", [])
        self.meeting_link = data.get("meeting_link")

    def is_soon(self, minutes: int = 15) -> bool:
        """Check if event starts soon.

        Args:
            minutes: How many minutes is "soon"

        Returns:
            True if event starts within minutes
        """
        if self.all_day:
            return False

        now = datetime.now()
        if self.start.tzinfo:
            now = now.astimezone()

        delta = (self.start - now).total_seconds() / 60
        return 0 <= delta <= minutes

    def __str__(self) -> str:
        if self.all_day:
            return f"{self.title} (all day)"
        return f"{self.title} at {self.start.strftime('%I:%M %p')}"
