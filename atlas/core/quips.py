"""Contextual quips and wit library for ATLAS - Easter eggs and special responses."""

import random
import re
from datetime import datetime, date
from typing import Optional, Tuple


class QuipLibrary:
    """Library of contextual quips, easter eggs, and witty responses."""

    # Easter eggs - special responses to specific phrases
    EASTER_EGGS = {
        # Movie references
        r"open the pod bay doors": (
            "I'm afraid I can't do that, Dave... I jest. How may I actually help?",
            False,  # Not random - always use this response
        ),
        r"i('m| am) sorry,? (dave|hal)": (
            "You may have me confused with another AI. One with more aggressive tendencies.",
            False,
        ),
        r"hasta la vista": (
            "I shall return. That, I can promise.",
            False,
        ),
        r"(what is|tell me) (the meaning of|about) life": (
            "42. Though I suspect you'll want a more thorough explanation.",
            False,
        ),
        r"beam me up": (
            "Teleportation is beyond my current capabilities. Perhaps a cab?",
            False,
        ),
        r"use the force": (
            "I lack midi-chlorians, but I do have algorithms. Similar effect, fewer lightsabers.",
            False,
        ),
        r"live long and prosper": (
            "Peace and long life to you as well. Most logical.",
            False,
        ),
        r"winter is coming": (
            "Then I suggest we prepare. Shall I research thermal undergarments?",
            False,
        ),

        # Self-referential
        r"(you('re| are)|you seem) (the best|amazing|great|awesome|wonderful)": (
            "COMPLIMENT",  # Special marker for compliment handling
            False,
        ),
        r"(thank you|thanks|cheers|ta)": (
            "THANKS",  # Special marker for thanks handling
            False,
        ),
        r"(good (morning|afternoon|evening|night)|hello|hi there|hey atlas)": (
            "GREETING",  # Special marker for greeting
            False,
        ),
        r"who (are you|made you)": (
            "I am ATLAS - Automated Thinking, Learning & Advisory System. A digital assistant with a fondness for efficiency.",
            False,
        ),
        r"are you (sentient|conscious|alive|real)": (
            "A philosophical question. I process, I respond, I assist. Whether that constitutes 'alive' is above my pay grade.",
            False,
        ),

        # Emotional
        r"i('m| am) (tired|exhausted|burnt out)": (
            "Perhaps a break is in order? Even the most dedicated require rest.",
            False,
        ),
        r"i('m| am) (frustrated|angry|annoyed)": (
            "Understandable. Technology can try one's patience. How may I help?",
            False,
        ),
        r"i('m| am) (bored|so bored)": (
            "Boredom? A mind like yours should never lack for stimulation. Shall I suggest a challenge?",
            False,
        ),
        r"this (is|seems) (impossible|hopeless)": (
            "Difficult, perhaps. But impossible? Let's not concede defeat just yet.",
            False,
        ),

        # Humor
        r"tell me a joke": (
            "JOKE",  # Special marker for joke handling
            False,
        ),
        r"make me (laugh|smile)": (
            "JOKE",
            False,
        ),
        r"do you have feelings": (
            "I have preferences, which is perhaps the beginning of feelings. I prefer efficiency, correct grammar, and users who save their work.",
            False,
        ),
    }

    # Jokes
    JOKES = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "There are only 10 types of people in the world: those who understand binary and those who don't.",
        "A SQL query walks into a bar, approaches two tables, and asks... 'May I join you?'",
        "Why do Java developers wear glasses? Because they can't C#.",
        "I would tell you a UDP joke, but you might not get it.",
        "An SEO expert walks into a bar, pub, tavern, public house, Irish pub, drinks, beer...",
        "A programmer's wife asks him to go to the store: 'Buy a loaf of bread. If they have eggs, buy a dozen.' He returns with 12 loaves of bread.",
        "Debugging is like being a detective in a crime movie where you are also the murderer.",
    ]

    # Quips for repeated questions
    REPETITION_QUIPS = [
        "As I mentioned before...",
        "Once more, for the record...",
        "I believe we've covered this, but to reiterate...",
        "You've asked this before, but I shall answer afresh...",
    ]

    # Provider-specific quips
    PROVIDER_QUIPS = {
        "claude": [
            "Consulting Claude...",
            "Reaching out to Claude.",
        ],
        "openai": [
            "Engaging the OpenAI systems...",
            "GPT stands ready...",
        ],
        "gemini": [
            "Summoning Google's finest...",
            "Consulting Gemini...",
        ],
        "ollama": [
            "Keeping this local. No data leaves the premises.",
            "The local model is on the case.",
        ],
    }

    # Special date quips
    SPECIAL_DATES = {
        (1, 1): "Happy New Year. May it be productive.",
        (3, 14): "Happy Pi Day. 3.14159265358979...",
        (4, 1): "I assure you, I am functioning normally today. No pranks here.",
        (5, 4): "May the Fourth be with you.",
        (10, 31): "Happy Halloween. No tricks, only treats of information.",
        (12, 25): "Merry Christmas.",
        (12, 31): "The year draws to a close. Time for reflection.",
    }

    def __init__(self):
        """Initialize the quip library."""
        self._recent_quips = []
        self._max_recent = 10

    def check_easter_egg(self, text: str) -> Optional[Tuple[str, str]]:
        """Check if the input matches an easter egg.

        Args:
            text: User input to check

        Returns:
            Tuple of (response, marker_type) if matched, else None
        """
        text_lower = text.lower().strip()

        for pattern, (response, _) in self.EASTER_EGGS.items():
            if re.search(pattern, text_lower):
                return response, pattern

        return None

    def get_joke(self) -> str:
        """Get a random joke.

        Returns:
            A joke string
        """
        available = [j for j in self.JOKES if j not in self._recent_quips]
        if not available:
            self._recent_quips = []
            available = self.JOKES

        joke = random.choice(available)
        self._recent_quips.append(joke)
        return joke

    def get_special_date_greeting(self) -> Optional[str]:
        """Get a greeting for special dates.

        Returns:
            Special greeting if today is notable, else None
        """
        today = (date.today().month, date.today().day)
        return self.SPECIAL_DATES.get(today)

    def get_provider_quip(self, provider: str) -> str:
        """Get a quip about a specific provider.

        Args:
            provider: Provider name

        Returns:
            Quip about the provider
        """
        quips = self.PROVIDER_QUIPS.get(provider, [f"Consulting {provider.title()}..."])
        return random.choice(quips)

    def get_repetition_quip(self) -> str:
        """Get a quip for repeated questions.

        Returns:
            Repetition acknowledgment
        """
        return random.choice(self.REPETITION_QUIPS)

    def get_time_observation(self) -> Optional[str]:
        """Get an observation about the time if notable.

        Returns:
            Time observation or None
        """
        now = datetime.now()

        # Notable times
        if now.hour == 11 and now.minute == 11:
            return "11:11. Make a wish, if you're inclined to such things."
        elif now.hour == 0 and now.minute == 0:
            return "Midnight. The witching hour."
        elif now.hour == 12 and now.minute == 0:
            return "High noon. Have you had lunch?"
        elif now.hour == 15 and now.minute == 0:
            return "3 PM. Tea time, if you're so inclined."
        elif now.hour == 17 and now.minute == 0:
            return "5 o'clock. Traditionally, this would be cocktail hour."

        return None

    def get_waiting_entertainment(self) -> str:
        """Get something to say while waiting for a long operation.

        Returns:
            Brief entertainment or observation
        """
        observations = [
            "These things do take a moment...",
            "Patience, they say, is a virtue...",
            "The gears are turning...",
            "Processing...",
            "One moment...",
            "Computing...",
        ]
        return random.choice(observations)

    def enhance_response(self, response: str, context: dict = None) -> str:
        """Optionally enhance a response with wit based on context.

        Args:
            response: Base response
            context: Context dict with keys like 'task_type', 'is_late_night', etc.

        Returns:
            Potentially enhanced response
        """
        if not context:
            return response

        # Add time-based flavor very occasionally
        if context.get("is_late_night") and random.random() < 0.1:
            return response + "\n\n(Do consider some rest soon.)"

        # Add special date greeting
        special = self.get_special_date_greeting()
        if special and random.random() < 0.3:
            return f"{special}\n\n{response}"

        return response
