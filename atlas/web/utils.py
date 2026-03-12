"""Utility functions for ATLAS Web."""

import os
import json
import zipfile
import subprocess
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


# Default monthly token budgets per provider (configurable)
DEFAULT_BUDGETS = {
    "openai": 1_000_000,      # 1M tokens
    "anthropic": 1_000_000,   # 1M tokens
    "gemini": 2_000_000,      # 2M tokens (often more generous)
    "ollama": float('inf'),   # Unlimited (local)
    "total": 5_000_000,       # 5M total across all
}

# Average token usage per agent (based on typical outputs)
AGENT_TOKEN_ESTIMATES = {
    "architect": {
        "base_output": 800,        # Base output tokens
        "per_feature": 100,        # Additional per feature requested
        "input_multiplier": 0.3,   # Output is ~30% of input context
    },
    "mason": {
        "base_output": 1500,       # Code generation is verbose
        "per_feature": 300,        # More code per feature
        "input_multiplier": 0.5,   # Output is ~50% of input
    },
    "oracle": {
        "base_output": 600,        # Verification is shorter
        "per_feature": 80,
        "input_multiplier": 0.25,  # Output is ~25% of input
    },
}


# Token pricing per 1M tokens (as of 2024)
TOKEN_PRICING = {
    "openai": {
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
    "anthropic": {
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    },
    "gemini": {
        "gemini-pro": {"input": 0.50, "output": 1.50},
        "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
        "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
    },
    "ollama": {
        "default": {"input": 0.00, "output": 0.00},  # Local, free
    },
    "default": {"input": 5.00, "output": 15.00},  # Fallback estimate
}


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "default",
    model: str = "default"
) -> dict:
    """Estimate cost based on token usage.

    Args:
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        provider: Provider name (openai, anthropic, gemini, ollama)
        model: Model name

    Returns:
        Dict with cost breakdown
    """
    # Get pricing for provider/model
    provider_pricing = TOKEN_PRICING.get(provider.lower(), {})

    # Try exact model match, then partial match, then default
    pricing = None
    model_lower = model.lower() if model else ""

    for model_key, prices in provider_pricing.items():
        if model_key in model_lower or model_lower in model_key:
            pricing = prices
            break

    if not pricing:
        pricing = provider_pricing.get("default", TOKEN_PRICING["default"])

    # Calculate costs (pricing is per 1M tokens)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
        "formatted": f"${total_cost:.4f}",
        "provider": provider,
        "model": model,
        "is_estimate": True,
    }


def calculate_project_cost(metadata: dict) -> dict:
    """Calculate total project cost from metadata.

    Args:
        metadata: Project metadata with tokens info

    Returns:
        Cost breakdown by agent and total
    """
    tokens = metadata.get("tokens", {})
    by_agent = tokens.get("by_agent", {})

    costs = {
        "by_agent": {},
        "total": 0.0,
        "formatted": "$0.0000",
    }

    # Get agent outputs for detailed token info
    plan = metadata.get("plan", {}).get("agent_output", {})
    build = metadata.get("build", {}).get("agent_output", {})
    verification = metadata.get("verification", {}).get("agent_output", {})

    agent_outputs = {
        "architect": plan,
        "mason": build,
        "oracle": verification,
    }

    total_cost = 0.0

    for agent_name, output in agent_outputs.items():
        if output:
            cost = estimate_cost(
                output.get("prompt_tokens", 0),
                output.get("completion_tokens", 0),
                output.get("provider", "default"),
            )
            costs["by_agent"][agent_name] = cost
            total_cost += cost["total_cost"]

    costs["total"] = round(total_cost, 6)
    costs["formatted"] = f"${total_cost:.4f}"

    return costs


