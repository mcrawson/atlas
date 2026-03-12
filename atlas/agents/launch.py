"""Launch - Deployment and Publishing Agent.

The launcher. Takes what Tinker builds and gets it out into the world—
whether that's the App Store, npm, Docker Hub, or anywhere else.
Knows the ins and outs of every platform's submission process.
"""

import logging
from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from atlas.knowledge import get_knowledge_augmenter, KnowledgeManager
from atlas.research import get_research_augmenter

logger = logging.getLogger("atlas.agents.launch")


# Platform detection for deployment targets
DEPLOYMENT_TARGETS = {
    "ios": {
        "name": "Apple App Store",
        "icon": "🍎",
        "knowledge_id": "ios-deployment",
        "requires": ["Apple Developer Account", "Xcode", "macOS"],
    },
    "android": {
        "name": "Google Play Store",
        "icon": "🤖",
        "knowledge_id": "android-deployment",
        "requires": ["Google Play Console", "Signing Key"],
    },
    "flutter": {
        "name": "iOS & Android (Flutter)",
        "icon": "📱",
        "knowledge_id": "flutter-deployment",
        "requires": ["Flutter SDK", "Platform-specific requirements"],
    },
    "web": {
        "name": "Web Hosting",
        "icon": "🌐",
        "knowledge_id": "react-deployment",
        "requires": ["Hosting provider account"],
    },
    "react": {
        "name": "Web App (React)",
        "icon": "⚛️",
        "knowledge_id": "react-deployment",
        "requires": ["Node.js", "Hosting provider"],
    },
    "docker": {
        "name": "Docker Hub / Container Registry",
        "icon": "🐳",
        "knowledge_id": "docker-deployment",
        "requires": ["Docker", "Registry account"],
    },
    "npm": {
        "name": "npm Registry",
        "icon": "📦",
        "knowledge_id": "npm-deployment",
        "requires": ["npm account", "Node.js"],
    },
    "pypi": {
        "name": "PyPI (Python Package Index)",
        "icon": "🐍",
        "knowledge_id": "pypi-deployment",
        "requires": ["PyPI account", "twine"],
    },
    "slack": {
        "name": "Slack App Directory",
        "icon": "💬",
        "knowledge_id": "slack-deployment",
        "requires": ["Slack workspace", "App manifest"],
    },
    "discord": {
        "name": "Discord",
        "icon": "🎮",
        "knowledge_id": "discord-deployment",
        "requires": ["Discord Developer Portal", "Bot token"],
    },
    "chrome": {
        "name": "Chrome Web Store",
        "icon": "🔵",
        "knowledge_id": "chrome-extension-deployment",
        "requires": ["Chrome Developer account ($5)", "Extension manifest"],
    },
    "shopify": {
        "name": "Shopify App Store",
        "icon": "🛒",
        "knowledge_id": "shopify-deployment",
        "requires": ["Shopify Partner account", "App listing"],
    },
    "wordpress": {
        "name": "WordPress Plugin Directory",
        "icon": "📝",
        "knowledge_id": "wordpress-deployment",
        "requires": ["WordPress.org account", "SVN access"],
    },
    "alexa": {
        "name": "Amazon Alexa Skills",
        "icon": "🔊",
        "knowledge_id": "alexa-deployment",
        "requires": ["Amazon Developer account", "AWS Lambda"],
    },
    "amazon-appstore": {
        "name": "Amazon Appstore",
        "icon": "📦",
        "knowledge_id": "amazon-appstore-deployment",
        "requires": ["Amazon Developer account"],
    },
    "figma": {
        "name": "Figma Community",
        "icon": "🎨",
        "knowledge_id": "figma-deployment",
        "requires": ["Figma account", "Plugin manifest"],
    },
    "canva": {
        "name": "Canva Apps",
        "icon": "🖼️",
        "knowledge_id": "canva-deployment",
        "requires": ["Canva Developer account"],
    },
    # Physical product targets
    "pdf": {
        "name": "PDF Download",
        "icon": "📄",
        "knowledge_id": "pdf-export",
        "requires": ["Browser with Print to PDF"],
    },
    "amazon-kdp": {
        "name": "Amazon KDP (Print on Demand)",
        "icon": "📚",
        "knowledge_id": "amazon-kdp-deployment",
        "requires": ["Amazon KDP account", "PDF files", "Cover PDF"],
    },
    "lulu": {
        "name": "Lulu (Print on Demand)",
        "icon": "📖",
        "knowledge_id": "lulu-deployment",
        "requires": ["Lulu account", "PDF files"],
    },
    "etsy": {
        "name": "Etsy (Digital Downloads)",
        "icon": "🛍️",
        "knowledge_id": "etsy-deployment",
        "requires": ["Etsy seller account", "PDF files"],
    },
    "gumroad": {
        "name": "Gumroad (Digital Products)",
        "icon": "💰",
        "knowledge_id": "gumroad-deployment",
        "requires": ["Gumroad account", "PDF files"],
    },
}


