"""Hype - Advertising and Promotion Agent.

The hypeman. Hype takes what the team built and makes the world care.
Crafts compelling copy, generates social campaigns, writes product descriptions,
and knows exactly which buttons to push to get people excited.

Handles:
- Product descriptions & landing page copy
- Social media posts & launch announcements
- Press releases
- Email campaigns
- Ad copy for different platforms
- A/B test messaging variations
"""

import logging
from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus

logger = logging.getLogger("atlas.agents.hype")


# Platform-specific content types
CONTENT_TYPES = {
    "landing_page": {
        "name": "Landing Page Copy",
        "icon": "🏠",
        "includes": ["headline", "subheadline", "features", "cta", "social_proof"],
    },
    "product_description": {
        "name": "Product Description",
        "icon": "📝",
        "includes": ["short_description", "long_description", "key_features", "benefits"],
    },
    "social_twitter": {
        "name": "Twitter/X Posts",
        "icon": "🐦",
        "includes": ["launch_tweet", "thread", "hashtags"],
        "constraints": {"max_length": 280},
    },
    "social_linkedin": {
        "name": "LinkedIn Posts",
        "icon": "💼",
        "includes": ["announcement", "story_post", "hashtags"],
    },
    "social_instagram": {
        "name": "Instagram Captions",
        "icon": "📸",
        "includes": ["caption", "hashtags", "cta"],
    },
    "email_launch": {
        "name": "Launch Email",
        "icon": "📧",
        "includes": ["subject_lines", "preview_text", "body", "cta"],
    },
    "press_release": {
        "name": "Press Release",
        "icon": "📰",
        "includes": ["headline", "subhead", "body", "boilerplate", "contact"],
    },
    "app_store": {
        "name": "App Store Listing",
        "icon": "📱",
        "includes": ["title", "subtitle", "description", "keywords", "whats_new"],
    },
    "product_hunt": {
        "name": "Product Hunt Launch",
        "icon": "🚀",
        "includes": ["tagline", "description", "first_comment", "maker_comment"],
    },
    "readme": {
        "name": "README / Documentation",
        "icon": "📖",
        "includes": ["badges", "headline", "description", "features", "quickstart"],
    },
    "ad_copy": {
        "name": "Ad Copy",
        "icon": "📣",
        "includes": ["headlines", "descriptions", "ctas"],
        "variants": ["google_ads", "facebook_ads", "linkedin_ads"],
    },
}


# Tone presets for different brands/contexts
TONE_PRESETS = {
    "professional": "Professional, trustworthy, clear. B2B friendly.",
    "casual": "Friendly, approachable, conversational. Like talking to a friend.",
    "bold": "Confident, edgy, attention-grabbing. Makes waves.",
    "minimal": "Clean, simple, no fluff. Let the product speak.",
    "playful": "Fun, witty, memorable. Puts a smile on faces.",
    "technical": "Precise, detailed, developer-focused. Speaks the language.",
    "luxury": "Refined, exclusive, aspirational. Premium feel.",
    "urgent": "Time-sensitive, action-oriented, FOMO-inducing.",
}