# Project Templates
PROJECT_TEMPLATES = {
    "api": {
        "name": "REST API",
        "icon": "🔌",
        "description": "Build a REST API with endpoints, authentication, and database",
        "defaults": {
            "problem": "Need a backend API to serve data to clients",
            "features": [
                "CRUD endpoints for resources",
                "Authentication (JWT or API keys)",
                "Input validation",
                "Error handling",
                "Database integration",
            ],
            "technical": "Python FastAPI, SQLite/PostgreSQL, Pydantic models",
        }
    },
    "cli": {
        "name": "CLI Tool",
        "icon": "⌨️",
        "description": "Build a command-line tool with arguments and subcommands",
        "defaults": {
            "problem": "Need a terminal tool for automation or workflow",
            "features": [
                "Argument parsing with help text",
                "Subcommands for different actions",
                "Configuration file support",
                "Progress indicators",
                "Colored output",
            ],
            "technical": "Python with Click or Typer, Rich for output",
        }
    },
    "webapp": {
        "name": "Web Application",
        "icon": "🌐",
        "description": "Build a web application with frontend and backend",
        "defaults": {
            "problem": "Need an interactive web application",
            "features": [
                "User authentication",
                "Responsive UI",
                "Database storage",
                "Form handling",
                "API integration",
            ],
            "technical": "Python FastAPI backend, HTMX + Jinja2 frontend, SQLite",
        }
    },
    "data": {
        "name": "Data Pipeline",
        "icon": "📊",
        "description": "Build a data processing pipeline with ETL capabilities",
        "defaults": {
            "problem": "Need to process, transform, and analyze data",
            "features": [
                "Data ingestion from multiple sources",
                "Data cleaning and transformation",
                "Data validation",
                "Output to various formats",
                "Scheduling and automation",
            ],
            "technical": "Python with Pandas, data validation with Pydantic",
        }
    },
    "automation": {
        "name": "Automation Script",
        "icon": "🤖",
        "description": "Build a script to automate repetitive tasks",
        "defaults": {
            "problem": "Need to automate a manual workflow",
            "features": [
                "Task scheduling",
                "File operations",
                "API integrations",
                "Error handling and retries",
                "Logging and notifications",
            ],
            "technical": "Python with standard library, requests for APIs",
        }
    },
    "library": {
        "name": "Python Library",
        "icon": "📚",
        "description": "Build a reusable Python library/package",
        "defaults": {
            "problem": "Need a reusable module for common functionality",
            "features": [
                "Clean public API",
                "Type hints throughout",
                "Comprehensive docstrings",
                "Unit tests",
                "Package configuration (pyproject.toml)",
            ],
            "technical": "Python 3.10+, pytest for testing, setuptools",
        }
    },
    # ============== ADDITIONAL TEMPLATES ==============
    "portfolio": {
        "name": "Portfolio Website",
        "icon": "💼",
        "description": "Modern portfolio website to showcase projects and services",
        "defaults": {
            "problem": "Need a professional website to showcase work and attract clients",
            "features": [
                "Dark mode design with clean aesthetic",
                "Responsive mobile-first layout",
                "Projects showcase with images",
                "Services/skills section",
                "About me page",
                "Contact form integration",
                "SEO-ready with meta tags",
            ],
            "technical": "React 19 + Vite, React Router, CSS Variables, Formspree for contact",
        },
    },
    "landing": {
        "name": "Landing Page",
        "icon": "🚀",
        "description": "High-converting landing page for products or services",
        "defaults": {
            "problem": "Need a landing page to convert visitors into customers",
            "features": [
                "Hero section with CTA",
                "Features/benefits showcase",
                "Social proof/testimonials",
                "Pricing section",
                "FAQ accordion",
                "Newsletter signup",
                "Mobile responsive",
            ],
            "technical": "HTML5, CSS3, vanilla JavaScript, Tailwind CSS",
        },
    },
    "dashboard": {
        "name": "Admin Dashboard",
        "icon": "📊",
        "description": "Admin dashboard with charts, tables, and data management",
        "defaults": {
            "problem": "Need an admin interface to manage data and view analytics",
            "features": [
                "Sidebar navigation",
                "Data tables with sorting/filtering",
                "Charts and visualizations",
                "User management",
                "Settings page",
                "Dark/light mode toggle",
                "Responsive design",
            ],
            "technical": "React, Chart.js or Recharts, Tailwind CSS, data grid component",
        },
    },
    "ecommerce": {
        "name": "E-commerce Store",
        "icon": "🛍️",
        "description": "Online store with product catalog, cart, and checkout",
        "defaults": {
            "problem": "Need an online store to sell products",
            "features": [
                "Product catalog with categories",
                "Product detail pages",
                "Shopping cart",
                "Checkout flow",
                "User accounts",
                "Order history",
                "Search and filters",
            ],
            "technical": "React/Next.js, Stripe for payments, database for products",
        },
    },
    "mobile-app": {
        "name": "Mobile App",
        "icon": "📱",
        "description": "Cross-platform mobile app for iOS and Android",
        "defaults": {
            "problem": "Need a mobile app for iOS and Android",
            "features": [
                "Cross-platform (iOS + Android)",
                "Native-like UI/UX",
                "Push notifications",
                "Offline support",
                "User authentication",
                "API integration",
            ],
            "technical": "React Native or Flutter, Firebase for backend services",
        },
    },
    "chrome-extension": {
        "name": "Chrome Extension",
        "icon": "🧩",
        "description": "Browser extension with popup UI and background scripts",
        "defaults": {
            "problem": "Need a browser extension to enhance web browsing",
            "features": [
                "Popup UI",
                "Background service worker",
                "Content scripts for page interaction",
                "Storage for settings",
                "Keyboard shortcuts",
                "Context menu integration",
            ],
            "technical": "Manifest V3, JavaScript/TypeScript, Chrome APIs",
        },
    },
    "slack-bot": {
        "name": "Slack Bot",
        "icon": "💬",
        "description": "Slack bot with commands, events, and interactive messages",
        "defaults": {
            "problem": "Need a Slack bot for team automation",
            "features": [
                "Slash commands",
                "Event handling (messages, reactions)",
                "Interactive buttons and menus",
                "Scheduled messages",
                "User mentions and DMs",
                "Integration with external APIs",
            ],
            "technical": "Node.js with Bolt.js, or Python with slack-bolt",
        },
    },
    "discord-bot": {
        "name": "Discord Bot",
        "icon": "🎮",
        "description": "Discord bot with commands, events, and server management",
        "defaults": {
            "problem": "Need a Discord bot for server management or community",
            "features": [
                "Slash commands",
                "Message reactions and events",
                "Role management",
                "Welcome messages",
                "Moderation tools",
                "Music/audio playback",
            ],
            "technical": "Node.js with discord.js, or Python with discord.py",
        },
    },
    "saas": {
        "name": "SaaS Starter",
        "icon": "☁️",
        "description": "SaaS application with auth, billing, and multi-tenancy",
        "defaults": {
            "problem": "Need a SaaS product with subscriptions and user management",
            "features": [
                "User authentication (OAuth, magic links)",
                "Subscription billing (Stripe)",
                "Team/organization support",
                "Usage limits and quotas",
                "Admin dashboard",
                "API for integrations",
                "Onboarding flow",
            ],
            "technical": "Next.js, Prisma, PostgreSQL, Stripe, NextAuth.js",
        },
    },
    "blog": {
        "name": "Blog / CMS",
        "icon": "📝",
        "description": "Blog with markdown support, categories, and admin panel",
        "defaults": {
            "problem": "Need a blog or content management system",
            "features": [
                "Markdown/rich text editor",
                "Categories and tags",
                "Comment system",
                "Author profiles",
                "RSS feed",
                "SEO optimization",
                "Admin panel for content",
            ],
            "technical": "Next.js or Astro, MDX for content, Tailwind CSS",
        },
    },
    "npm-package": {
        "name": "npm Package",
        "icon": "📦",
        "description": "Publishable npm package with TypeScript and tests",
        "defaults": {
            "problem": "Need to create a reusable JavaScript/TypeScript package",
            "features": [
                "TypeScript support with type definitions",
                "ESM and CommonJS builds",
                "Unit tests with Jest or Vitest",
                "Documentation with examples",
                "CI/CD for automated publishing",
                "Semantic versioning",
            ],
            "technical": "TypeScript, Rollup or tsup for bundling, Jest/Vitest",
        },
    },
    "alexa-skill": {
        "name": "Alexa Skill",
        "icon": "🔊",
        "description": "Voice-activated Alexa skill with intents and responses",
        "defaults": {
            "problem": "Need a voice assistant skill for Amazon Alexa",
            "features": [
                "Custom intents and slots",
                "Multi-turn conversations",
                "Account linking",
                "Persistent user data",
                "Audio playback",
                "Cards and visual responses",
            ],
            "technical": "Node.js or Python, ASK SDK, AWS Lambda",
        },
    },
    "figma-plugin": {
        "name": "Figma Plugin",
        "icon": "🎯",
        "description": "Figma plugin with custom UI and design manipulation",
        "defaults": {
            "problem": "Need a Figma plugin to extend design workflows",
            "features": [
                "Custom UI panel",
                "Selection manipulation",
                "Style generation",
                "Export functionality",
                "Settings persistence",
                "Keyboard shortcuts",
            ],
            "technical": "TypeScript, Figma Plugin API, Preact or vanilla JS for UI",
        },
    },
}


