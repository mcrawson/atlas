"""
Project Type Classification

When a user wants to BUILD something (IdeaType.PRODUCT), this module
determines WHAT they're building - a mobile app, website, CLI tool, etc.

This affects:
- How Sketch writes specifications
- How Tinker builds the project
- How Oracle verifies the output
- What templates and patterns to use
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ProjectCategory(Enum):
    """High-level project categories."""
    APP = "app"                 # Mobile or desktop application
    WEB = "web"                 # Website or web application
    API = "api"                 # Backend API or service
    CLI = "cli"                 # Command-line tool
    LIBRARY = "library"         # Reusable library or package
    SCRIPT = "script"           # Automation script or one-off tool
    DOCUMENT = "document"       # Book, documentation, or written content
    PHYSICAL = "physical"       # Physical products (planners, printed materials)
    OTHER = "other"             # Doesn't fit other categories


class ProjectType(Enum):
    """Specific project types within each category."""
    # App category
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    MOBILE_CROSS_PLATFORM = "mobile_cross_platform"
    DESKTOP_ELECTRON = "desktop_electron"
    DESKTOP_NATIVE = "desktop_native"

    # Web category
    WEB_STATIC = "web_static"           # Static HTML/CSS/JS site
    WEB_SPA = "web_spa"                 # Single-page app (React, Vue, etc.)
    WEB_FULLSTACK = "web_fullstack"     # Full-stack with backend
    WEB_LANDING = "web_landing"         # Landing page / marketing site
    WEB_BLOG = "web_blog"               # Blog or content site
    WEB_ECOMMERCE = "web_ecommerce"     # E-commerce site
    WEB_DASHBOARD = "web_dashboard"     # Admin dashboard / internal tool

    # API category
    API_REST = "api_rest"
    API_GRAPHQL = "api_graphql"
    API_WEBSOCKET = "api_websocket"
    API_MICROSERVICE = "api_microservice"

    # CLI category
    CLI_TOOL = "cli_tool"
    CLI_INTERACTIVE = "cli_interactive"

    # Library category
    LIBRARY_NPM = "library_npm"
    LIBRARY_PYPI = "library_pypi"
    LIBRARY_OTHER = "library_other"

    # Script category
    SCRIPT_AUTOMATION = "script_automation"
    SCRIPT_DATA = "script_data"
    SCRIPT_DEVOPS = "script_devops"

    # Document category
    DOC_BOOK = "doc_book"
    DOC_TECHNICAL = "doc_technical"
    DOC_PROPOSAL = "doc_proposal"
    DOC_REPORT = "doc_report"
    DOC_GUIDE = "doc_guide"

    # Physical products category
    PHYSICAL_PLANNER = "physical_planner"
    PHYSICAL_JOURNAL = "physical_journal"
    PHYSICAL_WORKBOOK = "physical_workbook"
    PHYSICAL_CARDS = "physical_cards"
    PHYSICAL_PRINTABLE = "physical_printable"

    # Other
    OTHER = "other"


@dataclass
class ProjectTypeConfig:
    """Configuration for a specific project type."""
    type: ProjectType
    category: ProjectCategory
    name: str
    description: str
    icon: str

    # Technology suggestions
    suggested_stack: list[str] = field(default_factory=list)

    # Build configuration
    file_structure: str = ""  # Template name or description
    build_approach: str = ""  # How Tinker should approach building
    verification_focus: list[str] = field(default_factory=list)  # What Oracle checks

    # Conversation hints
    key_questions: list[str] = field(default_factory=list)


# Detection patterns for project types
PROJECT_TYPE_PATTERNS = {
    # Mobile Apps
    ProjectType.MOBILE_IOS: {
        "keywords": [r'\b(ios|iphone|ipad|swift|swiftui|xcode|apple)\b'],
        "phrases": [r'ios app', r'iphone app', r'ipad app', r'apple (app|store)'],
    },
    ProjectType.MOBILE_ANDROID: {
        "keywords": [r'\b(android|kotlin|java android|play store|google play)\b'],
        "phrases": [r'android app', r'google play'],
    },
    ProjectType.MOBILE_CROSS_PLATFORM: {
        "keywords": [r'\b(react native|flutter|expo|ionic|xamarin|cross.?platform)\b'],
        "phrases": [r'(ios|iphone) and (android)', r'both (platforms|ios and android)', r'cross.?platform'],
    },

    # Web
    ProjectType.WEB_STATIC: {
        "keywords": [r'\b(static (site|website)|html|css|simple (site|website|page))\b'],
        "phrases": [r'simple (website|site|page)', r'static (site|website)', r'just (html|a website)'],
    },
    ProjectType.WEB_SPA: {
        "keywords": [r'\b(spa|single.?page|react|vue|angular|svelte|next\.?js|nuxt|widget|component|frontend|web app)\b'],
        "phrases": [r'react app', r'vue app', r'angular app', r'single.?page', r'weather widget', r'(ui|web) component', r'frontend (app|project)', r'interactive widget'],
    },
    ProjectType.WEB_FULLSTACK: {
        "keywords": [r'\b(full.?stack|backend|database|node|django|rails|laravel|auth)\b'],
        "phrases": [r'full.?stack', r'with (a )?backend', r'needs? (a )?database', r'user (accounts?|auth)'],
    },
    ProjectType.WEB_LANDING: {
        "keywords": [r'\b(landing page|marketing|waitlist|signup|launch)\b'],
        "phrases": [r'landing page', r'marketing (site|page)', r'coming soon', r'waitlist'],
    },
    ProjectType.WEB_BLOG: {
        "keywords": [r'\b(blog|cms|content|posts?|articles?|wordpress|ghost)\b'],
        "phrases": [r'blog', r'write (posts?|articles?)', r'content (site|management)'],
    },
    ProjectType.WEB_ECOMMERCE: {
        "keywords": [r'\b(ecommerce|e-commerce|shop|store|cart|checkout|stripe|payments?)\b'],
        "phrases": [r'online (store|shop)', r'sell (products?|items?)', r'shopping cart'],
    },
    ProjectType.WEB_DASHBOARD: {
        "keywords": [r'\b(dashboard|admin|panel|internal tool|backoffice)\b'],
        "phrases": [r'admin (panel|dashboard)', r'internal (tool|dashboard)', r'management (dashboard|system)'],
    },

    # API
    ProjectType.API_REST: {
        "keywords": [r'\b(api|rest|restful|endpoints?|backend only|json api|weather api|data api|service)\b'],
        "phrases": [r'rest api', r'api (server|backend|only)', r'(build|create) an api', r'uses? (a |an )?(public |external )?api', r'fetch(es)? data', r'weather (api|service|data)', r'(get|fetch) (weather|data|forecast)'],
    },
    ProjectType.API_GRAPHQL: {
        "keywords": [r'\b(graphql|apollo|hasura)\b'],
        "phrases": [r'graphql (api|server)'],
    },
    ProjectType.API_MICROSERVICE: {
        "keywords": [r'\b(microservice|micro.?service|serverless|lambda|cloud function)\b'],
        "phrases": [r'micro.?service', r'serverless', r'cloud function'],
    },

    # CLI
    ProjectType.CLI_TOOL: {
        "keywords": [r'\b(cli|command.?line|terminal|bash|shell|script tool)\b'],
        "phrases": [r'(cli|command.?line) (tool|app)', r'terminal (app|tool)', r'run from (terminal|command.?line)'],
    },
    ProjectType.CLI_INTERACTIVE: {
        "keywords": [r'\b(interactive cli|tui|text ui|ncurses|inquirer)\b'],
        "phrases": [r'interactive (cli|terminal|command.?line)', r'text (ui|interface)'],
    },

    # Library
    ProjectType.LIBRARY_NPM: {
        "keywords": [r'\b(npm|package|module|javascript library|typescript library)\b'],
        "phrases": [r'npm (package|module)', r'(javascript|typescript|js|ts) (library|package)'],
    },
    ProjectType.LIBRARY_PYPI: {
        "keywords": [r'\b(pip|pypi|python (library|package|module))\b'],
        "phrases": [r'python (library|package|module)', r'pip (package|install)'],
    },

    # Script
    ProjectType.SCRIPT_AUTOMATION: {
        "keywords": [r'\b(automate|automation|script|cron|scheduled|batch)\b'],
        "phrases": [r'automate (this|the|my)', r'automation script', r'scheduled (task|job)'],
    },
    ProjectType.SCRIPT_DATA: {
        "keywords": [r'\b(data|etl|scrape|scraping|parse|transform|csv|json|excel)\b'],
        "phrases": [r'(scrape|extract) data', r'process (csv|json|data)', r'data (pipeline|processing)'],
    },

    # Document
    ProjectType.DOC_BOOK: {
        "keywords": [r'\b(book|ebook|novel|chapters?|manuscript)\b'],
        "phrases": [r'write a book', r'(my|a) book', r'ebook'],
    },
    ProjectType.DOC_TECHNICAL: {
        "keywords": [r'\b(documentation|docs|readme|technical writing|api docs)\b'],
        "phrases": [r'write (documentation|docs)', r'(technical|api) documentation'],
    },
    ProjectType.DOC_GUIDE: {
        "keywords": [r'\b(guide|tutorial|how.?to|walkthrough|instructions)\b'],
        "phrases": [r'(write|create) a guide', r'how.?to (guide|document)', r'step.?by.?step'],
    },

    # Physical Products
    ProjectType.PHYSICAL_PLANNER: {
        "keywords": [r'\b(planner|daily planner|weekly planner|agenda|organizer)\b'],
        "phrases": [r'physical planner', r'planner book', r'printable planner', r'paper planner'],
    },
    ProjectType.PHYSICAL_JOURNAL: {
        "keywords": [r'\b(journal|diary|gratitude journal|bullet journal|bujo)\b'],
        "phrases": [r'physical journal', r'journal book', r'printable journal'],
    },
    ProjectType.PHYSICAL_WORKBOOK: {
        "keywords": [r'\b(workbook|worksheet|activity book|exercise book)\b'],
        "phrases": [r'physical workbook', r'printable workbook', r'worksheet book'],
    },
    ProjectType.PHYSICAL_CARDS: {
        "keywords": [r'\b(cards|flashcards|playing cards|game cards|greeting cards)\b'],
        "phrases": [r'physical cards', r'printable cards', r'card deck'],
    },
    ProjectType.PHYSICAL_PRINTABLE: {
        "keywords": [r'\b(printable|print.?ready|pdf template|downloadable)\b'],
        "phrases": [r'printable (template|pdf)', r'print.?ready', r'downloadable (pdf|template)'],
    },
}


# Full configurations for each project type
PROJECT_CONFIGS: dict[ProjectType, ProjectTypeConfig] = {
    # Mobile Apps
    ProjectType.MOBILE_IOS: ProjectTypeConfig(
        type=ProjectType.MOBILE_IOS,
        category=ProjectCategory.APP,
        name="iOS App",
        description="Native iPhone/iPad application",
        icon="",
        suggested_stack=["Swift", "SwiftUI", "UIKit", "Xcode"],
        build_approach="Create Swift/SwiftUI code with proper iOS patterns (MVVM, Coordinator)",
        verification_focus=["iOS guidelines compliance", "memory management", "accessibility"],
        key_questions=["iPhone only or iPad too?", "iOS version target?", "Need offline support?"],
    ),
    ProjectType.MOBILE_ANDROID: ProjectTypeConfig(
        type=ProjectType.MOBILE_ANDROID,
        category=ProjectCategory.APP,
        name="Android App",
        description="Native Android application",
        icon="",
        suggested_stack=["Kotlin", "Jetpack Compose", "Android Studio"],
        build_approach="Create Kotlin code with modern Android architecture (MVVM, Compose)",
        verification_focus=["Material Design compliance", "lifecycle handling", "permissions"],
        key_questions=["Minimum Android version?", "Tablet support?", "Need background services?"],
    ),
    ProjectType.MOBILE_CROSS_PLATFORM: ProjectTypeConfig(
        type=ProjectType.MOBILE_CROSS_PLATFORM,
        category=ProjectCategory.APP,
        name="Cross-Platform App",
        description="App for both iOS and Android",
        icon="",
        suggested_stack=["React Native", "Flutter", "Expo"],
        build_approach="Create cross-platform code with shared business logic",
        verification_focus=["platform parity", "performance", "native feel"],
        key_questions=["React Native or Flutter preference?", "Need native modules?", "Expo or bare?"],
    ),

    # Web
    ProjectType.WEB_STATIC: ProjectTypeConfig(
        type=ProjectType.WEB_STATIC,
        category=ProjectCategory.WEB,
        name="Static Website",
        description="Simple HTML/CSS/JS website",
        icon="",
        suggested_stack=["HTML", "CSS", "JavaScript", "Tailwind"],
        build_approach="Create clean, semantic HTML with modern CSS",
        verification_focus=["accessibility", "SEO", "performance", "responsive design"],
        key_questions=["How many pages?", "Need a contact form?", "Hosting preference?"],
    ),
    ProjectType.WEB_SPA: ProjectTypeConfig(
        type=ProjectType.WEB_SPA,
        category=ProjectCategory.WEB,
        name="Single-Page App",
        description="Dynamic web application (React, Vue, etc.)",
        icon="",
        suggested_stack=["React", "TypeScript", "Vite", "Tailwind"],
        build_approach="Create component-based SPA with proper state management",
        verification_focus=["component architecture", "state management", "routing", "performance"],
        key_questions=["React, Vue, or other?", "Need routing?", "State management needs?"],
    ),
    ProjectType.WEB_FULLSTACK: ProjectTypeConfig(
        type=ProjectType.WEB_FULLSTACK,
        category=ProjectCategory.WEB,
        name="Full-Stack Web App",
        description="Web app with frontend and backend",
        icon="",
        suggested_stack=["Next.js", "TypeScript", "PostgreSQL", "Prisma"],
        build_approach="Create full-stack app with API routes, database, and authentication",
        verification_focus=["security", "API design", "database schema", "auth flow"],
        key_questions=["User authentication needed?", "What data needs storing?", "Real-time features?"],
    ),
    ProjectType.WEB_LANDING: ProjectTypeConfig(
        type=ProjectType.WEB_LANDING,
        category=ProjectCategory.WEB,
        name="Landing Page",
        description="Marketing or launch page",
        icon="",
        suggested_stack=["HTML", "Tailwind", "JavaScript"],
        build_approach="Create conversion-focused landing page with clear CTA",
        verification_focus=["conversion elements", "load speed", "mobile-first", "SEO"],
        key_questions=["What's the main CTA?", "Need email capture?", "Analytics needed?"],
    ),
    ProjectType.WEB_DASHBOARD: ProjectTypeConfig(
        type=ProjectType.WEB_DASHBOARD,
        category=ProjectCategory.WEB,
        name="Dashboard / Admin Panel",
        description="Internal tool or admin interface",
        icon="",
        suggested_stack=["React", "TypeScript", "shadcn/ui", "TanStack Table"],
        build_approach="Create data-rich dashboard with tables, charts, and forms",
        verification_focus=["data display", "filtering/sorting", "user permissions", "responsiveness"],
        key_questions=["What data to display?", "Role-based access?", "Export features?"],
    ),

    # API
    ProjectType.API_REST: ProjectTypeConfig(
        type=ProjectType.API_REST,
        category=ProjectCategory.API,
        name="REST API",
        description="RESTful backend API",
        icon="",
        suggested_stack=["Python/FastAPI", "Node/Express", "PostgreSQL"],
        build_approach="Create RESTful API with proper resource design and documentation",
        verification_focus=["REST conventions", "error handling", "validation", "security"],
        key_questions=["What resources/endpoints?", "Authentication method?", "Database choice?"],
    ),
    ProjectType.API_GRAPHQL: ProjectTypeConfig(
        type=ProjectType.API_GRAPHQL,
        category=ProjectCategory.API,
        name="GraphQL API",
        description="GraphQL backend API",
        icon="",
        suggested_stack=["Node.js", "Apollo Server", "PostgreSQL"],
        build_approach="Create GraphQL schema with resolvers and proper type system",
        verification_focus=["schema design", "N+1 queries", "authorization", "caching"],
        key_questions=["What types/queries needed?", "Real-time subscriptions?", "Existing data sources?"],
    ),

    # CLI
    ProjectType.CLI_TOOL: ProjectTypeConfig(
        type=ProjectType.CLI_TOOL,
        category=ProjectCategory.CLI,
        name="CLI Tool",
        description="Command-line application",
        icon="",
        suggested_stack=["Python/Click", "Node/Commander", "Go/Cobra"],
        build_approach="Create CLI with clear commands, flags, and helpful output",
        verification_focus=["argument parsing", "error messages", "help text", "exit codes"],
        key_questions=["What commands needed?", "Interactive prompts?", "Config file support?"],
    ),

    # Library
    ProjectType.LIBRARY_NPM: ProjectTypeConfig(
        type=ProjectType.LIBRARY_NPM,
        category=ProjectCategory.LIBRARY,
        name="NPM Package",
        description="JavaScript/TypeScript library",
        icon="",
        suggested_stack=["TypeScript", "Vitest", "tsup"],
        build_approach="Create well-typed, tested, and documented npm package",
        verification_focus=["type definitions", "test coverage", "bundle size", "API design"],
        key_questions=["What problem does it solve?", "Browser, Node, or both?", "Dependencies?"],
    ),
    ProjectType.LIBRARY_PYPI: ProjectTypeConfig(
        type=ProjectType.LIBRARY_PYPI,
        category=ProjectCategory.LIBRARY,
        name="Python Package",
        description="Python library for PyPI",
        icon="",
        suggested_stack=["Python", "pytest", "poetry"],
        build_approach="Create well-documented Python package with type hints",
        verification_focus=["type hints", "docstrings", "test coverage", "API design"],
        key_questions=["Python version support?", "Async support needed?", "CLI included?"],
    ),

    # Script
    ProjectType.SCRIPT_AUTOMATION: ProjectTypeConfig(
        type=ProjectType.SCRIPT_AUTOMATION,
        category=ProjectCategory.SCRIPT,
        name="Automation Script",
        description="Script to automate a task",
        icon="",
        suggested_stack=["Python", "Bash"],
        build_approach="Create focused script with error handling and logging",
        verification_focus=["error handling", "idempotency", "logging", "documentation"],
        key_questions=["What does it automate?", "Scheduled or manual?", "Error handling needs?"],
    ),
    ProjectType.SCRIPT_DATA: ProjectTypeConfig(
        type=ProjectType.SCRIPT_DATA,
        category=ProjectCategory.SCRIPT,
        name="Data Script",
        description="Data processing or ETL script",
        icon="",
        suggested_stack=["Python", "pandas", "requests"],
        build_approach="Create data pipeline with clear input/output and error handling",
        verification_focus=["data validation", "error handling", "performance", "logging"],
        key_questions=["Data source format?", "Output format?", "Volume/frequency?"],
    ),

    # Documents
    ProjectType.DOC_BOOK: ProjectTypeConfig(
        type=ProjectType.DOC_BOOK,
        category=ProjectCategory.DOCUMENT,
        name="Book",
        description="Book or long-form written content",
        icon="",
        suggested_stack=["Markdown", "mdBook", "Pandoc"],
        build_approach="Create structured chapters with consistent style and flow",
        verification_focus=["structure", "consistency", "flow", "completeness"],
        key_questions=["Genre/type?", "Target length?", "Audience?"],
    ),
    ProjectType.DOC_TECHNICAL: ProjectTypeConfig(
        type=ProjectType.DOC_TECHNICAL,
        category=ProjectCategory.DOCUMENT,
        name="Technical Documentation",
        description="API docs, README, or technical writing",
        icon="",
        suggested_stack=["Markdown", "Docusaurus", "MkDocs"],
        build_approach="Create clear, structured documentation with examples",
        verification_focus=["accuracy", "completeness", "examples", "clarity"],
        key_questions=["What are you documenting?", "Audience technical level?", "Include code examples?"],
    ),
    ProjectType.DOC_GUIDE: ProjectTypeConfig(
        type=ProjectType.DOC_GUIDE,
        category=ProjectCategory.DOCUMENT,
        name="Guide / Tutorial",
        description="How-to guide or tutorial",
        icon="",
        suggested_stack=["Markdown"],
        build_approach="Create step-by-step guide with clear instructions",
        verification_focus=["step accuracy", "completeness", "clarity", "prerequisites"],
        key_questions=["Beginner or advanced?", "Include screenshots?", "Code examples?"],
    ),

    # Physical Products
    ProjectType.PHYSICAL_PLANNER: ProjectTypeConfig(
        type=ProjectType.PHYSICAL_PLANNER,
        category=ProjectCategory.PHYSICAL,
        name="Physical Planner",
        description="Printable planner book or pages",
        icon="📅",
        suggested_stack=["HTML", "CSS", "PDF"],
        build_approach="Create print-ready HTML/CSS templates that can be exported to PDF. Include all page layouts with proper print margins (0.5 inch), page sizes (letter/A4/A5), and bleed areas.",
        verification_focus=["print margins", "page dimensions", "readability", "completeness"],
        key_questions=["Page size (letter, A4, A5)?", "Binding side (left, top)?", "Color or black & white?", "How many pages/sections?"],
    ),
    ProjectType.PHYSICAL_JOURNAL: ProjectTypeConfig(
        type=ProjectType.PHYSICAL_JOURNAL,
        category=ProjectCategory.PHYSICAL,
        name="Physical Journal",
        description="Printable journal or diary",
        icon="📓",
        suggested_stack=["HTML", "CSS", "PDF"],
        build_approach="Create print-ready journal templates with prompts, lined areas, and decorative elements. Include cover design.",
        verification_focus=["print margins", "line spacing", "prompt clarity", "aesthetic appeal"],
        key_questions=["Guided prompts or blank?", "Daily, weekly, or undated?", "Include cover design?"],
    ),
    ProjectType.PHYSICAL_WORKBOOK: ProjectTypeConfig(
        type=ProjectType.PHYSICAL_WORKBOOK,
        category=ProjectCategory.PHYSICAL,
        name="Physical Workbook",
        description="Printable workbook with exercises",
        icon="📝",
        suggested_stack=["HTML", "CSS", "PDF"],
        build_approach="Create print-ready workbook pages with exercises, fill-in areas, and answer sections.",
        verification_focus=["exercise clarity", "answer space", "progression", "instructions"],
        key_questions=["Subject/topic?", "Age group?", "Include answer key?"],
    ),
    ProjectType.PHYSICAL_CARDS: ProjectTypeConfig(
        type=ProjectType.PHYSICAL_CARDS,
        category=ProjectCategory.PHYSICAL,
        name="Physical Cards",
        description="Printable cards (flashcards, game cards, etc.)",
        icon="🃏",
        suggested_stack=["HTML", "CSS", "PDF"],
        build_approach="Create print-ready card layouts with proper cut lines, front/back alignment, and card dimensions.",
        verification_focus=["card dimensions", "cut lines", "front/back alignment", "readability"],
        key_questions=["Card size?", "Number of cards?", "Double-sided?", "Cut lines needed?"],
    ),
    ProjectType.PHYSICAL_PRINTABLE: ProjectTypeConfig(
        type=ProjectType.PHYSICAL_PRINTABLE,
        category=ProjectCategory.PHYSICAL,
        name="Printable Template",
        description="General printable PDF template",
        icon="🖨️",
        suggested_stack=["HTML", "CSS", "PDF"],
        build_approach="Create print-ready template with proper margins and dimensions for the target use case.",
        verification_focus=["print quality", "margins", "usability", "completeness"],
        key_questions=["What will it be used for?", "Page size?", "Single or multi-page?"],
    ),
}


class ProjectTypeDetector:
    """Detects specific project type from conversation."""

    def __init__(self):
        self.patterns = PROJECT_TYPE_PATTERNS
        self.configs = PROJECT_CONFIGS

    def detect(self, text: str) -> tuple[ProjectType, ProjectCategory, float]:
        """
        Detect project type from text.

        Returns:
            Tuple of (ProjectType, ProjectCategory, confidence 0-1)
        """
        text_lower = text.lower()
        scores: dict[ProjectType, float] = {}

        for project_type, patterns in self.patterns.items():
            score = 0.0

            # Check keywords
            for pattern in patterns.get("keywords", []):
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                score += len(matches) * 1.0

            # Check phrases (higher weight)
            for pattern in patterns.get("phrases", []):
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                score += len(matches) * 2.0

            if score > 0:
                scores[project_type] = score

        if not scores:
            return ProjectType.OTHER, ProjectCategory.OTHER, 0.0

        # Get best match
        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]

        # Calculate confidence
        total_score = sum(scores.values())
        confidence = min(max_score / max(total_score, 1), 1.0)
        if max_score >= 3.0:
            confidence = max(confidence, 0.7)

        # Get category from config
        config = self.configs.get(best_type)
        category = config.category if config else ProjectCategory.OTHER

        return best_type, category, confidence

    def get_config(self, project_type: ProjectType) -> Optional[ProjectTypeConfig]:
        """Get configuration for a project type."""
        return self.configs.get(project_type)

    def get_category_options(self, category: ProjectCategory) -> list[ProjectTypeConfig]:
        """Get all project types in a category."""
        return [
            config for config in self.configs.values()
            if config.category == category
        ]

    def get_all_categories(self) -> list[dict]:
        """Get all categories with their options."""
        categories = {}
        for config in self.configs.values():
            cat = config.category
            if cat not in categories:
                categories[cat] = {
                    "category": cat,
                    "name": cat.value.title(),
                    "types": [],
                }
            categories[cat]["types"].append({
                "type": config.type.value,
                "name": config.name,
                "icon": config.icon,
                "description": config.description,
            })
        return list(categories.values())

    def suggest_type(self, text: str) -> dict:
        """
        Suggest project type with explanation.

        Returns dict with type, category, confidence, and options.
        """
        project_type, category, confidence = self.detect(text)

        if project_type == ProjectType.OTHER or confidence < 0.4:
            return {
                "detected": False,
                "confidence": confidence,
                "message": "I'm not sure what type of project this is. What are you building?",
                "categories": self.get_all_categories(),
            }

        config = self.get_config(project_type)
        return {
            "detected": True,
            "type": project_type.value,
            "category": category.value,
            "name": config.name,
            "icon": config.icon,
            "description": config.description,
            "confidence": confidence,
            "suggested_stack": config.suggested_stack,
            "key_questions": config.key_questions,
            "message": f"This sounds like a {config.name}. Is that right?",
            "alternatives": [
                {"type": c.type.value, "name": c.name, "icon": c.icon}
                for c in self.get_category_options(category)
                if c.type != project_type
            ][:3],
        }
