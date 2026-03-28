"""AppBuilder - Creates mobile applications using React Native.

This builder specializes in creating cross-platform mobile apps.
Output is React Native code ready for Expo development.

Products:
- iOS apps
- Android apps
- Cross-platform mobile apps
"""

import json
import logging
from typing import Optional

from atlas.agents.base import AgentOutput, AgentStatus
from .base import BaseBuilder, BuilderType, BuildOutput, BuildContext, OutputFormat
from .config import get_app_config, AppConfig

logger = logging.getLogger("atlas.builders.app")


class AppBuilder(BaseBuilder):
    """Builder for mobile applications using React Native.

    Creates cross-platform mobile apps that run on iOS and Android.
    Output is React Native/Expo code ready for development and deployment.
    """

    name = "app_builder"
    description = "Mobile app specialist (React Native)"
    icon = "📱"
    color = "#9C27B0"

    builder_type = BuilderType.APP
    supported_formats = [OutputFormat.REACT_NATIVE, OutputFormat.JSON]

    def __init__(self, router=None, memory=None, **kwargs):
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._callbacks = []
        self.config: AppConfig = get_app_config()

    def _get_builder_context(self) -> str:
        """Get AppBuilder-specific context."""
        return """You are the AppBuilder - expert in creating mobile applications.

YOUR SPECIALIZATION:
- Cross-platform mobile apps (iOS + Android)
- React Native with Expo
- Modern mobile UI/UX patterns
- App Store ready applications

TECH STACK:
- React Native (latest)
- Expo SDK
- TypeScript
- React Navigation
- Expo Vector Icons

OUTPUT REQUIREMENTS:
- Generate complete, runnable React Native code
- Use functional components with hooks
- Follow React Native best practices
- Include proper typing (TypeScript)
- Use Expo-compatible libraries only

MOBILE DESIGN PRINCIPLES:
1. NATIVE FEEL: Platform-appropriate interactions
2. PERFORMANT: Smooth 60fps animations
3. ACCESSIBLE: Screen reader support
4. INTUITIVE: Obvious navigation patterns
5. CONSISTENT: Unified design system

OUTPUT FORMAT:
Generate a complete React Native project structure as JSON:
{
    "files": {
        "App.tsx": "// main app code",
        "screens/HomeScreen.tsx": "// screen code",
        ...
    },
    "package.json": { ... },
    "app.json": { ... }
}

Include all necessary files for a working Expo app."""

    def get_system_prompt(self) -> str:
        """Get the full system prompt."""
        mission = """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

Your job is to create SELLABLE mobile apps. Every output must be something
professional and ready for App Store or Google Play submission."""

        return f"{mission}\n\n{self._get_builder_context()}"

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a build request."""
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            build_context = BuildContext(
                project_name=context.get("name", "Mobile App") if context else "Mobile App",
                project_description=task,
                business_brief=context.get("business_brief", {}) if context else {},
                mockup=context.get("mockup") if context else None,
                plan=context.get("plan") if context else None,
            )

            self.status = AgentStatus.WORKING
            output = await self.build(build_context)

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=output.content,
                artifacts={
                    "build_output": output.to_dict(),
                    "files": output.files,
                    "format": output.format.value,
                },
                metadata={
                    "agent": self.name,
                    "builder_type": self.builder_type.value,
                },
            )

        except Exception as e:
            logger.error(f"[AppBuilder] Build failed: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Build failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    async def build(self, context: BuildContext) -> BuildOutput:
        """Build a mobile application.

        Args:
            context: Build context with all necessary information

        Returns:
            BuildOutput with React Native code
        """
        logger.info(f"[AppBuilder] Building: {context.project_name}")

        # Determine app type and settings
        app_type = self._detect_app_type(context)
        app_config = self._get_app_settings(context, app_type)

        # Generate the app structure
        prompt = self._build_generation_prompt(context, app_type, app_config)

        response, token_info = await self._generate_with_provider(
            prompt,
            temperature=0.7,
        )

        # Parse the response into files
        files = self._parse_app_files(response, context)

        # Generate preview HTML (shows app screenshots/mockup)
        preview_html = self._generate_preview_html(context, files)

        return BuildOutput(
            content=json.dumps(files, indent=2),
            format=OutputFormat.REACT_NATIVE,
            files=files,
            metadata={
                "app_type": app_type,
                "config": app_config,
                "tokens_used": token_info.get("total_tokens", 0),
            },
        )

    async def generate_preview(self, output: BuildOutput) -> str:
        """Generate a preview - shows app structure and key screens."""
        return self._generate_preview_html(None, output.files)

    def _detect_app_type(self, context: BuildContext) -> str:
        """Detect the type of mobile app."""
        description = context.project_description.lower()
        brief = context.business_brief

        if brief.get("product_type"):
            return brief["product_type"]

        if any(word in description for word in ["social", "community", "chat"]):
            return "social"
        if any(word in description for word in ["fitness", "health", "workout"]):
            return "fitness"
        if any(word in description for word in ["productivity", "task", "todo"]):
            return "productivity"
        if any(word in description for word in ["commerce", "shop", "store"]):
            return "ecommerce"
        if any(word in description for word in ["utility", "tool"]):
            return "utility"

        return "general"

    def _get_app_settings(self, context: BuildContext, app_type: str) -> dict:
        """Get app-specific settings."""
        brief = context.business_brief

        settings = {
            "use_expo": self.config.use_expo,
            "navigation": self.config.default_navigation,
            "target_ios": self.config.target_ios,
            "target_android": self.config.target_android,
        }

        # Type-specific settings
        if app_type == "social":
            settings["navigation"] = "tab"
            settings["features"] = ["auth", "feed", "profile", "messaging"]
        elif app_type == "fitness":
            settings["navigation"] = "tab"
            settings["features"] = ["dashboard", "workouts", "progress", "settings"]
        elif app_type == "productivity":
            settings["navigation"] = "stack"
            settings["features"] = ["home", "create", "list", "settings"]
        elif app_type == "ecommerce":
            settings["navigation"] = "tab"
            settings["features"] = ["home", "catalog", "cart", "profile"]
        else:
            settings["features"] = ["home", "details", "settings"]

        return settings

    def _build_generation_prompt(
        self,
        context: BuildContext,
        app_type: str,
        settings: dict,
    ) -> str:
        """Build the prompt for generating the mobile app."""
        brief = context.business_brief

        # Create safe app name
        app_name = "".join(c for c in context.project_name if c.isalnum() or c in " -_")
        app_slug = app_name.lower().replace(" ", "-")

        prompt_parts = [
            f"Create a complete React Native mobile app based on these specifications:",
            "",
            f"## App: {context.project_name}",
            f"Description: {context.project_description}",
            f"App Type: {app_type}",
            f"Navigation: {settings['navigation']}",
            "",
        ]

        # Add business brief context
        if brief:
            if brief.get("target_customer"):
                prompt_parts.append("## Target User:")
                prompt_parts.append(str(brief["target_customer"]))
                prompt_parts.append("")

            if brief.get("success_criteria"):
                prompt_parts.append("## Success Criteria:")
                for criterion in brief.get("success_criteria", []):
                    prompt_parts.append(f"- {criterion.get('criterion', criterion)}")
                prompt_parts.append("")

        # Features
        prompt_parts.extend([
            "## Core Features:",
            *[f"- {feature}" for feature in settings.get("features", [])],
            "",
        ])

        prompt_parts.extend([
            "## Technical Requirements:",
            "- React Native with Expo SDK 50+",
            "- TypeScript for all code",
            "- Functional components with hooks",
            "- React Navigation 6.x",
            "- Expo Vector Icons",
            "- Clean, maintainable code structure",
            "",
            "## Output Format:",
            "Generate a JSON object with this structure:",
            "```json",
            "{",
            '  "files": {',
            '    "App.tsx": "// App entry point",',
            '    "app.json": "// Expo config as string",',
            '    "package.json": "// Dependencies as string",',
            '    "screens/HomeScreen.tsx": "// Screen code",',
            '    "components/Header.tsx": "// Component code",',
            '    "navigation/index.tsx": "// Navigation setup"',
            "  }",
            "}",
            "```",
            "",
            f"Use app name: {app_name}",
            f"Use slug: {app_slug}",
            "",
            "Generate complete, working code for each file.",
            "Output valid JSON only, no explanations.",
        ])

        return "\n".join(prompt_parts)

    def _parse_app_files(self, response: str, context: BuildContext) -> dict[str, str]:
        """Parse the LLM response into app files."""
        try:
            # Extract JSON
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end]
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                response = response[start:end]

            data = json.loads(response)

            if "files" in data:
                return data["files"]
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"[AppBuilder] Failed to parse JSON: {e}")
            # Return minimal app structure
            return self._generate_minimal_app(context)

    def _generate_minimal_app(self, context: BuildContext) -> dict[str, str]:
        """Generate a minimal working app structure."""
        app_name = context.project_name
        slug = app_name.lower().replace(" ", "-").replace("_", "-")

        return {
            "App.tsx": f'''import React from 'react';
import {{ SafeAreaView, Text, StyleSheet }} from 'react-native';

export default function App() {{
  return (
    <SafeAreaView style={{styles.container}}>
      <Text style={{styles.title}}>{app_name}</Text>
      <Text style={{styles.subtitle}}>Your app is ready!</Text>
    </SafeAreaView>
  );
}}

const styles = StyleSheet.create({{
  container: {{
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  }},
  title: {{
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 10,
  }},
  subtitle: {{
    fontSize: 16,
    color: '#666',
  }},
}});
''',
            "app.json": json.dumps({
                "expo": {
                    "name": app_name,
                    "slug": slug,
                    "version": "1.0.0",
                    "orientation": "portrait",
                    "icon": "./assets/icon.png",
                    "userInterfaceStyle": "automatic",
                    "splash": {
                        "backgroundColor": "#ffffff"
                    },
                    "ios": {
                        "supportsTablet": True
                    },
                    "android": {
                        "adaptiveIcon": {
                            "backgroundColor": "#ffffff"
                        }
                    }
                }
            }, indent=2),
            "package.json": json.dumps({
                "name": slug,
                "version": "1.0.0",
                "main": "expo/AppEntry.js",
                "scripts": {
                    "start": "expo start",
                    "android": "expo start --android",
                    "ios": "expo start --ios",
                    "web": "expo start --web"
                },
                "dependencies": {
                    "expo": "~50.0.0",
                    "expo-status-bar": "~1.11.0",
                    "react": "18.2.0",
                    "react-native": "0.73.0"
                },
                "devDependencies": {
                    "@types/react": "~18.2.0",
                    "typescript": "^5.3.0"
                }
            }, indent=2),
        }

    def _generate_preview_html(self, context: Optional[BuildContext], files: dict) -> str:
        """Generate preview HTML showing the app structure."""
        project_name = context.project_name if context else "Mobile App"

        file_list = "\n".join([
            f'<div class="file-item"><span class="file-icon">📄</span>{name}</div>'
            for name in sorted(files.keys())
        ])

        # Get App.tsx preview if available
        app_code = files.get("App.tsx", "// No App.tsx found")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview: {project_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .preview-header {{
            text-align: center;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .preview-header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .preview-header p {{
            color: #888;
        }}
        .preview-content {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .file-tree {{
            background: #16213e;
            padding: 20px;
            border-radius: 12px;
        }}
        .file-tree h3 {{
            margin-bottom: 15px;
            color: #4ecca3;
        }}
        .file-item {{
            padding: 8px 12px;
            border-radius: 6px;
            margin: 4px 0;
            font-family: monospace;
            font-size: 13px;
        }}
        .file-item:hover {{
            background: rgba(255,255,255,0.1);
        }}
        .file-icon {{
            margin-right: 8px;
        }}
        .code-preview {{
            background: #16213e;
            padding: 20px;
            border-radius: 12px;
        }}
        .code-preview h3 {{
            margin-bottom: 15px;
            color: #4ecca3;
        }}
        .code-preview pre {{
            background: #0f0f1a;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.5;
        }}
        .phone-mockup {{
            width: 280px;
            height: 560px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 40px;
            padding: 15px;
            margin: 30px auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .phone-screen {{
            width: 100%;
            height: 100%;
            background: #f5f5f5;
            border-radius: 28px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .phone-screen h2 {{
            color: #333;
            font-size: 24px;
        }}
        .phone-screen p {{
            color: #666;
            font-size: 14px;
        }}
        .install-instructions {{
            background: #16213e;
            padding: 20px;
            border-radius: 12px;
            margin-top: 30px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }}
        .install-instructions h3 {{
            color: #4ecca3;
            margin-bottom: 15px;
        }}
        .install-instructions code {{
            background: #0f0f1a;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
        }}
        .install-instructions ol {{
            padding-left: 20px;
        }}
        .install-instructions li {{
            margin: 10px 0;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="preview-header">
        <h1>📱 {project_name}</h1>
        <p>React Native Mobile App</p>
    </div>

    <div class="phone-mockup">
        <div class="phone-screen">
            <h2>{project_name}</h2>
            <p>Your app is ready!</p>
        </div>
    </div>

    <div class="preview-content">
        <div class="file-tree">
            <h3>📁 Project Files</h3>
            {file_list}
        </div>
        <div class="code-preview">
            <h3>App.tsx</h3>
            <pre><code>{app_code[:2000]}{'...' if len(app_code) > 2000 else ''}</code></pre>
        </div>
    </div>

    <div class="install-instructions">
        <h3>🚀 Getting Started</h3>
        <ol>
            <li>Create a new Expo project: <code>npx create-expo-app@latest {project_name.lower().replace(' ', '-')}</code></li>
            <li>Replace the generated files with the ones from this build</li>
            <li>Install dependencies: <code>npm install</code></li>
            <li>Start the development server: <code>npx expo start</code></li>
            <li>Scan the QR code with Expo Go app on your phone</li>
        </ol>
    </div>
</body>
</html>"""