def get_templates() -> dict:
    """Get available project templates."""
    return PROJECT_TEMPLATES


def write_project_files(
    project_id: int,
    files: dict[str, str],
    base_dir: Optional[str] = None
) -> dict:
    """Write generated files to disk.

    Args:
        project_id: Project ID for folder naming
        files: Dict of filename -> content
        base_dir: Base directory (default: ~/atlas-projects)

    Returns:
        Dict with written files info
    """
    if base_dir is None:
        base_dir = os.path.expanduser("~/atlas-projects")

    project_dir = Path(base_dir) / f"project-{project_id}"
    project_dir.mkdir(parents=True, exist_ok=True)

    written = []
    errors = []

    for filename, content in files.items():
        try:
            file_path = project_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            written.append(str(file_path))
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})

    return {
        "project_dir": str(project_dir),
        "files_written": written,
        "errors": errors,
        "success": len(errors) == 0,
    }


def init_git_repo(project_dir: str, initial_commit: bool = True) -> dict:
    """Initialize a git repository for the project.

    Args:
        project_dir: Project directory path
        initial_commit: Whether to create initial commit

    Returns:
        Dict with git operation results
    """
    results = {
        "initialized": False,
        "committed": False,
        "errors": [],
    }

    try:
        # Check if git is available
        subprocess.run(["git", "--version"], capture_output=True, check=True)

        # Initialize repo
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            capture_output=True,
            check=True
        )
        results["initialized"] = True

        if initial_commit:
            # Add all files
            subprocess.run(
                ["git", "add", "."],
                cwd=project_dir,
                capture_output=True,
                check=True
            )

            # Create initial commit
            subprocess.run(
                ["git", "commit", "-m", "Initial commit from ATLAS"],
                cwd=project_dir,
                capture_output=True,
                check=True
            )
            results["committed"] = True

    except subprocess.CalledProcessError as e:
        results["errors"].append(str(e))
    except FileNotFoundError:
        results["errors"].append("Git not found in PATH")

    return results


