"""The Governor - Intelligent LLM and integration routing powered by Ollama.

The Governor routes tasks to the optimal LLM provider AND recommends
integrations (Canva, Figma, KDP, etc.) based on product needs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json

from atlas.standards import PRODUCT_INTEGRATIONS, get_agent_philosophy


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"      # Basic tasks, can use free/cheap models
    MEDIUM = "medium"      # Moderate tasks, mid-tier models
    COMPLEX = "complex"    # Complex tasks, premium models required


class TaskType(Enum):
    """Types of tasks for routing."""
    PLANNING = "planning"           # Architecture, design, strategy
    CODING = "coding"               # Writing code, implementation
    REVIEW = "review"               # Code review, verification
    ANALYSIS = "analysis"           # Understanding, research
    SIMPLE_QUERY = "simple_query"   # Basic questions, formatting


@dataclass
class IntegrationRecommendation:
    """Recommended integrations for a product."""
    product_type: str
    design_tools: list[str] = field(default_factory=list)  # canva, figma
    publish_platforms: list[str] = field(default_factory=list)  # etsy, kdp, app_store
    needs_cover: bool = False
    needs_icon: bool = False
    needs_docs: bool = False
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "product_type": self.product_type,
            "design_tools": self.design_tools,
            "publish_platforms": self.publish_platforms,
            "needs_cover": self.needs_cover,
            "needs_icon": self.needs_icon,
            "needs_docs": self.needs_docs,
            "reasoning": self.reasoning,
        }


@dataclass
class RoutingDecision:
    """A routing decision from the Governor."""
    provider: str                   # e.g., "ollama", "openai", "anthropic"
    model: str                      # e.g., "llama3", "gpt-4", "claude-3-opus"
    complexity: TaskComplexity
    task_type: TaskType
    reasoning: str                  # Why this decision was made
    estimated_tokens: int           # Estimated token usage
    estimated_cost: float           # Estimated cost in dollars
    confidence: float               # 0.0 to 1.0
    fallback_provider: Optional[str] = None  # If primary fails
    fallback_model: Optional[str] = None
    integrations: Optional[IntegrationRecommendation] = None  # Recommended integrations

    def to_dict(self) -> dict:
        result = {
            "provider": self.provider,
            "model": self.model,
            "complexity": self.complexity.value,
            "task_type": self.task_type.value,
            "reasoning": self.reasoning,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost": self.estimated_cost,
            "confidence": self.confidence,
            "fallback_provider": self.fallback_provider,
            "fallback_model": self.fallback_model,
        }
        if self.integrations:
            result["integrations"] = self.integrations.to_dict()
        return result


# Model capabilities and costs
MODEL_REGISTRY = {
    # Ollama (free, local)
    "ollama": {
        "llama3": {
            "cost_per_1k": 0.0,
            "capabilities": ["coding", "analysis", "simple_query"],
            "quality": 0.7,
            "speed": "fast",
            "context_window": 8192,
        },
        "llama3:70b": {
            "cost_per_1k": 0.0,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.85,
            "speed": "medium",
            "context_window": 8192,
        },
        "codellama": {
            "cost_per_1k": 0.0,
            "capabilities": ["coding", "review"],
            "quality": 0.75,
            "speed": "fast",
            "context_window": 16384,
        },
        "mistral": {
            "cost_per_1k": 0.0,
            "capabilities": ["coding", "analysis", "simple_query"],
            "quality": 0.7,
            "speed": "fast",
            "context_window": 8192,
        },
    },
    # OpenAI
    "openai": {
        "gpt-4": {
            "cost_per_1k": 0.03,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.95,
            "speed": "medium",
            "context_window": 8192,
        },
        "gpt-4-turbo": {
            "cost_per_1k": 0.01,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.93,
            "speed": "fast",
            "context_window": 128000,
        },
        "gpt-4o": {
            "cost_per_1k": 0.005,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.92,
            "speed": "fast",
            "context_window": 128000,
        },
        "gpt-3.5-turbo": {
            "cost_per_1k": 0.0005,
            "capabilities": ["coding", "analysis", "simple_query"],
            "quality": 0.75,
            "speed": "very_fast",
            "context_window": 16384,
        },
    },
    # Anthropic (Claude)
    "anthropic": {
        "claude-3-opus": {
            "cost_per_1k": 0.015,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.97,
            "speed": "medium",
            "context_window": 200000,
        },
        "claude-3-sonnet": {
            "cost_per_1k": 0.003,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.90,
            "speed": "fast",
            "context_window": 200000,
        },
        "claude-3-haiku": {
            "cost_per_1k": 0.00025,
            "capabilities": ["coding", "analysis", "review", "simple_query"],
            "quality": 0.80,
            "speed": "very_fast",
            "context_window": 200000,
        },
    },
    # Google (Gemini)
    "gemini": {
        "gemini-1.5-pro": {
            "cost_per_1k": 0.0035,
            "capabilities": ["planning", "coding", "analysis", "review"],
            "quality": 0.90,
            "speed": "fast",
            "context_window": 1000000,
        },
        "gemini-1.5-flash": {
            "cost_per_1k": 0.00035,
            "capabilities": ["coding", "analysis", "simple_query"],
            "quality": 0.80,
            "speed": "very_fast",
            "context_window": 1000000,
        },
    },
}


class Governor:
    """The Governor - Intelligent LLM routing agent.

    Uses Ollama (free, local) to analyze tasks and make smart routing
    decisions to optimize for cost, quality, and speed.
    """

    def __init__(
        self,
        ollama_model: str = "llama3",
        available_providers: list[str] = None,
        budget_limit: float = 10.0,  # Monthly budget in dollars
        budget_used: float = 0.0,
        prefer_local: bool = False,  # Prefer Ollama when quality is similar
    ):
        """Initialize the Governor.

        Args:
            ollama_model: Ollama model to use for routing decisions
            available_providers: List of available providers
            budget_limit: Monthly budget limit in dollars
            budget_used: Amount already spent
            prefer_local: Whether to prefer local/free models
        """
        self.ollama_model = ollama_model
        self.available_providers = available_providers or ["ollama", "openai", "anthropic", "gemini"]
        self.budget_limit = budget_limit
        self.budget_used = budget_used
        self.prefer_local = prefer_local

    @property
    def budget_remaining(self) -> float:
        return max(0, self.budget_limit - self.budget_used)

    @property
    def budget_percentage_used(self) -> float:
        if self.budget_limit <= 0:
            return 100.0
        return (self.budget_used / self.budget_limit) * 100

    def _analyze_complexity(self, task: str, context: dict = None) -> TaskComplexity:
        """Analyze task complexity based on content."""
        task_lower = task.lower()
        context = context or {}

        # Complex indicators
        complex_indicators = [
            "architect", "design system", "complex", "critical",
            "security", "scalable", "enterprise", "production",
            "optimize", "refactor entire", "migration", "integration"
        ]

        # Simple indicators
        simple_indicators = [
            "fix typo", "rename", "simple", "basic", "quick",
            "format", "add comment", "update text", "minor"
        ]

        # Check for complexity indicators
        complex_score = sum(1 for ind in complex_indicators if ind in task_lower)
        simple_score = sum(1 for ind in simple_indicators if ind in task_lower)

        # Factor in context
        num_features = len(context.get("features", []))
        if num_features > 5:
            complex_score += 2
        elif num_features > 2:
            complex_score += 1

        # Make decision
        if simple_score > complex_score and complex_score == 0:
            return TaskComplexity.SIMPLE
        elif complex_score >= 2:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MEDIUM

    def _determine_task_type(self, agent_name: str, task: str) -> TaskType:
        """Determine task type based on agent and task content."""
        task_lower = task.lower()

        # Map agent to default task type
        agent_task_map = {
            "architect": TaskType.PLANNING,
            "mason": TaskType.CODING,
            "oracle": TaskType.REVIEW,
        }

        # Check for overrides based on task content
        if any(word in task_lower for word in ["review", "check", "verify", "audit"]):
            return TaskType.REVIEW
        if any(word in task_lower for word in ["plan", "design", "architect", "strategy"]):
            return TaskType.PLANNING
        if any(word in task_lower for word in ["implement", "code", "build", "create", "write"]):
            return TaskType.CODING
        if any(word in task_lower for word in ["analyze", "understand", "explain", "research"]):
            return TaskType.ANALYSIS

        return agent_task_map.get(agent_name, TaskType.ANALYSIS)

    def _select_best_model(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
    ) -> tuple[str, str]:
        """Select the best provider and model for the task."""

        # Budget exhausted - force Ollama
        if self.budget_remaining <= 0.01:
            return ("ollama", self.ollama_model)

        # Get required quality based on complexity
        min_quality = {
            TaskComplexity.SIMPLE: 0.65,
            TaskComplexity.MEDIUM: 0.80,
            TaskComplexity.COMPLEX: 0.90,
        }[complexity]

        # Collect eligible models
        candidates = []

        for provider, models in MODEL_REGISTRY.items():
            if provider not in self.available_providers:
                continue

            for model_name, specs in models.items():
                # Check if model can handle this task type
                if task_type.value not in specs["capabilities"] and task_type != TaskType.SIMPLE_QUERY:
                    continue

                # Check quality threshold
                if specs["quality"] < min_quality:
                    continue

                # Check budget (estimate 2K tokens)
                estimated_cost = specs["cost_per_1k"] * 2
                if estimated_cost > self.budget_remaining and provider != "ollama":
                    continue

                # Calculate score (balance quality vs cost)
                cost_factor = 1 - (specs["cost_per_1k"] / 0.05) if specs["cost_per_1k"] > 0 else 1.0
                quality_factor = specs["quality"]

                # Prefer local if flag set
                local_bonus = 0.1 if provider == "ollama" and self.prefer_local else 0

                score = (quality_factor * 0.6) + (cost_factor * 0.3) + local_bonus

                candidates.append({
                    "provider": provider,
                    "model": model_name,
                    "score": score,
                    "quality": specs["quality"],
                    "cost": specs["cost_per_1k"],
                })

        if not candidates:
            # Fallback to Ollama
            return ("ollama", self.ollama_model)

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        return (best["provider"], best["model"])

    def _get_fallback(self, primary_provider: str) -> tuple[Optional[str], Optional[str]]:
        """Get fallback provider and model."""
        # Always fallback to Ollama if available
        if "ollama" in self.available_providers and primary_provider != "ollama":
            return ("ollama", self.ollama_model)

        # Otherwise try a cheaper option
        fallback_order = ["ollama", "gemini", "openai", "anthropic"]
        for provider in fallback_order:
            if provider in self.available_providers and provider != primary_provider:
                models = MODEL_REGISTRY.get(provider, {})
                # Get cheapest model
                cheapest = min(models.items(), key=lambda x: x[1]["cost_per_1k"], default=None)
                if cheapest:
                    return (provider, cheapest[0])

        return (None, None)

    def _estimate_tokens(self, task: str, context: dict, task_type: TaskType) -> int:
        """Estimate token usage for a task."""
        # Base estimation
        input_tokens = len(task) // 4 + 500  # Task + system prompt

        # Add context
        for key, value in (context or {}).items():
            if isinstance(value, str):
                input_tokens += len(value) // 4
            elif isinstance(value, list):
                input_tokens += sum(len(str(v)) // 4 for v in value)

        # Output estimation based on task type
        output_multipliers = {
            TaskType.PLANNING: 1.5,
            TaskType.CODING: 2.0,
            TaskType.REVIEW: 0.8,
            TaskType.ANALYSIS: 1.2,
            TaskType.SIMPLE_QUERY: 0.5,
        }

        output_tokens = int(input_tokens * output_multipliers.get(task_type, 1.0))

        return input_tokens + output_tokens

    def route(
        self,
        task: str,
        agent_name: str = "general",
        context: dict = None,
    ) -> RoutingDecision:
        """Make a routing decision for a task.

        Args:
            task: The task description
            agent_name: Name of the agent (architect, mason, oracle)
            context: Task context (features, description, etc.)

        Returns:
            RoutingDecision with provider, model, and reasoning
        """
        context = context or {}

        # Analyze the task
        complexity = self._analyze_complexity(task, context)
        task_type = self._determine_task_type(agent_name, task)

        # Select best model
        provider, model = self._select_best_model(task_type, complexity)

        # Get fallback
        fallback_provider, fallback_model = self._get_fallback(provider)

        # Estimate tokens and cost
        estimated_tokens = self._estimate_tokens(task, context, task_type)
        model_specs = MODEL_REGISTRY.get(provider, {}).get(model, {"cost_per_1k": 0})
        estimated_cost = (estimated_tokens / 1000) * model_specs.get("cost_per_1k", 0)

        # Build reasoning
        reasoning_parts = []

        if self.budget_remaining <= 0.01:
            reasoning_parts.append("Budget exhausted - using free local model")
        elif self.budget_percentage_used > 80:
            reasoning_parts.append(f"Budget {self.budget_percentage_used:.0f}% used - preferring cost-effective option")

        reasoning_parts.append(f"Task complexity: {complexity.value}")
        reasoning_parts.append(f"Task type: {task_type.value} (agent: {agent_name})")
        reasoning_parts.append(f"Selected: {provider}/{model} (quality: {model_specs.get('quality', 'N/A')})")

        if provider == "ollama":
            reasoning_parts.append("Using local model - no API cost")
        else:
            reasoning_parts.append(f"Estimated cost: ${estimated_cost:.4f}")

        # Calculate confidence
        confidence = model_specs.get("quality", 0.7)
        if self.budget_remaining <= 0.01:
            confidence *= 0.8  # Lower confidence when forced to use fallback

        # Get integration recommendations if product type is known
        integrations = None
        product_type = context.get("project_type") or context.get("product_type")
        if product_type:
            integrations = self.recommend_integrations(product_type, task)

        return RoutingDecision(
            provider=provider,
            model=model,
            complexity=complexity,
            task_type=task_type,
            reasoning=" | ".join(reasoning_parts),
            estimated_tokens=estimated_tokens,
            estimated_cost=estimated_cost,
            confidence=confidence,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            integrations=integrations,
        )

    async def route_with_ollama(
        self,
        task: str,
        agent_name: str = "general",
        context: dict = None,
        ollama_client = None,
    ) -> RoutingDecision:
        """Make a routing decision using Ollama for analysis.

        This uses Ollama to actually analyze the task and make a smarter
        routing decision. Falls back to rule-based routing if Ollama fails.

        Args:
            task: The task description
            agent_name: Name of the agent
            context: Task context
            ollama_client: Ollama provider instance

        Returns:
            RoutingDecision
        """
        # If no Ollama client, use rule-based routing
        if not ollama_client:
            return self.route(task, agent_name, context)

        try:
            # Ask Ollama to analyze the task
            analysis_prompt = f"""Analyze this task and respond with JSON only:

