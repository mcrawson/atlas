"""
ATLAS Training Data Collector

Collects agent interactions for fine-tuning local LLMs.
Goal: Build a dataset to train a local model that can replicate
cloud LLM behavior for ATLAS agent tasks.

Data Format (JSONL - compatible with most fine-tuning frameworks):
{
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "metadata": {
        "agent": "architect|mason|oracle",
        "task_type": "planning|coding|review",
        "complexity": "simple|medium|complex",
        "source_model": "gpt-4|claude-3-opus|...",
        "tokens": {"prompt": N, "completion": N},
        "quality_score": 0-1,
        "approved": true|false,
        "revision_count": N
    }
}
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class QualityLabel(Enum):
    """Quality labels for training data"""
    APPROVED = "approved"           # User approved without changes
    REVISED_ONCE = "revised_once"   # Needed one revision
    REVISED_MULTI = "revised_multi" # Needed multiple revisions
    REJECTED = "rejected"           # User rejected/abandoned
    UNKNOWN = "unknown"             # No feedback yet


@dataclass
class TrainingExample:
    """A single training example for fine-tuning"""
    # Core conversation
    system_prompt: str
    user_input: str
    assistant_output: str

    # Metadata for filtering/weighting
    agent: str  # architect, mason, oracle
    task_type: str  # planning, coding, review, analysis
    complexity: str  # simple, medium, complex
    source_model: str  # The model that generated this
    source_provider: str

    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Quality signals
    quality_label: str = "unknown"
    approved: bool = False
    revision_count: int = 0
    user_rating: Optional[int] = None  # 1-5 if provided

    # Identifiers
    project_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    example_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S_%f"))

    def to_training_format(self) -> Dict[str, Any]:
        """Convert to standard fine-tuning format (OpenAI/Anthropic compatible)"""
        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_input},
                {"role": "assistant", "content": self.assistant_output}
            ],
            "metadata": {
                "agent": self.agent,
                "task_type": self.task_type,
                "complexity": self.complexity,
                "source_model": self.source_model,
                "source_provider": self.source_provider,
                "tokens": {
                    "prompt": self.prompt_tokens,
                    "completion": self.completion_tokens,
                    "total": self.prompt_tokens + self.completion_tokens
                },
                "quality": {
                    "label": self.quality_label,
                    "approved": self.approved,
                    "revision_count": self.revision_count,
                    "user_rating": self.user_rating
                },
                "project_id": self.project_id,
                "timestamp": self.timestamp,
                "example_id": self.example_id
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TrainingStats:
    """Statistics about collected training data"""
    total_examples: int = 0
    by_agent: Dict[str, int] = field(default_factory=dict)
    by_complexity: Dict[str, int] = field(default_factory=dict)
    by_quality: Dict[str, int] = field(default_factory=dict)
    by_provider: Dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    approved_examples: int = 0
    approval_rate: float = 0.0
    avg_revisions: float = 0.0
    estimated_cloud_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TrainingCollector:
    """
    Collects and manages training data for local LLM fine-tuning.

    Usage:
        collector = TrainingCollector()

        # After each agent interaction
        collector.add_example(
            system_prompt="You are Sketch...",
            user_input="Build a REST API with auth",
            assistant_output="## Understanding\n...",
            agent="architect",
            task_type="planning",
            complexity="medium",
            source_model="gpt-4",
            source_provider="openai",
            prompt_tokens=500,
            completion_tokens=1200,
            project_id="proj_123"
        )

        # When user approves/rejects
        collector.update_quality("example_id", approved=True, revision_count=0)

        # Export for fine-tuning
        collector.export_training_set("training_data.jsonl", min_quality="approved")
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "training")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Main data files
        self.examples_file = self.data_dir / "examples.jsonl"
        self.stats_file = self.data_dir / "stats.json"

        # In-memory index for quick lookups
        self._example_index: Dict[str, int] = {}  # example_id -> line number
        self._load_index()

    def _load_index(self):
        """Load example index from disk"""
        if self.examples_file.exists():
            with open(self.examples_file, 'r') as f:
                for i, line in enumerate(f):
                    try:
                        data = json.loads(line)
                        example_id = data.get("metadata", {}).get("example_id", "")
                        if example_id:
                            self._example_index[example_id] = i
                    except json.JSONDecodeError:
                        continue

    def add_example(
        self,
        system_prompt: str,
        user_input: str,
        assistant_output: str,
        agent: str,
        task_type: str,
        complexity: str,
        source_model: str,
        source_provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        project_id: str = ""
    ) -> str:
        """
        Add a new training example.
        Returns the example_id for later quality updates.
        """
        example = TrainingExample(
            system_prompt=system_prompt,
            user_input=user_input,
            assistant_output=assistant_output,
            agent=agent,
            task_type=task_type,
            complexity=complexity,
            source_model=source_model,
            source_provider=source_provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            project_id=project_id
        )

        # Append to JSONL file
        with open(self.examples_file, 'a') as f:
            f.write(json.dumps(example.to_training_format()) + "\n")

        # Update index
        self._example_index[example.example_id] = len(self._example_index)

        return example.example_id

    def update_quality(
        self,
        example_id: str,
        approved: bool = False,
        revision_count: int = 0,
        user_rating: Optional[int] = None
    ):
        """
        Update quality labels for an example after user feedback.
        Note: This requires rewriting the file (expensive for large datasets).
        For production, consider using a database instead.
        """
        if example_id not in self._example_index:
            return

        # Determine quality label
        if approved:
            if revision_count == 0:
                quality_label = QualityLabel.APPROVED.value
            elif revision_count == 1:
                quality_label = QualityLabel.REVISED_ONCE.value
            else:
                quality_label = QualityLabel.REVISED_MULTI.value
        else:
            quality_label = QualityLabel.REJECTED.value

        # Read all examples
        examples = []
        if self.examples_file.exists():
            with open(self.examples_file, 'r') as f:
                for line in f:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Update the specific example
        line_num = self._example_index[example_id]
        if line_num < len(examples):
            examples[line_num]["metadata"]["quality"]["label"] = quality_label
            examples[line_num]["metadata"]["quality"]["approved"] = approved
            examples[line_num]["metadata"]["quality"]["revision_count"] = revision_count
            if user_rating is not None:
                examples[line_num]["metadata"]["quality"]["user_rating"] = user_rating

        # Write back
        with open(self.examples_file, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")

    def get_stats(self) -> TrainingStats:
        """Calculate statistics about collected training data"""
        stats = TrainingStats()

        if not self.examples_file.exists():
            return stats

        total_revisions = 0

        with open(self.examples_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    meta = data.get("metadata", {})
                    quality = meta.get("quality", {})
                    tokens = meta.get("tokens", {})

                    stats.total_examples += 1

                    # By agent
                    agent = meta.get("agent", "unknown")
                    stats.by_agent[agent] = stats.by_agent.get(agent, 0) + 1

                    # By complexity
                    complexity = meta.get("complexity", "unknown")
                    stats.by_complexity[complexity] = stats.by_complexity.get(complexity, 0) + 1

                    # By quality
                    quality_label = quality.get("label", "unknown")
                    stats.by_quality[quality_label] = stats.by_quality.get(quality_label, 0) + 1

                    # By provider
                    provider = meta.get("source_provider", "unknown")
                    stats.by_provider[provider] = stats.by_provider.get(provider, 0) + 1

                    # Tokens
                    stats.total_tokens += tokens.get("total", 0)

                    # Approved count
                    if quality.get("approved", False):
                        stats.approved_examples += 1

                    # Revision count
                    total_revisions += quality.get("revision_count", 0)

                except json.JSONDecodeError:
                    continue

        # Calculate rates
        if stats.total_examples > 0:
            stats.approval_rate = stats.approved_examples / stats.total_examples
            stats.avg_revisions = total_revisions / stats.total_examples
            # Rough cost estimate ($0.00001 per token average)
            stats.estimated_cloud_cost = stats.total_tokens * 0.00001

        return stats

    def export_training_set(
        self,
        output_file: str,
        min_quality: str = "approved",
        agents: Optional[List[str]] = None,
        complexity: Optional[List[str]] = None,
        max_examples: Optional[int] = None
    ) -> int:
        """
        Export filtered training data for fine-tuning.

        Args:
            output_file: Path to output JSONL file
            min_quality: Minimum quality level ("approved", "revised_once", "revised_multi", "all")
            agents: Filter by agent names (None = all)
            complexity: Filter by complexity levels (None = all)
            max_examples: Maximum number of examples to export

        Returns:
            Number of examples exported
        """
        quality_hierarchy = ["approved", "revised_once", "revised_multi", "rejected", "unknown"]
        min_quality_idx = quality_hierarchy.index(min_quality) if min_quality in quality_hierarchy else len(quality_hierarchy)

        exported = 0
        output_path = Path(output_file)

        with open(self.examples_file, 'r') as f_in, open(output_path, 'w') as f_out:
            for line in f_in:
                if max_examples and exported >= max_examples:
                    break

                try:
                    data = json.loads(line)
                    meta = data.get("metadata", {})
                    quality = meta.get("quality", {})

                    # Filter by quality
                    quality_label = quality.get("label", "unknown")
                    if min_quality != "all":
                        quality_idx = quality_hierarchy.index(quality_label) if quality_label in quality_hierarchy else len(quality_hierarchy)
                        if quality_idx > min_quality_idx:
                            continue

                    # Filter by agent
                    if agents and meta.get("agent") not in agents:
                        continue

                    # Filter by complexity
                    if complexity and meta.get("complexity") not in complexity:
                        continue

                    # Write (just the messages for training, optionally include metadata)
                    f_out.write(json.dumps(data) + "\n")
                    exported += 1

                except json.JSONDecodeError:
                    continue

        return exported

    def export_for_ollama(self, output_file: str, model_name: str = "atlas-agent") -> int:
        """
        Export in Ollama Modelfile format for creating a custom model.

        Creates a Modelfile that can be used with:
            ollama create atlas-agent -f Modelfile
        """
        stats = self.get_stats()

        # Get the most common system prompts by agent
        system_prompts = {}

        with open(self.examples_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    messages = data.get("messages", [])
                    meta = data.get("metadata", {})
                    agent = meta.get("agent", "unknown")

                    for msg in messages:
                        if msg.get("role") == "system":
                            system_prompts[agent] = msg.get("content", "")
                            break
                except json.JSONDecodeError:
                    continue

        # Create Modelfile
        modelfile_content = f"""# ATLAS Agent Model
# Generated from {stats.total_examples} training examples
# Approval rate: {stats.approval_rate:.1%}

FROM llama3

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

SYSTEM \"\"\"
You are ATLAS, a multi-agent AI system with three specialized personas:

1. THE ARCHITECT (📐): Strategic planner who analyzes tasks, identifies risks,
   and creates detailed implementation plans.

2. THE MASON (🔨): Master builder who implements code based on the Architect's
   plans with clean, efficient, well-documented code.

3. THE ORACLE (🔮): Quality guardian who verifies implementations, runs tests,
   and ensures everything meets requirements.

Respond based on which agent role you're asked to embody.
\"\"\"
"""

        with open(output_file, 'w') as f:
            f.write(modelfile_content)

        return stats.total_examples

    def get_cost_savings_potential(self) -> Dict[str, Any]:
        """
        Calculate potential cost savings from using local models.
        """
        stats = self.get_stats()

        # Current cloud costs (rough estimates per 1K tokens)
        cloud_costs = {
            "openai": {"gpt-4": 0.03, "gpt-3.5-turbo": 0.002},
            "anthropic": {"claude-3-opus": 0.015, "claude-3-sonnet": 0.003, "claude-3-haiku": 0.00025},
            "gemini": {"gemini-1.5-pro": 0.00125, "gemini-1.5-flash": 0.000075}
        }

        # Local cost (electricity + depreciation, roughly $0.0001 per 1K tokens)
        local_cost_per_1k = 0.0001

        # Calculate current spend by provider
        provider_costs = {}
        total_cloud_cost = 0

        if self.examples_file.exists():
            with open(self.examples_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        meta = data.get("metadata", {})
                        tokens = meta.get("tokens", {}).get("total", 0)
                        provider = meta.get("source_provider", "unknown")
                        model = meta.get("source_model", "unknown")

                        # Get cost rate
                        cost_rate = cloud_costs.get(provider, {}).get(model, 0.01)  # Default $0.01/1K
                        cost = (tokens / 1000) * cost_rate

                        provider_costs[provider] = provider_costs.get(provider, 0) + cost
                        total_cloud_cost += cost

                    except json.JSONDecodeError:
                        continue

        # Calculate local alternative cost
        local_cost = (stats.total_tokens / 1000) * local_cost_per_1k

        return {
            "total_tokens": stats.total_tokens,
            "cloud_cost": total_cloud_cost,
            "cloud_cost_by_provider": provider_costs,
            "local_cost_estimate": local_cost,
            "potential_savings": total_cloud_cost - local_cost,
            "savings_percentage": ((total_cloud_cost - local_cost) / total_cloud_cost * 100) if total_cloud_cost > 0 else 0,
            "examples_collected": stats.total_examples,
            "ready_for_training": stats.total_examples >= 100,  # Minimum for reasonable fine-tuning
            "recommendation": self._get_training_recommendation(stats)
        }

    def _get_training_recommendation(self, stats: TrainingStats) -> str:
        """Get recommendation based on current data"""
        if stats.total_examples < 50:
            return f"Collect more data. You have {stats.total_examples} examples, need at least 50 for basic fine-tuning."
        elif stats.total_examples < 100:
            return f"Almost ready! {stats.total_examples} examples collected. 100+ recommended for good results."
        elif stats.approval_rate < 0.7:
            return f"Quality needs improvement. {stats.approval_rate:.0%} approval rate. Aim for 70%+."
        elif stats.total_examples < 500:
            return f"Ready for initial fine-tuning with {stats.total_examples} examples. More data will improve quality."
        else:
            return f"Excellent! {stats.total_examples} high-quality examples ready for fine-tuning."


# Singleton instance
_collector: Optional[TrainingCollector] = None


def get_collector() -> TrainingCollector:
    """Get the global training collector instance"""
    global _collector
    if _collector is None:
        _collector = TrainingCollector()
    return _collector