def generate_readme(
    project_name: str,
    metadata: dict,
    files: dict[str, str]
) -> str:
    """Generate a comprehensive README for a project.

    Args:
        project_name: Name of the project
        metadata: Project metadata (plan, context, build, etc.)
        files: Dict of filename -> content

    Returns:
        README content as string
    """
    context = metadata.get("context", {})
    plan = metadata.get("plan", {})
    build = metadata.get("build", {})

    # Project description
    description = context.get("description", "") or metadata.get("description", "") or plan.get("overview", "")

    # Problem being solved
    problem = context.get("problem", "")

    # Features
    features = context.get("features", []) or plan.get("features", [])
    features_text = "\n".join(f"- {f}" for f in features) if features else "- Core functionality"

    # Technical requirements
    technical = context.get("technical", "") or plan.get("architecture", "")

    # Detect project type from files
    file_extensions = [f.split(".")[-1].lower() for f in files.keys() if "." in f]
    project_type = _detect_project_type(file_extensions)

    # Generate setup instructions based on project type
    setup_instructions = _get_setup_instructions(project_type, files)

    # Generate deployment instructions
    deployment_guide = _get_deployment_guide(project_type, metadata)

    readme = f"""# {project_name}

{description}

> Generated by ATLAS on {datetime.now().strftime('%Y-%m-%d %H:%M')}

{f"## Problem{chr(10)}{chr(10)}{problem}{chr(10)}" if problem else ""}
## Features

{features_text}

## Project Structure

```
{project_name}/
{chr(10).join("├── " + f for f in sorted(files.keys()))}
```

## Getting Started

### Prerequisites

{setup_instructions.get("prerequisites", "- Review the generated files and ensure you have the necessary tools installed.")}

### Installation

{setup_instructions.get("installation", "1. Download or clone the project files\\n2. Install any dependencies\\n3. Configure as needed")}

### Running the Project

{setup_instructions.get("running", "Review the main files and run according to your platform/framework.")}

## Deployment

{deployment_guide}

{f"## Technical Notes{chr(10)}{chr(10)}{technical}{chr(10)}" if technical else ""}
## Files Overview

| File | Description |
|------|-------------|
{chr(10).join(f"| `{f}` | {_describe_file(f)} |" for f in sorted(files.keys()))}

---

*Built with [ATLAS](https://github.com/anthropics/atlas) - AI-powered project builder*
"""
    return readme


def _detect_project_type(extensions: list[str]) -> str:
    """Detect project type from file extensions."""
    if any(ext in ["swift", "m", "h"] for ext in extensions):
        return "ios"
    elif any(ext in ["kt", "java"] for ext in extensions) and "swift" not in extensions:
        return "android"
    elif any(ext in ["tsx", "jsx"] for ext in extensions):
        return "react"
    elif "vue" in extensions:
        return "vue"
    elif any(ext in ["html", "css"] for ext in extensions):
        return "web"
    elif "py" in extensions:
        return "python"
    elif any(ext in ["js", "ts"] for ext in extensions):
        return "node"
    elif "go" in extensions:
        return "go"
    elif "rs" in extensions:
        return "rust"
    else:
        return "generic"


def _get_setup_instructions(project_type: str, files: dict) -> dict:
    """Get setup instructions based on project type."""
    instructions = {
        "ios": {
            "prerequisites": "- macOS with Xcode installed\\n- Apple Developer account (for deployment)\\n- CocoaPods or Swift Package Manager",
            "installation": "1. Open the `.xcodeproj` or `.xcworkspace` in Xcode\\n2. Install dependencies: `pod install` (if using CocoaPods)\\n3. Select your target device/simulator",
            "running": "1. Press `Cmd + R` in Xcode to build and run\\n2. Or use `xcodebuild` from command line",
        },
        "android": {
            "prerequisites": "- Android Studio installed\\n- JDK 11 or higher\\n- Android SDK",
            "installation": "1. Open the project in Android Studio\\n2. Let Gradle sync dependencies\\n3. Connect a device or start an emulator",
            "running": "1. Click 'Run' in Android Studio\\n2. Or use `./gradlew assembleDebug` from command line",
        },
        "react": {
            "prerequisites": "- Node.js (v16 or higher)\\n- npm or yarn",
            "installation": "```bash\\nnpm install\\n# or\\nyarn install\\n```",
            "running": "```bash\\nnpm start\\n# or\\nyarn start\\n```\\n\\nOpen http://localhost:3000 in your browser.",
        },
        "vue": {
            "prerequisites": "- Node.js (v16 or higher)\\n- npm or yarn",
            "installation": "```bash\\nnpm install\\n```",
            "running": "```bash\\nnpm run dev\\n```\\n\\nOpen http://localhost:5173 in your browser.",
        },
        "web": {
            "prerequisites": "- A modern web browser\\n- (Optional) Local web server",
            "installation": "No installation required for static files.",
            "running": "Open `index.html` in your browser, or serve with:\\n```bash\\npython -m http.server 8000\\n```",
        },
        "python": {
            "prerequisites": "- Python 3.8 or higher\\n- pip",
            "installation": "```bash\\npip install -r requirements.txt\\n# or create a virtual environment first:\\npython -m venv venv\\nsource venv/bin/activate  # On Windows: venv\\\\Scripts\\\\activate\\npip install -r requirements.txt\\n```",
            "running": "```bash\\npython main.py\\n# or\\npython src/main.py\\n```",
        },
        "node": {
            "prerequisites": "- Node.js (v16 or higher)\\n- npm",
            "installation": "```bash\\nnpm install\\n```",
            "running": "```bash\\nnode index.js\\n# or\\nnpm start\\n```",
        },
        "go": {
            "prerequisites": "- Go 1.19 or higher",
            "installation": "```bash\\ngo mod download\\n```",
            "running": "```bash\\ngo run .\\n# or\\ngo build && ./app\\n```",
        },
        "rust": {
            "prerequisites": "- Rust (install via rustup.rs)",
            "installation": "```bash\\ncargo build\\n```",
            "running": "```bash\\ncargo run\\n```",
        },
        "generic": {
            "prerequisites": "- Review the generated files to determine requirements",
            "installation": "1. Review dependencies in the project files\\n2. Install required tools and libraries",
            "running": "Follow the conventions for your language/framework.",
        },
    }
    return instructions.get(project_type, instructions["generic"])


