"""Gmail integration for ATLAS - email summary and important messages."""

import base64
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from .google_auth import GoogleAuth

logger = logging.getLogger("atlas.integrations.email")


class EmailClient:
    """Gmail API client for ATLAS."""

    def __init__(self, auth: GoogleAuth = None, important_senders: List[str] = None):
        """Initialize email client.

        Args:
            auth: GoogleAuth instance for authentication
            important_senders: List of email addresses to always flag as important
        """
        self.auth = auth or GoogleAuth()
        self.important_senders = important_senders or []
        self._service = None

    def is_available(self) -> bool:
        """Check if email is available.

        Returns:
            True if authenticated
        """
        return self.auth.is_authenticated()

    def _get_service(self):
        """Get or create Gmail API service."""
        if self._service is None:
            self._service = self.auth.build_service("gmail", "v1")
        return self._service

    async def get_unread_count(self) -> int:
        """Get count of unread emails.

        Returns:
            Number of unread emails
        """
        service = self._get_service()
        if not service:
            return 0

        try:
            result = service.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=1,
            ).execute()

            return result.get("resultSizeEstimate", 0)

        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0

    async def get_unread_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get unread emails.

        Args:
            limit: Maximum emails to return

        Returns:
            List of email dictionaries
        """
        service = self._get_service()
        if not service:
            return []

        try:
            result = service.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=limit,
            ).execute()

            messages = result.get("messages", [])
            emails = []

            for msg in messages:
                email_data = await self._get_email_details(msg["id"])
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            logger.error(f"Failed to get unread emails: {e}")
            return []

    async def get_important_unread(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get important unread emails.

        Important = starred, from known senders, or marked important

        Args:
            limit: Maximum emails to return

        Returns:
            List of email dictionaries
        """
        service = self._get_service()
        if not service:
            return []

        try:
            # Query for important/starred unread
            result = service.users().messages().list(
                userId="me",
                q="is:unread (is:important OR is:starred)",
                maxResults=limit,
            ).execute()

            messages = result.get("messages", [])
            emails = []

            for msg in messages[:limit]:
                email_data = await self._get_email_details(msg["id"])
                if email_data:
                    emails.append(email_data)

            # Also check for emails from important senders
            if self.important_senders and len(emails) < limit:
                for sender in self.important_senders[:3]:  # Limit sender queries
                    try:
                        result = service.users().messages().list(
                            userId="me",
                            q=f"is:unread from:{sender}",
                            maxResults=limit - len(emails),
                        ).execute()

                        for msg in result.get("messages", []):
                            if msg["id"] not in [e["id"] for e in emails]:
                                email_data = await self._get_email_details(msg["id"])
                                if email_data:
                                    emails.append(email_data)
                                    if len(emails) >= limit:
                                        break
                    except Exception:
                        continue

            return emails[:limit]

        except Exception as e:
            logger.error(f"Failed to get important emails: {e}")
            return []

    async def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific email.

        Args:
            message_id: Gmail message ID

        Returns:
            Email dictionary or None
        """
        service = self._get_service()
        if not service:
            return None

        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {
                h["name"]: h["value"]
                for h in message.get("payload", {}).get("headers", [])
            }

            # Parse date
            date_str = headers.get("Date", "")
            try:
                # Various date formats
                for fmt in [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%d %b %Y %H:%M:%S %z",
                ]:
                    try:
                        received = datetime.strptime(date_str[:31], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    received = datetime.now()
            except Exception:
                received = datetime.now()

            return {
                "id": message_id,
                "from": self._parse_sender(headers.get("From", "")),
                "subject": headers.get("Subject", "(no subject)"),
                "received": received,
                "snippet": message.get("snippet", ""),
                "labels": message.get("labelIds", []),
                "is_starred": "STARRED" in message.get("labelIds", []),
                "is_important": "IMPORTANT" in message.get("labelIds", []),
            }

        except Exception as e:
            logger.error(f"Failed to get email {message_id}: {e}")
            return None

    def _parse_sender(self, from_header: str) -> Dict[str, str]:
        """Parse From header into name and email.

        Args:
            from_header: Raw From header

        Returns:
            Dict with 'name' and 'email' keys
        """
        import re

        # Match "Name <email@domain.com>" pattern
        match = re.match(r'"?([^"<]*)"?\s*<([^>]+)>', from_header)
        if match:
            return {"name": match.group(1).strip(), "email": match.group(2)}

        # Just email address
        if "@" in from_header:
            return {"name": from_header.split("@")[0], "email": from_header}

        return {"name": from_header, "email": ""}

    async def get_summary(self) -> Dict[str, Any]:
        """Get email summary for briefing.

        Returns:
            Summary dictionary
        """
        unread_count = await self.get_unread_count()
        important = await self.get_important_unread(limit=5)

        return {
            "unread_count": unread_count,
            "important_count": len(important),
            "important_emails": important,
        }

    def format_email_for_briefing(self, email: Dict[str, Any]) -> str:
        """Format an email for display in briefing.

        Args:
            email: Email dictionary

        Returns:
            Formatted string
        """
        sender = email["from"]
        name = sender.get("name", sender.get("email", "Unknown"))[:20]
        subject = email.get("subject", "(no subject)")[:40]

        # Time ago
        received = email.get("received")
        if received:
            delta = datetime.now(received.tzinfo if received.tzinfo else None) - received
            if delta.days > 0:
                time_ago = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_ago = f"{delta.seconds // 3600}h ago"
            else:
                time_ago = f"{delta.seconds // 60}m ago"
        else:
            time_ago = ""

        return f"{name}: \"{subject}\" ({time_ago})"

    async def get_email_briefing(self) -> str:
        """Get formatted email briefing.

        Returns:
            Formatted briefing string
        """
        summary = await self.get_summary()

        unread = summary["unread_count"]
        important = summary["important_count"]

        if unread == 0:
            return "No unread emails, sir."

        lines = [f"{unread} unread ({important} important)"]

        for email in summary["important_emails"][:3]:
            lines.append(f"  - {self.format_email_for_briefing(email)}")

        return "\n".join(lines)

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """Send an email using Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        service = self._get_service()
        if not service:
            logger.error("Gmail service not available")
            return False

        try:
            # Create message
            if html:
                message = MIMEMultipart("alternative")
                message.attach(MIMEText(body, "html"))
            else:
                message = MIMEText(body)

            message["to"] = to
            message["subject"] = subject

            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send
            service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logger.info(f"Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
