"""Enhanced briefing system for ATLAS - morning and evening reports."""

import json
import random
import shutil
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger("atlas.briefings")


class BriefingEnhancer:
    """Provides enhanced data for morning and evening briefings."""

    # Motivational quotes for the day
    QUOTES = [
        ("The only way to do great work is to love what you do.", "Steve Jobs"),
        ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
        ("Stay hungry, stay foolish.", "Steve Jobs"),
        ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
        ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
        ("First, solve the problem. Then, write the code.", "John Johnson"),
        ("Experience is the name everyone gives to their mistakes.", "Oscar Wilde"),
        ("The only true wisdom is in knowing you know nothing.", "Socrates"),
        ("Simplicity is the soul of efficiency.", "Austin Freeman"),
        ("Make it work, make it right, make it fast.", "Kent Beck"),
        ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
        ("Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.", "Antoine de Saint-Exupery"),
        ("The advance of technology is based on making it fit in so that you don't really even notice it.", "Bill Gates"),
        ("It's not a bug – it's an undocumented feature.", "Anonymous"),
        ("Measuring programming progress by lines of code is like measuring aircraft building progress by weight.", "Bill Gates"),
        ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
        ("If debugging is the process of removing software bugs, then programming must be the process of putting them in.", "Edsger Dijkstra"),
        ("The most important property of a program is whether it accomplishes the intention of its user.", "C.A.R. Hoare"),
        ("A good programmer is someone who always looks both ways before crossing a one-way street.", "Doug Linder"),
        ("Don't worry if it doesn't work right. If everything did, you'd be out of a job.", "Mosher's Law"),
    ]

    def __init__(self, data_dir: Path, memory_dir: Path):
        """Initialize briefing enhancer.

        Args:
            data_dir: Directory for data storage
            memory_dir: Directory for memory/conversation storage
        """
        self.data_dir = data_dir
        self.memory_dir = memory_dir
        self.reminders_file = data_dir / "reminders.json"
        self.notes_dir = data_dir / "daily_notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    # ==================== START OF DAY FEATURES ====================

    def get_quote_of_the_day(self) -> dict:
        """Get a motivational quote for the day.

        Returns:
            Dict with 'quote' and 'author' keys
        """
        # Use date as seed for consistent daily quote
        today = date.today()
        random.seed(today.toordinal())
        quote, author = random.choice(self.QUOTES)
        random.seed()  # Reset seed
        return {"quote": quote, "author": author}

    def get_reminders(self) -> List[dict]:
        """Get pending reminders.

        Returns:
            List of reminder dicts with 'text', 'created', 'due' keys
        """
        if not self.reminders_file.exists():
            return []

        try:
            reminders = json.loads(self.reminders_file.read_text())
            # Filter to active reminders (not completed, due today or earlier)
            today = date.today().isoformat()
            active = [
                r for r in reminders
                if not r.get("completed") and r.get("due", today) <= today
            ]
            return active
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Could not load reminders: {e}")
            return []

    def add_reminder(self, text: str, due_date: Optional[str] = None) -> dict:
        """Add a new reminder.

        Args:
            text: Reminder text
            due_date: Optional due date (ISO format)

        Returns:
            The created reminder dict
        """
        reminders = []
        if self.reminders_file.exists():
            try:
                reminders = json.loads(self.reminders_file.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Could not load existing reminders: {e}")

        reminder = {
            "id": len(reminders) + 1,
            "text": text,
            "created": datetime.now().isoformat(),
            "due": due_date or date.today().isoformat(),
            "completed": False,
        }
        reminders.append(reminder)
        self.reminders_file.write_text(json.dumps(reminders, indent=2))
        return reminder

    def complete_reminder(self, reminder_id: int) -> bool:
        """Mark a reminder as completed.

        Args:
            reminder_id: ID of reminder to complete

        Returns:
            True if successful
        """
        if not self.reminders_file.exists():
            return False

        try:
            reminders = json.loads(self.reminders_file.read_text())
            for r in reminders:
                if r.get("id") == reminder_id:
                    r["completed"] = True
                    r["completed_at"] = datetime.now().isoformat()
                    self.reminders_file.write_text(json.dumps(reminders, indent=2))
                    return True
            return False
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not complete reminder: {e}")
            return False

    def get_system_status(self) -> dict:
        """Get system status information.

        Returns:
            Dict with disk usage, memory, and service status
        """
        status = {}

        # Disk usage
        try:
            total, used, free = shutil.disk_usage("/")
            status["disk"] = {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "percent_used": round(used / total * 100, 1),
            }
        except Exception as e:
            logger.debug(f"Could not read disk usage: {e}")
            status["disk"] = {"error": "Could not read disk usage"}

        # Check if Ollama is running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "ollama"],
                capture_output=True,
                timeout=5,
            )
            status["ollama_running"] = result.returncode == 0
        except Exception as e:
            logger.debug(f"Could not check Ollama status: {e}")
            status["ollama_running"] = None

        # Memory usage (if available)
        try:
            with open("/proc/meminfo") as f:
                meminfo = f.read()
                for line in meminfo.split("\n"):
                    if line.startswith("MemTotal:"):
                        total = int(line.split()[1]) / 1024 / 1024  # GB
                    elif line.startswith("MemAvailable:"):
                        available = int(line.split()[1]) / 1024 / 1024  # GB
                status["memory"] = {
                    "total_gb": round(total, 1),
                    "available_gb": round(available, 1),
                    "percent_used": round((total - available) / total * 100, 1),
                }
        except Exception:
            status["memory"] = {"error": "Could not read memory info"}

        return status

    def get_weekly_usage_stats(self, usage_tracker) -> dict:
        """Get weekly AI usage statistics.

        Args:
            usage_tracker: UsageTracker instance

        Returns:
            Dict with weekly usage percentages by provider
        """
        stats = {}

        # Get limits and calculate weekly usage
        for provider in ["claude", "openai", "gemini"]:
            daily_limit = usage_tracker.limits.get(provider, 0)
            if daily_limit > 0:
                weekly_limit = daily_limit * 7
                # Get weekly usage from history
                weekly_used = usage_tracker.get_weekly_usage(provider)
                stats[provider] = {
                    "daily_limit": daily_limit,
                    "weekly_limit": weekly_limit,
                    "weekly_used": weekly_used,
                    "weekly_percent": round(weekly_used / weekly_limit * 100, 1) if weekly_limit > 0 else 0,
                    "today_used": usage_tracker.get_usage(provider),
                }

        return stats

    async def get_news_headlines(self, interests: List[str] = None) -> dict:
        """Get relevant news headlines - both AI-specific and general tech.

        Args:
            interests: List of topics to filter news

        Returns:
            Dict with 'ai_news' and 'tech_news' lists
        """
        result = {
            "ai_news": [],
            "tech_news": [],
        }

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Fetch top stories from Hacker News
                async with session.get(
                    "https://hacker-news.firebaseio.com/v0/topstories.json",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        story_ids = await response.json()

                        # AI-related keywords
                        ai_keywords = [
                            'ai', 'artificial intelligence', 'machine learning', 'ml',
                            'gpt', 'llm', 'chatgpt', 'claude', 'gemini', 'openai',
                            'anthropic', 'deepmind', 'neural', 'transformer',
                            'diffusion', 'stable diffusion', 'midjourney', 'dall-e',
                            'langchain', 'vector', 'embedding', 'fine-tun', 'rag',
                            'agent', 'copilot', 'llama', 'mistral', 'groq',
                        ]

                        # Fetch more stories to find AI ones
                        for story_id in story_ids[:50]:
                            if len(result["ai_news"]) >= 5 and len(result["tech_news"]) >= 5:
                                break

                            try:
                                async with session.get(
                                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                                    timeout=aiohttp.ClientTimeout(total=5),
                                ) as story_resp:
                                    if story_resp.status == 200:
                                        story = await story_resp.json()
                                        if story and story.get("title"):
                                            title_lower = story["title"].lower()
                                            headline = {
                                                "title": story["title"],
                                                "source": "Hacker News",
                                                "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                                "score": story.get("score", 0),
                                            }

                                            # Check if AI-related
                                            is_ai = any(kw in title_lower for kw in ai_keywords)

                                            if is_ai and len(result["ai_news"]) < 5:
                                                result["ai_news"].append(headline)
                                            elif not is_ai and len(result["tech_news"]) < 5:
                                                result["tech_news"].append(headline)
                            except Exception:
                                continue

                # Also try to fetch from AI-specific sources
                await self._fetch_ai_news(session, result)

        except Exception as e:
            logger.warning(f"Could not fetch news: {e}")

        return result

    async def _fetch_ai_news(self, session, result: dict):
        """Fetch AI-specific news from additional sources.

        Args:
            session: aiohttp session
            result: Dict to append results to
        """
        # Try fetching from Reddit r/MachineLearning or r/artificial
        try:
            async with session.get(
                "https://www.reddit.com/r/MachineLearning/hot.json?limit=10",
                headers={"User-Agent": "ATLAS/1.0"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", {}).get("children", [])

                    for post in posts:
                        if len(result["ai_news"]) >= 8:
                            break
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        if title and not post_data.get("stickied"):
                            # Avoid duplicates
                            if not any(h["title"] == title for h in result["ai_news"]):
                                result["ai_news"].append({
                                    "title": title[:100],
                                    "source": "r/MachineLearning",
                                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                    "score": post_data.get("score", 0),
                                })
        except Exception as e:
            logger.debug(f"Could not fetch Reddit AI news: {e}")

        # Try fetching from AI-focused RSS/sources
        try:
            # The Batch (deeplearning.ai newsletter) - check their feed
            async with session.get(
                "https://www.reddit.com/r/artificial/hot.json?limit=5",
                headers={"User-Agent": "ATLAS/1.0"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", {}).get("children", [])

                    for post in posts:
                        if len(result["ai_news"]) >= 10:
                            break
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        if title and not post_data.get("stickied"):
                            if not any(h["title"] == title for h in result["ai_news"]):
                                result["ai_news"].append({
                                    "title": title[:100],
                                    "source": "r/artificial",
                                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                    "score": post_data.get("score", 0),
                                })
        except Exception as e:
            logger.debug(f"Could not fetch r/artificial news: {e}")

    # ==================== END OF DAY FEATURES ====================

    async def generate_day_insights(self, conversations: List[dict], provider) -> str:
        """Use AI to generate insights from the day's conversations.

        Args:
            conversations: List of conversation dicts
            provider: AI provider to use for generation

        Returns:
            Insights summary string
        """
        if not conversations:
            return "No conversations to analyze today."

        # Build a summary of the day's conversations
        conv_summary = []
        for conv in conversations[:20]:  # Limit to last 20
            query = conv.get("user_message", "")[:100]
            task_type = conv.get("task_type", "general")
            conv_summary.append(f"- [{task_type}] {query}")

        prompt = f"""Analyze today's ATLAS session and provide brief insights.

Today's queries:
{chr(10).join(conv_summary)}

Provide a 2-3 sentence summary of:
1. Main themes or focus areas
2. Any patterns you notice
3. One suggestion for tomorrow

Keep it concise and professional."""

        try:
            response = await provider.generate(prompt, max_tokens=200)
            return response.strip()
        except Exception as e:
            logger.error(f"Could not generate insights: {e}")
            return "Unable to generate insights at this time."

    async def extract_action_items(self, conversations: List[dict], provider) -> List[str]:
        """Extract action items from the day's conversations.

        Args:
            conversations: List of conversation dicts
            provider: AI provider to use

        Returns:
            List of action item strings
        """
        if not conversations:
            return []

        # Get responses that might contain action items
        responses = []
        for conv in conversations[:10]:
            response = conv.get("assistant_response", "")[:500]
            if any(word in response.lower() for word in ["should", "need to", "recommend", "suggest", "try", "consider"]):
                responses.append(response)

        if not responses:
            return []

        prompt = f"""Extract any action items or recommendations from these AI responses.

Responses:
{chr(10).join(responses[:5])}

List only clear, actionable items (max 5). Format as simple bullet points.
If no clear action items, respond with "None identified"."""

        try:
            response = await provider.generate(prompt, max_tokens=200)
            if "none identified" in response.lower():
                return []
            # Parse bullet points
            items = [line.strip().lstrip("-•*").strip()
                    for line in response.split("\n")
                    if line.strip() and line.strip()[0] in "-•*"]
            return items[:5]
        except Exception as e:
            logger.error(f"Could not extract action items: {e}")
            return []

    async def generate_tomorrow_suggestions(self, conversations: List[dict], provider) -> List[str]:
        """Generate suggestions for tomorrow based on today's work.

        Args:
            conversations: List of conversation dicts
            provider: AI provider to use

        Returns:
            List of suggestion strings
        """
        if not conversations:
            return ["Start fresh with a clear goal for the day."]

        # Analyze what was worked on
        task_types = {}
        for conv in conversations:
            task_type = conv.get("task_type", "general")
            task_types[task_type] = task_types.get(task_type, 0) + 1

        main_focus = max(task_types.items(), key=lambda x: x[1])[0] if task_types else "general"

        prompt = f"""Based on a day focused mainly on {main_focus} tasks ({len(conversations)} total queries),
suggest 2-3 things to focus on tomorrow. Be specific and actionable.
Keep suggestions brief (one line each)."""

        try:
            response = await provider.generate(prompt, max_tokens=150)
            suggestions = [line.strip().lstrip("-•*0123456789.").strip()
                          for line in response.split("\n")
                          if line.strip() and len(line.strip()) > 10]
            return suggestions[:3]
        except Exception as e:
            logger.error(f"Could not generate suggestions: {e}")
            return ["Review and continue yesterday's work."]

    def get_weekly_trends(self, usage_tracker) -> dict:
        """Calculate weekly usage trends.

        Args:
            usage_tracker: UsageTracker instance

        Returns:
            Dict with trend data
        """
        trends = {
            "total_queries_this_week": 0,
            "most_used_provider": None,
            "most_common_task": None,
            "busiest_day": None,
            "comparison_to_last_week": None,
        }

        try:
            # Get this week's data
            weekly_data = usage_tracker.get_weekly_breakdown()

            if weekly_data:
                # Total queries
                trends["total_queries_this_week"] = sum(
                    sum(day.values()) for day in weekly_data.values()
                )

                # Most used provider
                provider_totals = {}
                for day_data in weekly_data.values():
                    for provider, count in day_data.items():
                        provider_totals[provider] = provider_totals.get(provider, 0) + count

                if provider_totals:
                    trends["most_used_provider"] = max(provider_totals.items(), key=lambda x: x[1])

                # Busiest day
                day_totals = {day: sum(data.values()) for day, data in weekly_data.items()}
                if day_totals:
                    busiest = max(day_totals.items(), key=lambda x: x[1])
                    trends["busiest_day"] = busiest

        except Exception as e:
            logger.error(f"Could not calculate trends: {e}")

        return trends

    def export_daily_notes(self, report: dict, format: str = "markdown") -> Path:
        """Export daily report to notes file.

        Args:
            report: End of day report dictionary
            format: Export format (markdown, json)

        Returns:
            Path to exported file
        """
        today = date.today().isoformat()

        if format == "json":
            path = self.notes_dir / f"{today}.json"
            path.write_text(json.dumps(report, indent=2, default=str))
        else:
            path = self.notes_dir / f"{today}.md"
            lines = [
                f"# Daily Notes - {report.get('date', today)}",
                "",
                "## Session Summary",
                f"- Duration: {report.get('session_duration_minutes', 0)} minutes",
                f"- Queries: {report.get('queries_made', 0)}",
                "",
            ]

            if report.get("insights"):
                lines.extend([
                    "## Insights",
                    report["insights"],
                    "",
                ])

            if report.get("action_items"):
                lines.extend([
                    "## Action Items",
                ])
                for item in report["action_items"]:
                    lines.append(f"- [ ] {item}")
                lines.append("")

            if report.get("tomorrow_suggestions"):
                lines.extend([
                    "## Tomorrow",
                ])
                for suggestion in report["tomorrow_suggestions"]:
                    lines.append(f"- {suggestion}")
                lines.append("")

            if report.get("summary"):
                lines.extend([
                    "## Summary",
                    report["summary"],
                    "",
                ])

            path.write_text("\n".join(lines))

        return path