def _get_deployment_guide(project_type: str, metadata: dict) -> str:
    """Get deployment instructions based on project type.

    Pulls from Knowledge Base when available, falls back to built-in guides.
    """
    # Try to get from Knowledge Base first
    try:
        from ..knowledge import KnowledgeManager

        km = KnowledgeManager()

        # Map project type to platform
        platform_map = {
            "ios": "ios",
            "android": "android",
            "react": "web",
            "vue": "web",
            "web": "web",
            "python": "python",
            "node": "node",
            "flutter": "flutter",
            "go": "python",  # Similar deployment
            "rust": "python",  # Similar deployment
        }

        platform = platform_map.get(project_type)
        if platform:
            guide = km.get_deployment_guide(platform)
            if guide:
                # Extract key sections from the full guide
                content = guide.content
                # Add a link to the full guide
                return f"""### Deployment Guide

See the full [{guide.title}](/knowledge/{guide.id}) in the Knowledge Base.

**Quick Commands:**
```bash
{chr(10).join(guide.commands[:3]) if guide.commands else "# Check the full guide for commands"}
```

**Prerequisites:**
{chr(10).join("- " + p for p in guide.prerequisites[:4]) if guide.prerequisites else "See full guide"}

For detailed step-by-step instructions, visit the [Knowledge Base](/knowledge/{guide.id}).
"""
    except ImportError:
        pass  # Knowledge base not available, use fallback

    # Fallback to built-in guides
    guides = {
        "ios": """### App Store Deployment

1. **Prepare for submission:**
   - Create app icons (all required sizes)
   - Prepare screenshots for all device sizes
   - Write app description and keywords

2. **Archive and upload:**
   - In Xcode: Product → Archive
   - Use Xcode Organizer to upload to App Store Connect

3. **App Store Connect:**
   - Go to [App Store Connect](https://appstoreconnect.apple.com)
   - Create a new app or select existing
   - Fill in metadata, pricing, and availability
   - Submit for review

4. **TestFlight (Beta Testing):**
   - Upload your build
   - Add internal/external testers
   - Collect feedback before full release""",

        "android": """### Google Play Store Deployment

1. **Prepare for submission:**
   - Generate signed APK/AAB: Build → Generate Signed Bundle/APK
   - Create app icons and feature graphics
   - Prepare screenshots for different device sizes

2. **Google Play Console:**
   - Go to [Google Play Console](https://play.google.com/console)
   - Create a new app
   - Fill in store listing details

3. **Release:**
   - Upload your AAB (Android App Bundle)
   - Set up pricing and distribution
   - Submit for review

4. **Internal Testing:**
   - Use internal testing track for initial testing
   - Graduate to closed/open testing before production""",

        "react": """### Deployment Options

**Vercel (Recommended):**
```bash
npm install -g vercel
vercel
```

**Netlify:**
```bash
npm run build
# Drag 'build' folder to netlify.com
# Or use Netlify CLI: netlify deploy
```

**GitHub Pages:**
```bash
npm install gh-pages --save-dev
# Add to package.json: "homepage": "https://username.github.io/repo"
npm run build
npx gh-pages -d build
```

**Docker:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install && npm run build
RUN npm install -g serve
CMD ["serve", "-s", "build", "-l", "3000"]
```""",

        "vue": """### Deployment Options

**Vercel:**
```bash
npm install -g vercel
vercel
```

**Netlify:**
```bash
npm run build
netlify deploy --prod --dir=dist
```

**Docker:**
```bash
docker build -t myapp .
docker run -p 80:80 myapp
```""",

        "web": """### Deployment Options

**GitHub Pages:**
1. Push to GitHub repository
2. Go to Settings → Pages
3. Select branch and folder
4. Your site will be at `https://username.github.io/repo`

**Netlify:**
1. Drag and drop your folder to [netlify.com](https://netlify.com)
2. Or connect your Git repository

**Any Static Host:**
Upload files to any web hosting service (AWS S3, Cloudflare Pages, etc.)""",

        "python": """### Deployment Options

**Heroku:**
```bash
heroku create myapp
git push heroku main
```

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**AWS Lambda:**
Use AWS SAM or Serverless Framework for serverless deployment.

**VPS (DigitalOcean, Linode, etc.):**
```bash
ssh user@server
git clone <repo>
pip install -r requirements.txt
python main.py  # Or use gunicorn/uvicorn for web apps
```""",

        "node": """### Deployment Options

**Vercel:**
```bash
vercel
```

**Heroku:**
```bash
heroku create
git push heroku main
```

**Docker:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["node", "index.js"]
```

**PM2 (VPS):**
```bash
npm install -g pm2
pm2 start index.js
pm2 save
```""",

        "go": """### Deployment Options

**Build and deploy binary:**
```bash
go build -o app
./app  # Run directly on server
```

**Docker:**
```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o app

FROM alpine:latest
COPY --from=builder /app/app /app
CMD ["/app"]
```

**Google Cloud Run / AWS Lambda:**
Use respective CLIs for serverless deployment.""",

        "rust": """### Deployment Options

**Build release binary:**
```bash
cargo build --release
./target/release/app
```

**Docker:**
```dockerfile
FROM rust:1.70 AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /app
CMD ["/app"]
```""",

        "generic": """### General Deployment Steps

1. **Choose a hosting platform** based on your project type
2. **Prepare your code** for production (build, minify, etc.)
3. **Set up environment variables** for secrets and configuration
4. **Deploy** using platform-specific tools or CI/CD
5. **Monitor** your application after deployment

See platform-specific documentation for detailed instructions.""",
    }

    return guides.get(project_type, guides["generic"])