Task: {task}
Agent: {agent_name}
Context: {json.dumps(context or {}, indent=2)[:500]}

Respond with this exact JSON format:
{{
    "complexity": "simple" | "medium" | "complex",
    "task_type": "planning" | "coding" | "review" | "analysis",
    "needs_premium": true | false,
    "reasoning": "brief explanation"
}}"""

            response = await ollama_client.generate(
                analysis_prompt,
                system_prompt="You are a task analyzer. Respond only with valid JSON.",
                temperature=0.1,
            )

            # Parse Ollama's analysis
            try:
                # Extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    analysis = json.loads(response[json_start:json_end])
                else:
                    raise ValueError("No JSON found")

                # Map analysis to complexity
                complexity_map = {
                    "simple": TaskComplexity.SIMPLE,
                    "medium": TaskComplexity.MEDIUM,
                    "complex": TaskComplexity.COMPLEX,
                }
                complexity = complexity_map.get(
                    analysis.get("complexity", "medium"),
                    TaskComplexity.MEDIUM
                )

                # Map to task type
                task_type_map = {
                    "planning": TaskType.PLANNING,
                    "coding": TaskType.CODING,
                    "review": TaskType.REVIEW,
                    "analysis": TaskType.ANALYSIS,
                }
                task_type = task_type_map.get(
                    analysis.get("task_type", "analysis"),
                    TaskType.ANALYSIS
                )

                # Override complexity if Ollama says premium needed
                if analysis.get("needs_premium") and complexity == TaskComplexity.SIMPLE:
                    complexity = TaskComplexity.MEDIUM

                # Now select model with this analysis
                provider, model = self._select_best_model(task_type, complexity)
                fallback_provider, fallback_model = self._get_fallback(provider)

                estimated_tokens = self._estimate_tokens(task, context, task_type)
                model_specs = MODEL_REGISTRY.get(provider, {}).get(model, {"cost_per_1k": 0})
                estimated_cost = (estimated_tokens / 1000) * model_specs.get("cost_per_1k", 0)

                reasoning = f"Ollama analysis: {analysis.get('reasoning', 'N/A')} | "
                reasoning += f"Complexity: {complexity.value} | Task: {task_type.value} | "
                reasoning += f"Selected: {provider}/{model}"

                return RoutingDecision(
                    provider=provider,
                    model=model,
                    complexity=complexity,
                    task_type=task_type,
                    reasoning=reasoning,
                    estimated_tokens=estimated_tokens,
                    estimated_cost=estimated_cost,
                    confidence=model_specs.get("quality", 0.8),
                    fallback_provider=fallback_provider,
                    fallback_model=fallback_model,
                )

            except (json.JSONDecodeError, KeyError, ValueError):
                # Ollama response wasn't valid JSON, fall back to rules
                pass

        except Exception:
            # Ollama failed, fall back to rule-based routing
            pass

        # Fallback to rule-based routing
        return self.route(task, agent_name, context)


    def recommend_integrations(
        self,
        product_type: str,
        description: str = "",
    ) -> IntegrationRecommendation:
        """Recommend integrations for a product type.

        Args:
            product_type: Type of product (planner, app_ios, book, etc.)
            description: Product description for additional context

        Returns:
            IntegrationRecommendation with suggested tools and platforms
        """
        # Get base recommendations from standards
        config = PRODUCT_INTEGRATIONS.get(product_type, {})

        design_tools = config.get("design", [])
        publish_platforms = config.get("publish", [])
        needs_cover = config.get("needs_cover", False)
        needs_icon = config.get("needs_icon", False)
        needs_docs = config.get("needs_docs", False)

        # Build reasoning
        reasoning_parts = []

        if needs_cover:
            reasoning_parts.append("Product needs a professional cover - recommend Canva")
        if needs_icon:
            reasoning_parts.append("Product needs app icons/graphics - recommend Canva/Figma")
        if needs_docs:
            reasoning_parts.append("Product needs documentation - ensure README is complete")

        if design_tools:
            reasoning_parts.append(f"Design with: {', '.join(design_tools)}")
        if publish_platforms:
            reasoning_parts.append(f"Publish to: {', '.join(publish_platforms)}")

        if not reasoning_parts:
            reasoning_parts.append("Standard code product - focus on quality and completeness")

        return IntegrationRecommendation(
            product_type=product_type,
            design_tools=design_tools,
            publish_platforms=publish_platforms,
            needs_cover=needs_cover,
            needs_icon=needs_icon,
            needs_docs=needs_docs,
            reasoning=" | ".join(reasoning_parts),
        )


# Singleton instance for easy access
_governor_instance: Optional[Governor] = None


def get_governor(
    available_providers: list[str] = None,
    budget_limit: float = 10.0,
    budget_used: float = 0.0,
    prefer_local: bool = False,
) -> Governor:
    """Get or create the Governor instance."""
    global _governor_instance

    if _governor_instance is None:
        _governor_instance = Governor(
            available_providers=available_providers,
            budget_limit=budget_limit,
            budget_used=budget_used,
            prefer_local=prefer_local,
        )
    else:
        # Update settings
        if available_providers:
            _governor_instance.available_providers = available_providers
        _governor_instance.budget_limit = budget_limit
        _governor_instance.budget_used = budget_used
        _governor_instance.prefer_local = prefer_local

    return _governor_instance
