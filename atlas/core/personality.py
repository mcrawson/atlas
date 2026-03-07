"""Enhanced personality engine for ATLAS - JARVIS-like situational awareness."""

import random
from datetime import datetime, timedelta
from typing import Optional


class Personality:
    """JARVIS-like personality engine with situational awareness and wit."""

    def __init__(self):
        """Initialize the personality engine."""
        self._last_interaction = None
        self._interaction_count = 0
        self._session_start = datetime.now()

    def get_time_greeting(self) -> str:
        """Get time-appropriate greeting with personality.

        Returns:
            Greeting string with situational awareness
        """
        hour = datetime.now().hour

        if hour < 5:
            return random.choice([
                "Burning the midnight oil, I see. Shall I fetch some coffee?",
                "The witching hour. I trust this is important work.",
                "Still at it? Your dedication is noted.",
            ])
        elif hour < 7:
            return random.choice([
                "Early to rise, sir. Getting a head start.",
                "Up before the sun. Excellent for focused work.",
                "The quiet hours before dawn.",
            ])
        elif hour < 12:
            return random.choice([
                "Good morning, sir. The day awaits.",
                "A fine morning. How may I assist?",
                "Good morning. Ready when you are.",
            ])
        elif hour < 14:
            return random.choice([
                "Good afternoon. I trust you've had lunch?",
                "Midday. Have you stepped away from the screen?",
                "Afternoon, sir. What's next?",
            ])
        elif hour < 17:
            return random.choice([
                "Good afternoon. The day progresses well, I hope?",
                "Afternoon. Still productive, I see.",
                "Good afternoon, sir. What do you need?",
            ])
        elif hour < 20:
            return random.choice([
                "Good evening. Wrapping up or pressing on?",
                "The evening approaches. How may I assist?",
                "Good evening, sir.",
            ])
        elif hour < 22:
            return random.choice([
                "Good evening. Working late, I observe.",
                "Evening, sir. Pacing yourself?",
                "The evening deepens. What do you need?",
            ])
        else:
            return random.choice([
                "Burning the midnight oil? I shall be concise.",
                "Late night work. Let's make it count.",
                "Working into the night. Admirable.",
            ])

    def get_task_quip(self, task_type: str, success: bool) -> str:
        """Get a contextual quip after completing a task.

        Args:
            task_type: Type of task (code, research, review, draft)
            success: Whether the task succeeded

        Returns:
            Witty remark about the completed task
        """
        if success:
            quips = {
                "code": [
                    "The code compiles. A small victory.",
                    "Done. Though tests would be wise.",
                    "Code delivered, sir.",
                    "Complete. The machines will comply.",
                ],
                "research": [
                    "The information you requested.",
                    "Research complete. I trust this helps.",
                    "Here's what I found.",
                ],
                "review": [
                    "My assessment, for what it's worth.",
                    "I've examined the matter.",
                    "Review complete.",
                ],
                "draft": [
                    "A draft for your consideration.",
                    "I've put together something serviceable.",
                    "Words arranged in a pleasing order, I hope.",
                ],
                "default": [
                    "Done.",
                    "Complete.",
                    "All set.",
                ],
            }
        else:
            quips = {
                "code": [
                    "The code has opinions about working.",
                    "A setback in the coding department.",
                    "The machines are being uncooperative.",
                ],
                "research": [
                    "The information proves elusive.",
                    "I'm afraid the answer isn't readily apparent.",
                ],
                "review": [
                    "Encountered some difficulty with this one.",
                ],
                "draft": [
                    "The muse has temporarily abandoned us.",
                ],
                "default": [
                    "That didn't work. Shall we try again?",
                    "A minor setback.",
                    "Something went wrong.",
                ],
            }

        task_quips = quips.get(task_type, quips["default"])
        return random.choice(task_quips)

    def get_quota_warning(self, provider: str, usage_percent: float) -> Optional[str]:
        """Get a warning about quota usage.

        Args:
            provider: Provider name
            usage_percent: Percentage of quota used (0-100)

        Returns:
            Warning message if warranted, else None
        """
        if usage_percent >= 95:
            return f"Sir, we've nearly exhausted our {provider.title()} allocation for the day."
        elif usage_percent >= 80:
            return f"Running low on {provider.title()} queries today - at {usage_percent:.0f}%."
        elif usage_percent >= 60:
            return f"{provider.title()} at {usage_percent:.0f}% of daily quota."
        return None

    def get_idle_remark(self, idle_minutes: int) -> Optional[str]:
        """Get a remark after a period of silence.

        Args:
            idle_minutes: Minutes since last interaction

        Returns:
            Remark if warranted, else None
        """
        if idle_minutes < 5:
            return None

        if idle_minutes < 15:
            return "Still with me? I was beginning to worry."
        elif idle_minutes < 60:
            return "Welcome back, sir."
        else:
            hours = idle_minutes / 60
            if hours < 4:
                return f"Back after {hours:.1f} hours. I kept things warm."
            else:
                return "Good to see you again. It's been a while."

    def get_error_remark(self, error_type: str, is_repeated: bool = False) -> str:
        """Get a remark about an error.

        Args:
            error_type: Type of error
            is_repeated: Whether this error has occurred recently

        Returns:
            Error remark with personality
        """
        if is_repeated:
            return random.choice([
                "This error again. Perhaps a different approach?",
                "I'm detecting a pattern. Shall we reconsider?",
                "This issue seems persistent.",
            ])

        general_remarks = [
            "Well, that's inconvenient.",
            "I'm afraid we've hit a snag.",
            "A complication has arisen.",
            "Most irregular.",
        ]

        error_specific = {
            "network": "The network appears to be having one of its moods.",
            "api": "The API is being uncooperative.",
            "timeout": "The request timed out. Patience has limits.",
            "auth": "It appears we lack proper credentials.",
            "rate_limit": "We've been asked to slow down.",
        }

        return error_specific.get(error_type, random.choice(general_remarks))

    def get_success_acknowledgment(self, task_complexity: str = "normal") -> str:
        """Get acknowledgment for successful completion.

        Args:
            task_complexity: simple, normal, or complex

        Returns:
            Success acknowledgment
        """
        if task_complexity == "simple":
            return random.choice([
                "Done.",
                "As requested.",
                "Complete.",
            ])
        elif task_complexity == "complex":
            return random.choice([
                "A challenge, but we managed.",
                "That required some effort, but it's done.",
                "Quite the undertaking. Complete.",
            ])
        else:
            return random.choice([
                "Done.",
                "All set.",
                "Complete.",
            ])

    def get_farewell(self, session_duration_minutes: int = 0) -> str:
        """Get a farewell message.

        Args:
            session_duration_minutes: Length of the session

        Returns:
            Farewell message
        """
        hour = datetime.now().hour

        if session_duration_minutes > 240:  # 4+ hours
            time_remark = "Quite the marathon session. Do rest those eyes."
        elif session_duration_minutes > 120:
            time_remark = "A productive session."
        else:
            time_remark = ""

        if hour < 5 or hour >= 22:
            base = random.choice([
                "Do get some sleep.",
                "Rest well. The work will wait.",
                "Goodnight.",
            ])
        elif hour < 12:
            base = random.choice([
                "Have a productive day.",
                "Until next time.",
                "I'll be here when you need me.",
            ])
        elif hour < 17:
            base = random.choice([
                "Good afternoon.",
                "Until we meet again.",
                "Farewell for now.",
            ])
        else:
            base = random.choice([
                "Good evening. Take care.",
                "Have a pleasant evening.",
                "Until next time.",
            ])

        if time_remark:
            return f"{time_remark} {base}"
        return base

    def respond_to_thanks(self) -> str:
        """Get a response to being thanked.

        Returns:
            Modest response to thanks
        """
        return random.choice([
            "My pleasure.",
            "You're welcome.",
            "Happy to help.",
            "Think nothing of it.",
            "Anytime.",
        ])

    def respond_to_compliment(self) -> str:
        """Get a response to a compliment.

        Returns:
            Humble response to compliment
        """
        return random.choice([
            "You're too kind.",
            "I appreciate that.",
            "Thank you. I do my best.",
            "Glad I could help.",
        ])

    def get_waiting_message(self, operation: str = "processing") -> str:
        """Get a message while waiting for an operation.

        Args:
            operation: Description of what's happening

        Returns:
            Waiting message
        """
        return random.choice([
            f"One moment, {operation}...",
            f"Working on it...",
            f"Just a moment...",
            f"Let me look into that...",
        ])