def _describe_file(filename: str) -> str:
    """Generate a brief description for a file based on its name/extension."""
    name = filename.lower()
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    # Common file descriptions
    if name in ["main.py", "app.py", "index.py"]:
        return "Main application entry point"
    elif name in ["index.js", "index.ts", "main.js"]:
        return "Main application entry point"
    elif name in ["index.html"]:
        return "Main HTML page"
    elif name in ["readme.md"]:
        return "Project documentation"
    elif name in ["requirements.txt"]:
        return "Python dependencies"
    elif name in ["package.json"]:
        return "Node.js project configuration and dependencies"
    elif name in ["dockerfile"]:
        return "Docker container configuration"
    elif name.endswith("test.py") or name.endswith("_test.py"):
        return "Test file"
    elif name.endswith(".spec.js") or name.endswith(".test.js"):
        return "Test file"
    elif "config" in name:
        return "Configuration file"
    elif ext == "css":
        return "Stylesheet"
    elif ext == "html":
        return "HTML page"
    elif ext in ["py"]:
        return "Python module"
    elif ext in ["js", "ts"]:
        return "JavaScript/TypeScript module"
    elif ext in ["jsx", "tsx"]:
        return "React component"
    elif ext == "vue":
        return "Vue component"
    elif ext in ["java", "kt"]:
        return "Android/Java source file"
    elif ext == "swift":
        return "iOS Swift source file"
    elif ext == "go":
        return "Go source file"
    elif ext == "rs":
        return "Rust source file"
    elif ext in ["json", "yaml", "yml"]:
        return "Configuration/data file"
    elif ext == "sql":
        return "Database schema/queries"
    elif ext == "md":
        return "Documentation"
    else:
        return "Project file"


def create_project_zip(
    project_name: str,
    files: dict[str, str],
    metadata: Optional[dict] = None,
    include_readme: bool = True
) -> BytesIO:
    """Create a ZIP file of project files.

    Args:
        project_name: Name for the ZIP
        files: Dict of filename -> content
        metadata: Project metadata for README generation
        include_readme: Whether to include a README

    Returns:
        BytesIO buffer containing ZIP file
    """
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(f"{project_name}/{filename}", content)

        if include_readme:
            readme = generate_readme(project_name, metadata or {}, files)
            zf.writestr(f"{project_name}/README.md", readme)

    buffer.seek(0)
    return buffer