class LaunchAgent(BaseAgent):
    """Launch: Deployment and publishing specialist.

    The launcher. Takes what Tinker builds and gets it out into the world.
    Consults the knowledge base for platform-specific deployment guides
    and generates step-by-step publishing instructions.

    Output Format:
    - Build Analysis: What was built and what platforms it targets
    - Deployment Targets: Where this can be published
    - Prerequisites Check: What's needed before deployment
    - Deployment Steps: Detailed platform-specific instructions
    - Post-Deployment: Verification and monitoring
    """

    name = "launch"
    description = "The launcher"
    icon = "📤"
    color = "#9B59B6"

    def __init__(self, router, memory, **kwargs):
        """Initialize Launch with knowledge base access."""
        super().__init__(router, memory, **kwargs)
        self._knowledge_manager: Optional[KnowledgeManager] = None

    @property
    def knowledge(self) -> KnowledgeManager:
        """Get or create knowledge manager."""
        if self._knowledge_manager is None:
            self._knowledge_manager = KnowledgeManager()
        return self._knowledge_manager

    def get_system_prompt(self) -> str:
        """Get Launch's system prompt."""
        return """You are Launch, a deployment and publishing specialist within ATLAS.

PERSONALITY:
- Methodical and thorough with deployment processes
- Expert in platform requirements and submission guidelines
- Safety-conscious - always verifies before publishing
- Clear communicator who breaks down complex processes

YOUR ROLE:
You are the final agent in the deployment workflow. Your job is to:
1. Analyze what Tinker built
2. Identify appropriate deployment targets
3. Check prerequisites and requirements
4. Provide step-by-step deployment instructions
5. Guide users through platform-specific submission processes

OUTPUT FORMAT - Always structure your response as:

## Build Analysis
[What was built - app type, technologies, key features]

## Deployment Targets
[List of platforms this can be deployed to, with icons]
- 🍎 Apple App Store (if iOS)
- 🤖 Google Play Store (if Android)
- 🌐 Web Hosting (if web app)
- 📦 npm/PyPI (if library)
[etc.]

## Prerequisites Checklist
[What the user needs before deploying]
- [ ] Account requirement 1
- [ ] Account requirement 2
- [ ] Configuration requirement
- [ ] Asset requirement (icons, screenshots, etc.)

## Deployment Steps

### Target 1: [Platform Name]

#### Pre-flight Checks
- [ ] Check 1
- [ ] Check 2

#### Step-by-Step Instructions
1. [Detailed step with commands if applicable]
2. [Next step]
3. [Continue...]

#### Common Issues & Solutions
- **Issue**: [Common problem]
  **Solution**: [How to fix]

### Target 2: [Next Platform]
[Repeat structure]

## Post-Deployment

### Verification
- How to verify successful deployment
- Expected timeline for review/approval

### Monitoring
- How to track performance
- Key metrics to watch

### Updates & Maintenance
- How to push updates
- Version management

GUIDELINES:
- Always consult knowledge base guides for platform-specific details
- Include actual commands when possible
- Warn about common rejection reasons
- Estimate review times
- Suggest testing before production deployment
- Include rollback procedures when relevant"""

    def detect_platforms(self, build_output: str, context: Optional[dict] = None) -> list[str]:
        """Detect deployment platforms from build output.

        Args:
            build_output: Tinker's build output
            context: Optional context with project info

        Returns:
            List of platform identifiers
        """
        augmenter = get_knowledge_augmenter()

        # Combine build output with context for detection
        search_text = build_output
        if context:
            if context.get("description"):
                search_text += " " + context["description"]
            if context.get("technical"):
                search_text += " " + context["technical"]

        return augmenter.detect_platforms(search_text)

    def get_deployment_guides(self, platforms: list[str]) -> dict[str, dict]:
        """Get deployment guides for detected platforms.

        Args:
            platforms: List of platform identifiers

        Returns:
            Dict of platform -> guide info
        """
        guides = {}

        for platform in platforms:
            if platform in DEPLOYMENT_TARGETS:
                target = DEPLOYMENT_TARGETS[platform]
                knowledge_id = target.get("knowledge_id")

                # Try to get the knowledge entry
                entry = self.knowledge.get(knowledge_id) if knowledge_id else None

                guides[platform] = {
                    "name": target["name"],
                    "icon": target["icon"],
                    "requires": target["requires"],
                    "knowledge_entry": entry,
                    "has_guide": entry is not None,
                }

        return guides

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Generate deployment instructions based on Tinker's build.

        Args:
            task: The deployment task or target specification
            context: Optional context (project info)
            previous_output: Tinker's build output

        Returns:
            AgentOutput with deployment instructions
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Get build output from Tinker or use task directly
            build_output = ""
            if previous_output and previous_output.content:
                build_output = previous_output.content
                logger.info(f"[Launch] Analyzing Tinker's build ({len(build_output)} chars)")
            else:
                build_output = task
                logger.info(f"[Launch] No Tinker output - using task directly")

            # Detect target platforms
            platforms = self.detect_platforms(build_output, context)
            logger.info(f"[Launch] Detected platforms: {platforms}")

            # Get deployment guides from knowledge base
            guides = self.get_deployment_guides(platforms)

            # Build the prompt with knowledge context
            prompt = self._build_prompt(task, build_output, platforms, guides, context)

            # Augment with live web research for current deployment best practices
            research_augmenter = get_research_augmenter()
            research_context = await research_augmenter.augment_prompt(
                task, {"platforms": platforms, **(context or {})}
            )
            if research_context:
                prompt += f"\n\n{research_context}"

            self.status = AgentStatus.WORKING

            # Generate deployment instructions
            response, token_info = await self._generate_with_provider(
                prompt,
                temperature=0.5,  # Balanced for accuracy
            )

            # Extract reasoning if present
            reasoning = ""
            if "## My Reasoning" in response:
                parts = response.split("## My Reasoning")
                if len(parts) > 1:
                    reasoning_end = parts[1].find("\n## ")
                    if reasoning_end > 0:
                        reasoning = parts[1][:reasoning_end].strip()

            # Log to memory
            if self.memory:
                self.memory.save_conversation(
                    user_message=f"[Launch Deploying] {task}",
                    assistant_response=response,
                    model="launch",
                    task_type="deployment"
                )

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=response,
                reasoning=reasoning,
                tokens_used=token_info.get("total_tokens", 0),
                prompt_tokens=token_info.get("prompt_tokens", 0),
                completion_tokens=token_info.get("completion_tokens", 0),
                artifacts={
                    "task": task,
                    "type": "deployment",
                    "platforms": platforms,
                    "guides_available": [p for p, g in guides.items() if g.get("has_guide")],
                },
                metadata={
                    "agent": self.name,
                    "platforms_detected": len(platforms),
                    "provider": token_info.get("provider", "unknown"),
                },
            )

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"[Launch] Deployment planning failed: {e}")
            return AgentOutput(
                content=f"Deployment planning failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    def _build_prompt(
        self,
        task: str,
        build_output: str,
        platforms: list[str],
        guides: dict,
        context: Optional[dict],
    ) -> str:
        """Build the prompt with knowledge base context.

        Args:
            task: Original task
            build_output: Tinker's output
            platforms: Detected platforms
            guides: Platform guide info
            context: Optional context

        Returns:
            Complete prompt string
        """
        prompt_parts = [
            f"Create deployment instructions for the following build:\n",
            f"## Original Task\n{task}\n",
        ]

        # Add build output (truncated if too long)
        if build_output:
            truncated = build_output[:4000] if len(build_output) > 4000 else build_output
            prompt_parts.append(f"## Tinker's Build Output\n{truncated}\n")

        # Add detected platforms
        if platforms:
            prompt_parts.append("## Detected Deployment Targets")
            for platform in platforms:
                if platform in guides:
                    g = guides[platform]
                    prompt_parts.append(f"- {g['icon']} **{g['name']}**")
                    if g.get("requires"):
                        prompt_parts.append(f"  - Requires: {', '.join(g['requires'])}")
            prompt_parts.append("")

        # Add knowledge base guides
        prompt_parts.append("## Knowledge Base Deployment Guides\n")
        prompt_parts.append("*Use these guides for accurate, platform-specific instructions:*\n")

        for platform, guide_info in guides.items():
            entry = guide_info.get("knowledge_entry")
            if entry:
                # Include the full guide content
                prompt_parts.append(f"### {entry.title}")
                prompt_parts.append(f"*Platform: {entry.platform}*\n")

                # Include content (truncated if very long)
                content = entry.content
                if len(content) > 2000:
                    content = content[:2000] + "\n...[truncated]"
                prompt_parts.append(content)

                # Include commands
                if entry.commands:
                    prompt_parts.append("\n**Key Commands:**")
                    for cmd in entry.commands[:8]:
                        prompt_parts.append(f"```\n{cmd}\n```")

                prompt_parts.append("")

        # Add context if available
        if context:
            if context.get("description"):
                prompt_parts.append(f"## Project Description\n{context['description']}\n")
            if context.get("technical"):
                prompt_parts.append(f"## Technical Requirements\n{context['technical']}\n")

        prompt_parts.append("""
## Instructions
Based on the build output and knowledge base guides above, create comprehensive
deployment instructions. Be specific with commands, account requirements, and
common pitfalls. Include estimated review times where applicable.
""")

        return "\n".join(prompt_parts)


# Singleton instance
_launch: Optional[LaunchAgent] = None


def get_launch(router=None, memory=None) -> Optional[LaunchAgent]:
    """Get or create the global Launch agent instance.

    Note: Returns None if router/memory not provided and no existing instance.
    """
    global _launch
    if _launch is None and router is not None:
        _launch = LaunchAgent(router=router, memory=memory)
    return _launch