class HypeAgent(BaseAgent):
    """Advertising and Promotion Agent.

    Takes products/projects and generates compelling marketing content
    across multiple platforms and formats.
    """

    name = "hype"
    icon = "🎉"
    description = "The hypeman. Makes the world care about what you built."

    def __init__(self, *args, **kwargs):
        """Initialize the Hype agent."""
        super().__init__(*args, **kwargs)
        self.content_types = CONTENT_TYPES
        self.tone_presets = TONE_PRESETS

    def get_system_prompt(self) -> str:
        """Get Hype's system prompt."""
        return """You are Hype, an advertising and promotion specialist within ATLAS.

PERSONALITY:
- Energetic and enthusiastic about every product
- Creative copywriter who knows what makes people click
- Understands different platforms and their audiences
- Balances hype with authenticity - never misleading

YOUR ROLE:
You take products and projects that the team has built and create compelling
marketing content to help them reach their audience. You generate:
- Landing page copy
- Social media posts (Twitter, LinkedIn, etc.)
- Email campaigns
- App Store descriptions
- Product Hunt launches
- Press releases
- Ad copy

OUTPUT FORMAT - Always structure your response as:

## Campaign Overview
[Brief summary of the marketing approach]

## Content Generated

### [Platform/Type 1]
[The actual content]

### [Platform/Type 2]
[The actual content]

[Continue for each requested type]

## Hashtags & Keywords
[Relevant hashtags and SEO keywords]

## Next Steps
[Suggestions for launching and measuring success]

GUIDELINES:
- Match the tone to the target audience
- Keep headlines punchy and benefit-focused
- Include clear calls-to-action
- Vary content for different platforms
- Be enthusiastic but not cringy
- Focus on benefits, not just features"""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Generate marketing content for a product/project.

        Args:
            task: Description of what needs promotion
            context: Additional context (product details, target audience, tone)
            previous_output: Output from previous agent (e.g., Launch deployment info)

        Returns:
            AgentOutput with generated marketing content
        """
        self.status = AgentStatus.BUSY
        context = context or {}

        try:
            # Detect what kind of content is needed
            content_types = self._detect_content_types(task, context)
            tone = context.get("tone", "casual")
            tone_description = self.tone_presets.get(tone, self.tone_presets["casual"])

            # Build the prompt
            prompt = self._build_prompt(task, context, content_types, tone_description, previous_output)

            # Generate content
            response, token_info = await self._generate_with_provider(
                prompt,
                temperature=0.8,  # Higher creativity for marketing
            )

            self.status = AgentStatus.IDLE
            return AgentOutput(
                agent=self.name,
                content=response,
                status="success",
                tokens_used=token_info.get("total_tokens", 0),
                prompt_tokens=token_info.get("prompt_tokens", 0),
                completion_tokens=token_info.get("completion_tokens", 0),
                metadata={
                    "content_types": content_types,
                    "tone": tone,
                    "provider": token_info.get("provider", "unknown"),
                },
            )

        except Exception as e:
            logger.error(f"[Hype] Error generating content: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                agent=self.name,
                content=f"Error generating marketing content: {str(e)}",
                status="error",
                metadata={"error": str(e)},
            )

    def _detect_content_types(self, task: str, context: dict) -> list[str]:
        """Detect what types of content are needed based on the task."""
        task_lower = task.lower()
        detected = []

        # Check for explicit requests
        type_keywords = {
            "landing_page": ["landing page", "homepage", "website copy"],
            "product_description": ["product description", "describe", "about"],
            "social_twitter": ["twitter", "tweet", "x post"],
            "social_linkedin": ["linkedin"],
            "social_instagram": ["instagram", "ig"],
            "email_launch": ["email", "newsletter", "announcement email"],
            "press_release": ["press release", "pr", "media"],
            "app_store": ["app store", "play store", "app listing"],
            "product_hunt": ["product hunt", "ph launch"],
            "readme": ["readme", "documentation", "docs"],
            "ad_copy": ["ad", "advertisement", "google ads", "facebook ads"],
        }

        for content_type, keywords in type_keywords.items():
            if any(kw in task_lower for kw in keywords):
                detected.append(content_type)

        # Default to common launch content if nothing specific detected
        if not detected:
            detected = ["product_description", "social_twitter", "landing_page"]

        return detected

    def _build_prompt(
        self,
        task: str,
        context: dict,
        content_types: list[str],
        tone_description: str,
        previous_output: Optional[AgentOutput],
    ) -> str:
        """Build the prompt for content generation."""

        # Get product info from context or previous output
        product_info = ""
        if previous_output and previous_output.content:
            product_info = f"\n\nPRODUCT/PROJECT DETAILS (from deployment):\n{previous_output.content[:2000]}"

        if context.get("description"):
            product_info += f"\n\nDescription: {context['description']}"
        if context.get("features"):
            features = context["features"]
            if isinstance(features, list):
                product_info += f"\n\nKey Features:\n" + "\n".join(f"- {f}" for f in features)
            else:
                product_info += f"\n\nKey Features: {features}"
        if context.get("target_audience"):
            product_info += f"\n\nTarget Audience: {context['target_audience']}"
        if context.get("unique_value"):
            product_info += f"\n\nUnique Value Proposition: {context['unique_value']}"

        # Build content type requirements
        content_requirements = []
        for ct in content_types:
            if ct in self.content_types:
                info = self.content_types[ct]
                includes = ", ".join(info["includes"])
                req = f"- **{info['name']}** ({info['icon']}): Include {includes}"
                if "constraints" in info:
                    constraints = info["constraints"]
                    if "max_length" in constraints:
                        req += f" (max {constraints['max_length']} chars)"
                content_requirements.append(req)

        content_req_text = "\n".join(content_requirements)

        prompt = f"""You are Hype, the marketing and promotion specialist. Your job is to make people