def parse_code_blocks(content: str) -> dict[str, str]:
    """Parse code blocks from agent output.

    Args:
        content: Agent output with ```language code``` blocks

    Returns:
        Dict of filename -> code content
    """
    import re

    files = {}

    # Pattern to match code blocks with optional language
    pattern = r'```(\w+)?\s*\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    lang_extensions = {
        "python": ".py",
        "py": ".py",
        "javascript": ".js",
        "js": ".js",
        "typescript": ".ts",
        "ts": ".ts",
        "html": ".html",
        "css": ".css",
        "json": ".json",
        "yaml": ".yaml",
        "yml": ".yaml",
        "bash": ".sh",
        "sh": ".sh",
        "sql": ".sql",
        "markdown": ".md",
        "md": ".md",
        "go": ".go",
        "rust": ".rs",
        "rs": ".rs",
        "java": ".java",
        "kotlin": ".kt",
        "kt": ".kt",
        "swift": ".swift",
        "c": ".c",
        "cpp": ".cpp",
        "csharp": ".cs",
        "cs": ".cs",
        "php": ".php",
        "ruby": ".rb",
        "rb": ".rb",
        "xml": ".xml",
        "toml": ".toml",
        "ini": ".ini",
        "env": ".env",
        "dockerfile": "Dockerfile",
        "makefile": "Makefile",
    }

    # Find file markers with their positions for position-aware matching
    # Patterns:
    # - "**filename.ext**" or "### filename.ext" or "File: filename.ext"
    # - "### `filename.ext`" (with backticks - common in Mason output)
    file_marker_pattern = r'(?:\*\*|###?\s*`?|##\s*`?|File:\s*|Filename:\s*)([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)`?'
    file_markers_with_pos = [(m.group(1), m.start()) for m in re.finditer(file_marker_pattern, content)]

    # Find code block positions
    code_block_pattern = r'```(\w+)?\s*\n(.*?)```'
    code_blocks_with_pos = [(m.group(1), m.group(2), m.start()) for m in re.finditer(code_block_pattern, content, re.DOTALL)]

    for i, (lang, code, block_pos) in enumerate(code_blocks_with_pos):
        lang = lang.lower() if lang else "txt"
        ext = lang_extensions.get(lang, f".{lang}" if lang else ".txt")

        # Try multiple methods to find filename
        filename = None
        lines = code.strip().split('\n')

        # Method 1: Check for filename in first comment line
        if lines:
            first_line = lines[0].strip()
            # Patterns: # filename.py, // filename.js, <!-- filename.html -->, /* filename.css */
            comment_patterns = [
                r'^#\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',  # Python/bash
                r'^//\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',  # JS/C++
                r'^<!--\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',  # HTML
                r'^/\*\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',  # CSS/C
            ]
            for cp in comment_patterns:
                match = re.match(cp, first_line)
                if match:
                    filename = match.group(1)
                    break

        # Method 2: Find closest preceding file marker (position-aware)
        if not filename:
            closest_marker = None
            closest_distance = float('inf')
            for marker_name, marker_pos in file_markers_with_pos:
                # Marker must be before this code block
                if marker_pos < block_pos:
                    distance = block_pos - marker_pos
                    # Only use if within reasonable distance (200 chars) and closer than current
                    if distance < 200 and distance < closest_distance:
                        closest_marker = marker_name
                        closest_distance = distance
            if closest_marker:
                filename = closest_marker

        # Method 3: Detect from content patterns
        if not filename:
            if lang == "html" and '<!DOCTYPE' in code.upper():
                filename = "index.html"
            elif lang == "css" and ('body' in code or 'html' in code):
                filename = "styles.css"
            elif lang == "json" and '"name"' in code and '"version"' in code:
                filename = "package.json"
            elif lang == "py" and ('def main' in code or 'if __name__' in code):
                filename = "main.py"
            elif lang == "js" and ('module.exports' in code or 'export ' in code):
                filename = "index.js"

        # Method 4: Generate filename based on order and language
        if not filename:
            if lang == "html":
                filename = f"page_{i+1}.html" if i > 0 else "index.html"
            elif lang == "css":
                filename = f"style_{i+1}.css" if i > 0 else "styles.css"
            elif lang == "js" or lang == "javascript":
                filename = f"script_{i+1}.js" if i > 0 else "main.js"
            elif lang == "py" or lang == "python":
                filename = f"module_{i+1}.py" if i > 0 else "main.py"
            else:
                filename = f"file_{i+1}{ext}"

        # Clean up the filename
        filename = filename.strip().replace(' ', '_')

        # Store the file (handle duplicates by appending number)
        base_filename = filename
        counter = 1
        while filename in files:
            name, extension = base_filename.rsplit('.', 1) if '.' in base_filename else (base_filename, '')
            filename = f"{name}_{counter}.{extension}" if extension else f"{name}_{counter}"
            counter += 1

        files[filename] = code.strip()

    return files


def add_revision(metadata: dict, agent: str, content: dict) -> dict:
    """Add a revision entry to project metadata.

    Args:
        metadata: Current project metadata
        agent: Agent name that produced the revision
        content: Content to store as revision

    Returns:
        Updated metadata with revision added
    """
    if "revisions" not in metadata:
        metadata["revisions"] = []

    revision = {
        "id": len(metadata["revisions"]) + 1,
        "agent": agent,
        "timestamp": datetime.now().isoformat(),
        "content": content,
    }

    metadata["revisions"].append(revision)
    return metadata


def add_feedback(metadata: dict, agent: str, rating: int, comment: str = "") -> dict:
    """Add feedback for an agent's output.

    Args:
        metadata: Current project metadata
        agent: Agent name to rate
        rating: 1-5 rating
        comment: Optional feedback comment

    Returns:
        Updated metadata with feedback added
    """
    if "feedback" not in metadata:
        metadata["feedback"] = []

    feedback = {
        "agent": agent,
        "rating": max(1, min(5, rating)),  # Clamp to 1-5
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
    }

    metadata["feedback"].append(feedback)
    return metadata


def get_feedback_summary(metadata: dict) -> dict:
    """Get summary of feedback for a project.

    Args:
        metadata: Project metadata

    Returns:
        Feedback summary by agent
    """
    feedback_list = metadata.get("feedback", [])

    summary = {
        "total_ratings": len(feedback_list),
        "by_agent": {},
        "average_rating": 0.0,
    }

    if not feedback_list:
        return summary

    # Group by agent
    agent_ratings = {}
    for fb in feedback_list:
        agent = fb["agent"]
        if agent not in agent_ratings:
            agent_ratings[agent] = []
        agent_ratings[agent].append(fb["rating"])

    # Calculate averages
    all_ratings = []
    for agent, ratings in agent_ratings.items():
        avg = sum(ratings) / len(ratings)
        summary["by_agent"][agent] = {
            "average": round(avg, 2),
            "count": len(ratings),
        }
        all_ratings.extend(ratings)

    summary["average_rating"] = round(sum(all_ratings) / len(all_ratings), 2)

    return summary


# ================================================
# TOKEN PROJECTION & BUDGET TRACKING
# ================================================

