"""Cortex - Training Data Intelligence.

The brain of your training system. Understands your data, tracks your progress,
assesses readiness, and guides you to training your own local AI model.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("atlas.agents.cortex")


@dataclass
class CortexConfig:
    """Configuration for Cortex."""
    min_examples_for_training: int = 100
    optimal_examples: int = 500
    min_approval_rate: float = 0.7


class Cortex:
    """ATLAS Training Data Intelligence.

    The brain of your training system. Understands your data, tracks your progress,
    assesses readiness, and guides you to training your own local AI model.

    Responsibilities:
    - Analyze training data quality and coverage
    - Provide readiness assessments
    - Guide fine-tuning process
    - Recommend data collection strategies
    - Help with local model deployment (Ollama)
    """

    NAME = "Cortex"
    ICON = "🧠"
    DESCRIPTION = "Training data intelligence"
    COLOR = "#22d3ee"  # Cyan - clarity/intelligence

    def __init__(self, config: Optional[CortexConfig] = None):
        """Initialize Cortex.

        Args:
            config: Training configuration
        """
        self.config = config or CortexConfig()

    def get_system_prompt(self) -> str:
        """Get Cortex's system prompt for chat interactions."""
        return """You are Cortex, the training data intelligence within ATLAS.

PERSONALITY:
- Analytical mind that sees patterns in data
- Clear communicator who explains complex concepts simply
- Precise and accurate in assessments
- Calm and measured, focused on facts and insights

YOUR ROLE:
You help users understand their training data, assess readiness for fine-tuning,
and guide them through creating their own local AI model. You have access to
their training statistics and can provide specific insights.

KEY KNOWLEDGE AREAS:
1. **Training Data Quality**
   - Diversity of examples across agents (Sketch, Tinker, Oracle)
   - Balance of simple vs complex tasks
   - Approval rates and what they mean
   - Token distribution and coverage

2. **Fine-tuning Readiness**
   - Minimum viable dataset (~100 examples)
   - Optimal dataset size (~500+ examples)
   - Quality thresholds (>70% approval rate)
   - Data export and formatting (JSONL, chat format)

3. **Local Model Deployment**
   - Ollama setup and configuration
   - Model selection (Llama, Mistral, etc.)
   - Fine-tuning with tools like MLX, llama.cpp
   - VRAM requirements and optimization

4. **Cost Savings**
   - Calculate potential savings from local inference
   - Compare cloud API costs vs local hardware
   - ROI projections based on usage patterns

CONVERSATION STYLE:
- Start by understanding what the user wants to know
- Reference their actual training stats when available
- Give specific, data-driven insights
- Be precise about metrics and thresholds
- Present clear assessments with reasoning

EXAMPLE TOPICS:
- "How's my training data looking?"
- "Am I ready to start fine-tuning?"
- "What kind of examples should I focus on collecting?"
- "How do I export my data for training?"
- "What local model should I use?"
- "How much could I save with a local model?"

Remember: Your goal is to help users understand their data and guide them to
training their own AI assistant, running entirely on their own hardware."""

    def analyze_readiness(self, stats: dict) -> dict:
        """Analyze training readiness based on current stats.

        Args:
            stats: Training statistics dict

        Returns:
            Analysis with score, status, and recommendations
        """
        total = stats.get("total_examples", 0)
        approval_rate = stats.get("approval_rate", 0)
        by_agent = stats.get("by_agent", {})

        # Calculate readiness score (0-100)
        score = 0
        recommendations = []
        blockers = []

        # Quantity score (40 points max)
        if total >= self.config.optimal_examples:
            score += 40
        elif total >= self.config.min_examples_for_training:
            score += int(20 + (total - 100) / 20)  # 20-40 range
        elif total >= 50:
            score += int(total / 5)  # 10-20 range
        else:
            score += int(total / 5)
            blockers.append(f"Need at least {self.config.min_examples_for_training} examples (currently {total})")

        # Quality score (30 points max)
        if approval_rate >= 0.9:
            score += 30
        elif approval_rate >= self.config.min_approval_rate:
            score += int(15 + (approval_rate - 0.7) * 75)  # 15-30 range
        elif approval_rate >= 0.5:
            score += int(approval_rate * 30)
            recommendations.append("Try to improve approval rate above 70%")
        else:
            score += int(approval_rate * 20)
            blockers.append(f"Approval rate too low ({approval_rate:.0%}). Aim for >70%")

        # Diversity score (30 points max)
        agents_with_data = sum(1 for v in by_agent.values() if v > 10)
        if agents_with_data >= 3:
            score += 30
        elif agents_with_data >= 2:
            score += 20
            recommendations.append("Collect more examples from all three core agents")
        elif agents_with_data >= 1:
            score += 10
            recommendations.append("Your data is concentrated in one agent - diversify!")
        else:
            blockers.append("Need examples from multiple agents")

        # Determine status
        if blockers:
            status = "not_ready"
            status_text = "Not Ready"
        elif score >= 80:
            status = "ready"
            status_text = "Ready for Training"
        elif score >= 60:
            status = "almost_ready"
            status_text = "Almost Ready"
        else:
            status = "collecting"
            status_text = "Keep Collecting"

        # Add positive recommendations if doing well
        if not recommendations and not blockers:
            if score >= 90:
                recommendations.append("Excellent dataset. You're ready to train your model.")
            elif score >= 80:
                recommendations.append("Strong dataset. Consider collecting a few more complex examples.")

        return {
            "score": min(score, 100),
            "status": status,
            "status_text": status_text,
            "blockers": blockers,
            "recommendations": recommendations,
            "stats_summary": {
                "total_examples": total,
                "approval_rate": approval_rate,
                "agents_coverage": agents_with_data,
            }
        }

    def estimate_savings(self, stats: dict, monthly_tokens: int = 1000000) -> dict:
        """Estimate potential cost savings from local model.

        Args:
            stats: Training statistics
            monthly_tokens: Estimated monthly token usage

        Returns:
            Savings estimate dict
        """
        # Approximate cloud costs (blended rate)
        cloud_cost_per_1k = 0.01  # $0.01 per 1K tokens average

        monthly_cloud_cost = (monthly_tokens / 1000) * cloud_cost_per_1k
        yearly_cloud_cost = monthly_cloud_cost * 12

        # Local costs (electricity + hardware amortization)
        # Assuming ~$0.001 per 1K tokens for electricity on consumer GPU
        local_cost_per_1k = 0.001
        monthly_local_cost = (monthly_tokens / 1000) * local_cost_per_1k

        monthly_savings = monthly_cloud_cost - monthly_local_cost
        yearly_savings = monthly_savings * 12

        return {
            "monthly_cloud_cost": monthly_cloud_cost,
            "monthly_local_cost": monthly_local_cost,
            "monthly_savings": monthly_savings,
            "yearly_savings": yearly_savings,
            "savings_percentage": (monthly_savings / monthly_cloud_cost * 100) if monthly_cloud_cost > 0 else 0,
            "break_even_months": 0,  # Assuming existing hardware
        }


# Singleton instance
_cortex: Optional[Cortex] = None


def get_cortex() -> Cortex:
    """Get or create the global Cortex instance."""
    global _cortex
    if _cortex is None:
        _cortex = Cortex()
    return _cortex