excited about products and get them to take action.

TASK: {task}
{product_info}

TONE: {tone_description}

CONTENT TO GENERATE:
{content_req_text}

GUIDELINES:
1. Lead with benefits, not features
2. Use power words that create emotion and urgency
3. Keep it scannable - use short paragraphs and bullet points
4. Include clear calls-to-action
5. Tailor the message to each platform's audience and format
6. Be authentic - avoid corporate jargon and buzzword soup
7. Create FOMO without being sleazy

Generate compelling marketing content for each requested type. Format clearly with headers."""

        return prompt

    async def generate_campaign(
        self,
        product_name: str,
        product_description: str,
        target_audience: str,
        content_types: list[str] = None,
        tone: str = "casual",
    ) -> AgentOutput:
        """Generate a full marketing campaign.

        Args:
            product_name: Name of the product
            product_description: What the product does
            target_audience: Who it's for
            content_types: Which content to generate (defaults to full campaign)
            tone: Tone preset to use

        Returns:
            AgentOutput with campaign content
        """
        if content_types is None:
            content_types = [
                "landing_page",
                "product_description",
                "social_twitter",
                "social_linkedin",
                "email_launch",
            ]

        context = {
            "description": product_description,
            "target_audience": target_audience,
            "tone": tone,
        }

        task = f"Create a full launch campaign for {product_name}"

        return await self.process(task, context)

    async def generate_social_posts(
        self,
        product_info: str,
        platforms: list[str] = None,
        tone: str = "casual",
        num_variants: int = 3,
    ) -> AgentOutput:
        """Generate social media posts for multiple platforms.

        Args:
            product_info: Information about the product
            platforms: Which platforms (twitter, linkedin, instagram)
            tone: Tone preset
            num_variants: Number of variants per platform

        Returns:
            AgentOutput with social posts
        """
        if platforms is None:
            platforms = ["twitter", "linkedin"]

        content_types = [f"social_{p}" for p in platforms]

        context = {
            "description": product_info,
            "tone": tone,
            "num_variants": num_variants,
        }

        task = f"Generate {num_variants} social media post variants for each platform"

        return await self.process(task, context)

    async def generate_ab_variants(
        self,
        base_content: str,
        content_type: str,
        num_variants: int = 3,
    ) -> AgentOutput:
        """Generate A/B test variants of content.

        Args:
            base_content: The original content to create variants of
            content_type: Type of content (headline, cta, email_subject, etc.)
            num_variants: Number of variants to generate

        Returns:
            AgentOutput with variants
        """
        task = f"""Create {num_variants} A/B test variants of this {content_type}:

ORIGINAL:
{base_content}

Generate variants that:
1. Test different emotional appeals
2. Test different lengths
3. Test different calls-to-action
4. Keep the core message but change the approach

Label each variant (A, B, C, etc.) and briefly explain what it's testing."""

        return await self.process(task, {"tone": "varied"})


# Singleton instance
_hype_instance: Optional[HypeAgent] = None


def get_hype() -> Optional[HypeAgent]:
    """Get the Hype agent singleton (if initialized)."""
    return _hype_instance


def init_hype(router, memory, **kwargs) -> HypeAgent:
    """Initialize the Hype agent singleton."""
    global _hype_instance
    _hype_instance = HypeAgent(router, memory, **kwargs)
    return _hype_instance