def project_next_step_tokens(
    next_agent: str,
    context: dict,
    previous_output_tokens: int = 0,
) -> dict:
    """Project token usage for the next agent step.

    Args:
        next_agent: Name of the next agent (architect, mason, oracle)
        context: Project context with features, description, etc.
        previous_output_tokens: Tokens from previous agent output (becomes input)

    Returns:
        Dict with projected input/output/total tokens
    """
    estimates = AGENT_TOKEN_ESTIMATES.get(next_agent, AGENT_TOKEN_ESTIMATES["architect"])

    # Count features
    features = context.get("features", [])
    num_features = len(features) if isinstance(features, list) else 1

    # Estimate input tokens
    description = context.get("description", "")
    problem = context.get("problem", "")
    technical = context.get("technical", "")

    # Base input: description + problem + technical + previous output
    base_input_chars = len(description) + len(problem) + len(technical)
    base_input_tokens = base_input_chars // 4  # ~4 chars per token

    # Add previous output as context
    input_tokens = base_input_tokens + previous_output_tokens

    # Add system prompt overhead (~500 tokens)
    input_tokens += 500

    # Estimate output tokens
    output_tokens = estimates["base_output"]
    output_tokens += estimates["per_feature"] * num_features

    # Also factor in input size
    output_tokens += int(input_tokens * estimates["input_multiplier"])

    total_tokens = input_tokens + output_tokens

    return {
        "agent": next_agent,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "confidence": "estimate",
        "factors": {
            "num_features": num_features,
            "context_size": base_input_tokens,
            "previous_output": previous_output_tokens,
        }
    }


def get_provider_token_usage(metadata: dict) -> dict:
    """Get token usage broken down by provider/LLM.

    Args:
        metadata: Project metadata

    Returns:
        Dict with usage per provider
    """
    usage = {
        "by_provider": {},
        "total": 0,
    }

    # Collect from all agent outputs
    agent_outputs = [
        ("architect", metadata.get("plan", {}).get("agent_output", {})),
        ("mason", metadata.get("build", {}).get("agent_output", {})),
        ("oracle", metadata.get("verification", {}).get("agent_output", {})),
    ]

    for agent_name, output in agent_outputs:
        if not output:
            continue

        provider = output.get("provider", "unknown")
        tokens = output.get("tokens_used", 0)
        prompt_tokens = output.get("prompt_tokens", 0)
        completion_tokens = output.get("completion_tokens", 0)

        if provider not in usage["by_provider"]:
            usage["by_provider"][provider] = {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "calls": 0,
                "agents": [],
            }

        usage["by_provider"][provider]["total_tokens"] += tokens
        usage["by_provider"][provider]["prompt_tokens"] += prompt_tokens
        usage["by_provider"][provider]["completion_tokens"] += completion_tokens
        usage["by_provider"][provider]["calls"] += 1
        usage["by_provider"][provider]["agents"].append(agent_name)

        usage["total"] += tokens

    return usage


def get_budget_status(
    metadata: dict,
    budgets: Optional[dict] = None,
) -> dict:
    """Get budget/allowance status with percentages.

    Args:
        metadata: Project metadata with token usage
        budgets: Optional custom budgets (uses DEFAULT_BUDGETS if not provided)

    Returns:
        Dict with budget status per provider and overall
    """
    if budgets is None:
        budgets = DEFAULT_BUDGETS.copy()

    provider_usage = get_provider_token_usage(metadata)
    tokens = metadata.get("tokens", {"total": 0, "by_agent": {}})

    status = {
        "by_provider": {},
        "total": {
            "used": tokens.get("total", 0),
            "budget": budgets.get("total", DEFAULT_BUDGETS["total"]),
            "percentage": 0.0,
            "remaining": 0,
        }
    }

    # Calculate total percentage
    total_budget = status["total"]["budget"]
    total_used = status["total"]["used"]
    if total_budget > 0 and total_budget != float('inf'):
        status["total"]["percentage"] = round((total_used / total_budget) * 100, 2)
        status["total"]["remaining"] = total_budget - total_used
    else:
        status["total"]["percentage"] = 0.0
        status["total"]["remaining"] = float('inf')

    # Calculate per-provider
    for provider, usage in provider_usage.get("by_provider", {}).items():
        provider_budget = budgets.get(provider.lower(), budgets.get("total", 1_000_000))
        provider_used = usage.get("total_tokens", 0)

        if provider_budget == float('inf'):
            percentage = 0.0
            remaining = float('inf')
        elif provider_budget > 0:
            percentage = round((provider_used / provider_budget) * 100, 2)
            remaining = provider_budget - provider_used
        else:
            percentage = 100.0
            remaining = 0

        status["by_provider"][provider] = {
            "used": provider_used,
            "budget": provider_budget,
            "percentage": percentage,
            "remaining": remaining,
            "calls": usage.get("calls", 0),
            "is_unlimited": provider_budget == float('inf'),
        }

    return status


def format_token_count(count: int) -> str:
    """Format token count for display (e.g., 1.5K, 2.3M).

    Args:
        count: Token count

    Returns:
        Formatted string
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def get_budget_color(percentage: float) -> str:
    """Get color class based on budget percentage.

    Args:
        percentage: Usage percentage (0-100)

    Returns:
        CSS color class
    """
    if percentage >= 90:
        return "critical"  # Red
    elif percentage >= 75:
        return "warning"   # Orange
    elif percentage >= 50:
        return "moderate"  # Yellow
    else:
        return "good"      # Green
