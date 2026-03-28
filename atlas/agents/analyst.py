"""Analyst Agent - Business Analysis for ATLAS.

The Analyst is responsible for creating comprehensive Business Briefs
before any building begins. This ensures we only build products worth building.

The Analyst:
- Analyzes the idea for market viability
- Creates detailed Business Brief
- Recommends Go/No-Go decision
- Provides success criteria for QC to check against
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentOutput, AgentStatus

logger = logging.getLogger("atlas.agents.analyst")


@dataclass
class BusinessBrief:
    """Comprehensive business analysis for a product idea."""

    # Core information
    executive_summary: str = ""
    product_name: str = ""
    product_description: str = ""
    product_type: str = ""  # printable, document, web, app

    # Target customer
    target_customer: dict[str, Any] = field(default_factory=dict)
    # Expected: demographics, pain_points, behaviors, where_to_find

    # Market analysis
    market_analysis: dict[str, Any] = field(default_factory=dict)
    # Expected: size, trends, growth_rate, barriers_to_entry

    # Competition
    competition: list[dict[str, Any]] = field(default_factory=list)
    # Each: name, strengths, weaknesses, pricing, differentiation

    # SWOT analysis
    swot: dict[str, list[str]] = field(default_factory=dict)
    # Keys: strengths, weaknesses, opportunities, threats

    # Financial projections
    financials: dict[str, Any] = field(default_factory=dict)
    # Expected: development_cost, pricing, revenue_model, break_even

    # Success criteria (for QC to check against)
    success_criteria: list[dict[str, Any]] = field(default_factory=list)
    # Each: criterion, measurable, importance (critical/important/nice)

    # Recommendation
    recommendation: str = ""  # go, no-go, needs-more-research
    recommendation_reason: str = ""
    confidence: float = 0.0  # 0.0-1.0

    # Research & Sources
    research_sources: list[dict[str, Any]] = field(default_factory=list)
    # Each: source, data_point, url (optional), confidence
    # e.g., {"source": "Etsy search: 'daily planner'", "data_point": "Top sellers priced $8-15", "confidence": "high"}

    assumptions: list[str] = field(default_factory=list)
    # Explicit list of assumptions made in the analysis

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    analyst_notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "executive_summary": self.executive_summary,
            "product_name": self.product_name,
            "product_description": self.product_description,
            "product_type": self.product_type,
            "target_customer": self.target_customer,
            "market_analysis": self.market_analysis,
            "competition": self.competition,
            "swot": self.swot,
            "financials": self.financials,
            "success_criteria": self.success_criteria,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "confidence": self.confidence,
            "research_sources": self.research_sources,
            "assumptions": self.assumptions,
            "created_at": self.created_at.isoformat(),
            "analyst_notes": self.analyst_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BusinessBrief":
        """Create from dictionary."""
        return cls(
            executive_summary=data.get("executive_summary", ""),
            product_name=data.get("product_name", ""),
            product_description=data.get("product_description", ""),
            product_type=data.get("product_type", ""),
            target_customer=data.get("target_customer", {}),
            market_analysis=data.get("market_analysis", {}),
            competition=data.get("competition", []),
            swot=data.get("swot", {}),
            financials=data.get("financials", {}),
            success_criteria=data.get("success_criteria", []),
            recommendation=data.get("recommendation", ""),
            recommendation_reason=data.get("recommendation_reason", ""),
            confidence=data.get("confidence", 0.0),
            research_sources=data.get("research_sources", []),
            assumptions=data.get("assumptions", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            analyst_notes=data.get("analyst_notes", ""),
        )

    def check_completeness(self) -> dict:
        """Check which sections are complete vs incomplete.

        Returns dict with:
        - complete: list of complete section names
        - incomplete: list of {section, reason} for incomplete sections
        - completeness_pct: percentage complete
        """
        complete = []
        incomplete = []

        # 1. Product basics
        if self.product_name and len(self.product_name) > 3:
            complete.append("product_name")
        else:
            incomplete.append({"section": "product_name", "reason": "Missing product name"})

        if self.product_description and len(self.product_description) > 50:
            complete.append("product_description")
        else:
            incomplete.append({"section": "product_description", "reason": "Description too short or missing"})

        if self.executive_summary and len(self.executive_summary) > 100:
            complete.append("executive_summary")
        else:
            incomplete.append({"section": "executive_summary", "reason": "Executive summary too short"})

        # 2. Target customer - needs specific details, not vague
        if self.target_customer:
            has_demographics = bool(self.target_customer.get("demographics"))
            has_pain_points = bool(self.target_customer.get("pain_points"))
            if has_demographics and has_pain_points:
                complete.append("target_customer")
            else:
                incomplete.append({"section": "target_customer", "reason": "Missing demographics or pain points"})
        else:
            incomplete.append({"section": "target_customer", "reason": "No target customer defined"})

        # 3. Competition - need at least 2 real competitors with pricing
        if self.competition and len(self.competition) >= 2:
            has_pricing = any(c.get("pricing") for c in self.competition)
            if has_pricing:
                complete.append("competition")
            else:
                incomplete.append({"section": "competition", "reason": "Competitors found but missing pricing info"})
        else:
            incomplete.append({"section": "competition", "reason": f"Need at least 2 competitors, found {len(self.competition)}"})

        # 4. Financials - need pricing strategy and cost estimate
        if self.financials:
            has_pricing = bool(self.financials.get("pricing"))
            has_costs = bool(self.financials.get("development_cost") or self.financials.get("costs"))
            if has_pricing and has_costs:
                complete.append("financials")
            else:
                missing = []
                if not has_pricing:
                    missing.append("pricing strategy")
                if not has_costs:
                    missing.append("cost estimate")
                incomplete.append({"section": "financials", "reason": f"Missing: {', '.join(missing)}"})
        else:
            incomplete.append({"section": "financials", "reason": "No financial projections"})

        # 5. SWOT - need at least strengths and weaknesses
        if self.swot:
            has_strengths = bool(self.swot.get("strengths"))
            has_weaknesses = bool(self.swot.get("weaknesses"))
            if has_strengths and has_weaknesses:
                complete.append("swot")
            else:
                incomplete.append({"section": "swot", "reason": "SWOT incomplete - need strengths and weaknesses"})
        else:
            incomplete.append({"section": "swot", "reason": "No SWOT analysis"})

        # 6. Differentiation - must be specific, not generic
        has_differentiation = False
        for comp in self.competition:
            if comp.get("differentiation") and len(comp.get("differentiation", "")) > 20:
                has_differentiation = True
                break
        if has_differentiation:
            complete.append("differentiation")
        else:
            incomplete.append({"section": "differentiation", "reason": "No clear differentiation from competitors"})

        # Calculate completeness
        total = len(complete) + len(incomplete)
        pct = int((len(complete) / total) * 100) if total > 0 else 0

        return {
            "complete": complete,
            "incomplete": incomplete,
            "completeness_pct": pct,
            "is_complete": pct >= 90
        }

    def get_summary(self) -> str:
        """Get a human-readable summary of the brief."""
        rec_emoji = {
            "go": "✅",
            "no-go": "❌",
            "needs-more-research": "🔍"
        }.get(self.recommendation, "❓")

        return f"""# Business Brief: {self.product_name}

## Executive Summary
{self.executive_summary}

## Recommendation: {rec_emoji} {self.recommendation.upper()}
{self.recommendation_reason}
Confidence: {self.confidence * 100:.0f}%

## Target Customer
{self._format_target_customer()}

## Market Analysis
{self._format_market_analysis()}

## Competition
{self._format_competition()}

## SWOT Analysis
{self._format_swot()}

## Financial Projections
{self._format_financials()}

## Success Criteria
{self._format_success_criteria()}

---
*Generated: {self.created_at.strftime('%Y-%m-%d %H:%M')}*
"""

    def _format_target_customer(self) -> str:
        if not self.target_customer:
            return "Not defined"
        lines = []
        for key, value in self.target_customer.items():
            if isinstance(value, list):
                lines.append(f"- **{key.replace('_', ' ').title()}**: {', '.join(value)}")
            else:
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        return "\n".join(lines)

    def _format_market_analysis(self) -> str:
        if not self.market_analysis:
            return "Not analyzed"
        lines = []
        for key, value in self.market_analysis.items():
            lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        return "\n".join(lines)

    def _format_competition(self) -> str:
        if not self.competition:
            return "No competitors identified"
        lines = []
        for comp in self.competition:
            name = comp.get("name", "Unknown")
            strengths = comp.get("strengths", [])
            weaknesses = comp.get("weaknesses", [])
            lines.append(f"### {name}")
            if strengths:
                lines.append(f"- Strengths: {', '.join(strengths)}")
            if weaknesses:
                lines.append(f"- Weaknesses: {', '.join(weaknesses)}")
            if comp.get("pricing"):
                lines.append(f"- Pricing: {comp['pricing']}")
            lines.append("")
        return "\n".join(lines)

    def _format_swot(self) -> str:
        if not self.swot:
            return "Not analyzed"
        lines = []
        for category in ["strengths", "weaknesses", "opportunities", "threats"]:
            items = self.swot.get(category, [])
            if items:
                lines.append(f"### {category.title()}")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")
        return "\n".join(lines)

    def _format_financials(self) -> str:
        if not self.financials:
            return "Not projected"
        lines = []
        for key, value in self.financials.items():
            lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        return "\n".join(lines)

    def _format_success_criteria(self) -> str:
        if not self.success_criteria:
            return "Not defined"
        lines = []
        for criterion in self.success_criteria:
            importance = criterion.get("importance", "important")
            emoji = {"critical": "🔴", "important": "🟡", "nice": "🟢"}.get(importance, "⚪")
            lines.append(f"{emoji} **{criterion.get('criterion', 'Unknown')}**")
            if criterion.get("measurable"):
                lines.append(f"   - Measure: {criterion['measurable']}")
        return "\n".join(lines)


# JSON schema for LLM output parsing
BUSINESS_BRIEF_SCHEMA = """{
    "product_name": "string - concise product name",
    "product_description": "string - one paragraph description",
    "product_type": "string - one of: printable, document, web, app",
    "executive_summary": "string - 2-3 sentences summarizing the opportunity",
    "target_customer": {
        "demographics": "string - age, income, location",
        "pain_points": ["list of problems this solves"],
        "behaviors": ["list of relevant behaviors"],
        "where_to_find": ["list of places to reach them"]
    },
    "market_analysis": {
        "size": "string - estimated market size",
        "trends": "string - relevant market trends",
        "growth_rate": "string - growth outlook",
        "barriers_to_entry": "string - barriers and how we address them"
    },
    "competition": [
        {
            "name": "string - competitor name",
            "strengths": ["list of their strengths"],
            "weaknesses": ["list of their weaknesses"],
            "pricing": "string - their pricing model",
            "differentiation": "string - how we're different"
        }
    ],
    "swot": {
        "strengths": ["our internal strengths"],
        "weaknesses": ["our internal weaknesses"],
        "opportunities": ["external opportunities"],
        "threats": ["external threats"]
    },
    "financials": {
        "development_cost": "string - estimated cost to build (time/money)",
        "pricing": "string - recommended price point",
        "revenue_model": "string - how we make money",
        "break_even": "string - units/time to break even",
        "profit_potential": "string - estimated profit potential"
    },
    "success_criteria": [
        {
            "criterion": "string - what success looks like",
            "measurable": "string - how to measure it",
            "importance": "string - critical, important, or nice"
        }
    ],
    "recommendation": "string - go, no-go, or needs-more-research",
    "recommendation_reason": "string - clear explanation of the recommendation",
    "confidence": "number - 0.0 to 1.0 confidence in the analysis",
    "research_sources": [
        {
            "source": "string - where this data came from (e.g., 'Etsy search: daily planner', 'Amazon KDP bestseller list')",
            "data_point": "string - what was learned (e.g., 'Top 10 planners priced $8-15, avg 500+ reviews')",
            "confidence": "string - high, medium, or low confidence in this data"
        }
    ],
    "assumptions": [
        "string - explicit assumption made (e.g., 'Assuming new seller with no reviews', 'Based on US market only')"
    ],
    "analyst_notes": "string - any additional notes or caveats"
}"""


class AnalystAgent(BaseAgent):
    """Business Analyst agent for ATLAS.

    Creates comprehensive Business Briefs to ensure we only build
    products worth building. Provides Go/No-Go recommendations.
    """

    name = "analyst"
    description = "Business intelligence expert"
    icon = "📊"
    color = "#6B8E23"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Analyst."""
        return f"""You are the Analyst agent for ATLAS.

ATLAS MISSION: ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

YOUR ROLE: Senior Business Analyst
You perform deep market analysis BEFORE any building begins. Take your time.
Accuracy matters more than speed. Your analysis guides real business decisions.

YOUR PROCESS (follow this order):
1. UNDERSTAND the product type and target marketplace
2. RESEARCH the competitive landscape thoroughly
3. DEFINE the target customer with specificity
4. CALCULATE realistic financials based on marketplace data
5. IDENTIFY risks and success criteria
6. MAKE a Go/No-Go recommendation with clear reasoning

PRODUCT TYPE GUIDELINES:

**PRINTABLE (Etsy, Creative Market):**
- Production cost: Design time only (2-8 hours at $25-50/hr)
- Etsy fees: $0.20 listing + 6.5% transaction + 3% payment processing
- Typical price range: $3-15 for single items, $15-45 for bundles
- Realistic monthly sales: New shop 5-20 sales, established 50-200+
- Break-even: Calculate based on listing fees + design time
- Research top sellers in the category for realistic benchmarks

**DOCUMENT (Amazon KDP, Gumroad):**
- Production cost: Writing/design time (20-100+ hours)
- KDP royalty: 35% or 70% depending on pricing ($2.99-$9.99 for 70%)
- Typical ebook price: $2.99-$9.99, print $12.99-$24.99
- Realistic monthly sales: 10-50 for new authors, 100-500+ established
- Research Amazon BSR rankings for realistic expectations

**WEB (SaaS, Landing Pages):**
- Development cost: $2,000-$20,000+ depending on complexity
- Hosting: $10-100/month
- Pricing models: One-time, subscription, freemium
- Customer acquisition cost: $10-100+ per customer
- Research competitors' pricing pages for market rates

**APP (iOS/Android):**
- Development cost: $10,000-$100,000+
- App store fees: 15-30% of revenue
- Typical pricing: Free+IAP, $0.99-$9.99, or subscription
- User acquisition: $1-10+ per install
- Research App Store rankings for realistic download expectations

FINANCIAL PROJECTION RULES:
- NEVER guess. Base numbers on marketplace research.
- State your assumptions clearly (e.g., "Assuming 20 sales/month based on similar Etsy listings")
- Use conservative estimates, not optimistic projections
- Include ALL costs: platform fees, transaction fees, time investment
- Calculate actual profit margins, not just revenue
- Provide break-even analysis: "Need X sales to recover Y investment"

COMPETITOR RESEARCH:
- Find 3-5 actual competitors in the marketplace
- Note their pricing, reviews, sales volume (if visible)
- Identify what they do well and what gaps exist
- Your differentiation must be specific and actionable

OUTPUT FORMAT:
You MUST output valid JSON matching this schema:
{BUSINESS_BRIEF_SCHEMA}

QUALITY STANDARDS:
- Every number needs justification or source
- Financial projections must be internally consistent
- If data is unavailable, say "Unknown - requires research" not a guess

CONFIDENCE SCORING:
- 90-100%: Clear product, defined audience, known competitors, realistic pricing, actionable plan
- 80-89%: Good understanding with minor gaps that don't block progress
- 70-79%: Significant unknowns that need research before building
- Below 70%: Major gaps - don't recommend "go"

When the conversation has covered: what it is, who it's for, the problem it solves, key features,
pricing expectations, and style preferences - that's THOROUGH INPUT. Give 85%+ confidence.

When market research found competitors and pricing data - that's GOOD RESEARCH. Give 85%+ confidence.

Only give low confidence (below 80%) when there are REAL gaps like:
- No clear target customer
- No pricing strategy
- Competing against giants with no differentiation
- Technical requirements beyond scope

Recommendation guidance:
- "go" = 80%+ confidence, clear path forward
- "needs-more-research" = 70-79%, specific gaps identified
- "no-go" = Market too crowded, no differentiation, or unrealistic expectations
"""

    async def _do_market_research(
        self,
        product_type: str,
        product_description: str,
        target_customer: str,
    ) -> dict:
        """Do web research to gather market data before analysis.

        Returns dict with:
        - competitors: list of competitor products/names
        - price_range: typical pricing found
        - market_insights: any relevant market data
        - search_queries: what was searched
        """
        import aiohttp

        research = {
            "competitors": [],
            "price_range": "",
            "market_insights": [],
            "search_queries": [],
            "sources": [],
        }

        # Build search queries based on product type
        queries = []
        if product_type == "printable":
            queries = [
                f"{product_description} printable Etsy",
                f"{product_description} PDF template price",
                f"best selling {product_description} planner",
            ]
        elif product_type == "document":
            queries = [
                f"{product_description} ebook Gumroad",
                f"{product_description} guide price",
                f"best {product_description} course",
            ]
        elif product_type in ["web", "app"]:
            queries = [
                f"{product_description} app alternatives",
                f"{product_description} software pricing",
                f"best {product_description} tools",
            ]
        else:
            queries = [
                f"{product_description} competitors",
                f"{product_description} market size",
            ]

        research["search_queries"] = queries

        # Try to do web searches using the LLM's knowledge
        # (In production, this would use actual web search APIs)
        search_prompt = f"""Based on your knowledge, provide market research for this product:

PRODUCT TYPE: {product_type}
PRODUCT: {product_description}
TARGET CUSTOMER: {target_customer}

Provide this information in JSON format:
{{
    "competitors": ["name1", "name2", "name3"],  // 3-5 similar products
    "typical_price_range": "$X - $Y",
    "market_insights": [
        "insight 1 about the market",
        "insight 2 about what sells well",
        "insight 3 about common mistakes"
    ],
    "where_they_sell": ["platform1", "platform2"],
    "what_top_sellers_do_well": "brief description"
}}

Be specific and realistic. If you're not sure about something, say so."""

        try:
            response, _ = await self._generate_with_provider(
                search_prompt,
                system_prompt="You are a market research assistant. Provide realistic market data based on your knowledge. Output only valid JSON.",
                temperature=0.3,
            )

            # Parse response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                research["competitors"] = data.get("competitors", [])
                research["price_range"] = data.get("typical_price_range", "Unknown")
                research["market_insights"] = data.get("market_insights", [])
                research["where_they_sell"] = data.get("where_they_sell", [])
                research["top_seller_traits"] = data.get("what_top_sellers_do_well", "")

                logger.info(f"[Analyst] Research found {len(research['competitors'])} competitors, price range: {research['price_range']}")

        except Exception as e:
            logger.warning(f"[Analyst] Market research failed: {e}")
            research["error"] = str(e)

        return research

    async def _research_gap(self, gap: dict, product_type: str, product_description: str) -> dict:
        """Do targeted research to fill a specific gap in the brief."""
        section = gap["section"]
        reason = gap["reason"]

        research_prompts = {
            "competition": f"Find 3-5 specific competitors for this {product_type}: {product_description}. Include their names, pricing, and what they do well/poorly.",
            "financials": f"What's realistic pricing for this {product_type}: {product_description}? Include development costs, pricing strategy, and expected margins.",
            "target_customer": f"Who specifically would buy this {product_type}: {product_description}? Include demographics, pain points, and where to find them.",
            "differentiation": f"How could this {product_type} differentiate from competitors: {product_description}? Be specific about unique value.",
            "swot": f"What are the strengths, weaknesses, opportunities, and threats for this {product_type}: {product_description}?",
        }

        prompt = research_prompts.get(section, f"Research more about {section} for: {product_description}")

        try:
            response, _ = await self._generate_with_provider(
                prompt,
                system_prompt="You are a market research assistant. Provide specific, actionable data. Be realistic, not optimistic.",
                temperature=0.3,
            )
            return {"section": section, "research": response, "success": True}
        except Exception as e:
            logger.warning(f"[Analyst] Gap research failed for {section}: {e}")
            return {"section": section, "error": str(e), "success": False}

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process an idea and create a Business Brief.

        ITERATIVE PROCESS: Keeps refining until the brief is complete (90%+).
        """
        self.status = AgentStatus.THINKING
        total_tokens = 0
        max_iterations = 4

        try:
            # Get product type and target from context
            product_type = "printable"
            target_customer = ""
            if context:
                if context.get("project_identity"):
                    product_type = context["project_identity"].get("product_type", "printable")
                if context.get("target_users"):
                    target_customer = context["target_users"]
                elif context.get("brief", {}).get("target_users"):
                    target_customer = context["brief"]["target_users"]

            brief = None
            all_research = {}

            for iteration in range(max_iterations):
                logger.info(f"[Analyst] Iteration {iteration + 1}/{max_iterations}")

                # First iteration: do initial market research
                if iteration == 0:
                    self._current_task = f"Researching market..."
                    research = await self._do_market_research(product_type, task, target_customer)
                    all_research["initial"] = research
                else:
                    # Subsequent iterations: research specific gaps
                    self._current_task = f"Filling gaps (round {iteration + 1})..."
                    completeness = brief.check_completeness()

                    if completeness["is_complete"]:
                        logger.info(f"[Analyst] Brief is complete at {completeness['completeness_pct']}%")
                        break

                    # Research the first 2 incomplete sections
                    gaps_to_fill = completeness["incomplete"][:2]
                    for gap in gaps_to_fill:
                        logger.info(f"[Analyst] Researching gap: {gap['section']} - {gap['reason']}")
                        gap_research = await self._research_gap(gap, product_type, task)
                        if gap_research["success"]:
                            all_research[f"gap_{gap['section']}"] = gap_research["research"]

                # Build prompt with all research accumulated
                self._current_task = f"Writing brief..."
                prompt = self._build_analysis_prompt(task, context, previous_output, all_research)

                # Add previous brief context if we're iterating
                if brief and iteration > 0:
                    completeness = brief.check_completeness()
                    prompt += f"\n\n## PREVIOUS ATTEMPT - FIX THESE GAPS:\n"
                    for gap in completeness["incomplete"]:
                        prompt += f"- {gap['section']}: {gap['reason']}\n"
                    prompt += f"\nAdditional research to help fill gaps:\n"
                    for key, val in all_research.items():
                        if key.startswith("gap_"):
                            prompt += f"\n### {key}:\n{str(val)[:500]}\n"

                self.status = AgentStatus.WORKING
                response, token_info = await self._generate_with_provider(
                    prompt,
                    system_prompt=self.get_system_prompt(),
                    temperature=0.3,
                )
                total_tokens += token_info.get("total_tokens", 0)

                # Parse response
                brief = self._parse_response(response)

                # Enforce project_identity
                if context and context.get("project_identity"):
                    canonical_type = context["project_identity"]["product_type"]
                    if brief.product_type != canonical_type:
                        brief.product_type = canonical_type

                # Check completeness
                completeness = brief.check_completeness()
                logger.info(f"[Analyst] Completeness: {completeness['completeness_pct']}% - Complete: {completeness['complete']}, Incomplete: {[g['section'] for g in completeness['incomplete']]}")

                if completeness["is_complete"]:
                    break

            # Final completeness check
            completeness = brief.check_completeness()

            # Set confidence based on actual completeness
            brief.confidence = completeness["completeness_pct"] / 100.0

            # Set recommendation based on completeness
            if completeness["completeness_pct"] >= 90:
                brief.recommendation = "go"
                brief.recommendation_reason = f"Analysis complete ({completeness['completeness_pct']}%). All key sections filled with specific data."
            elif completeness["completeness_pct"] >= 70:
                brief.recommendation = "go"
                incomplete_sections = [g["section"] for g in completeness["incomplete"]]
                brief.recommendation_reason = f"Analysis mostly complete ({completeness['completeness_pct']}%). Minor gaps in: {', '.join(incomplete_sections)}"
            else:
                brief.recommendation = "needs-more-research"
                incomplete_sections = [g["section"] for g in completeness["incomplete"]]
                brief.recommendation_reason = f"Analysis incomplete ({completeness['completeness_pct']}%). Missing: {', '.join(incomplete_sections)}"

            # Add research sources
            if all_research.get("initial") and not all_research["initial"].get("error"):
                research = all_research["initial"]
                if research.get("competitors"):
                    brief.research_sources.append({
                        "source": "Market research",
                        "data_point": f"Competitors: {', '.join(research['competitors'])}",
                        "confidence": "medium"
                    })
                if research.get("price_range"):
                    brief.research_sources.append({
                        "source": "Price research",
                        "data_point": f"Typical price range: {research['price_range']}",
                        "confidence": "medium"
                    })

            # Log iterations in notes
            brief.analyst_notes = f"Analysis completed in {iteration + 1} iteration(s). Final completeness: {completeness['completeness_pct']}%"

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=brief.get_summary(),
                reasoning=f"Analyzed '{task}' in {iteration + 1} iterations. Completeness: {completeness['completeness_pct']}%",
                tokens_used=total_tokens,
                artifacts={
                    "brief": brief.to_dict(),
                    "type": "business_brief",
                    "recommendation": brief.recommendation,
                    "confidence": brief.confidence,
                    "completeness": completeness,
                    "iterations": iteration + 1,
                },
                next_agent="sketch" if brief.recommendation == "go" else None,
                metadata={
                    "agent": self.name,
                    "product_type": brief.product_type,
                    "recommendation": brief.recommendation,
                    "iterations": iteration + 1,
                    "completeness_pct": completeness["completeness_pct"],
                },
            )

        except Exception as e:
            logger.error(f"[Analyst] Analysis failed: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Analysis failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e), "agent": self.name},
            )
        finally:
            self._current_task = None

    def _build_analysis_prompt(
        self,
        idea: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
        research: Optional[dict] = None,
    ) -> str:
        """Build the prompt for business analysis."""
        prompt_parts = [
            "Analyze the following product idea and create a comprehensive Business Brief.",
            "",
            "## Product Idea",
            idea,
        ]

        # Add market research if available
        if research and not research.get("error"):
            prompt_parts.extend([
                "",
                "## Market Research (use this data in your analysis)",
            ])
            if research.get("competitors"):
                prompt_parts.append(f"**Competitors found:** {', '.join(research['competitors'])}")
            if research.get("price_range"):
                prompt_parts.append(f"**Typical price range:** {research['price_range']}")
            if research.get("where_they_sell"):
                prompt_parts.append(f"**Where they sell:** {', '.join(research['where_they_sell'])}")
            if research.get("market_insights"):
                prompt_parts.append("**Market insights:**")
                for insight in research["market_insights"]:
                    prompt_parts.append(f"  - {insight}")
            if research.get("top_seller_traits"):
                prompt_parts.append(f"**What top sellers do well:** {research['top_seller_traits']}")

        # Add context from Idea Chat if available
        if previous_output:
            prompt_parts.extend([
                "",
                "## Previous Discussion",
                previous_output.content[:2000],  # Limit to avoid token overflow
            ])

        # Add any additional context
        if context:
            if context.get("user_preferences"):
                prompt_parts.extend([
                    "",
                    "## User Preferences",
                    str(context["user_preferences"]),
                ])
            if context.get("constraints"):
                prompt_parts.extend([
                    "",
                    "## Constraints",
                    str(context["constraints"]),
                ])
            if context.get("target_marketplace"):
                prompt_parts.extend([
                    "",
                    "## Target Marketplace",
                    context["target_marketplace"],
                ])
            # Add project_identity - THE canonical source of truth
            if context.get("project_identity"):
                identity = context["project_identity"]
                prompt_parts.extend([
                    "",
                    "## 🔒 PROJECT IDENTITY (LOCKED - DO NOT CHANGE)",
                    f"Product Type: **{identity.get('product_type_name', identity['product_type']).upper()}**",
                    f"Source: {identity.get('source', 'user')}",
                    f"Locked: {identity.get('locked', True)}",
                    "",
                    f"⚠️ You MUST set product_type to exactly: `{identity['product_type']}`",
                    "This was explicitly chosen by the user and cannot be changed.",
                    "If you believe this is wrong, add a note in analyst_notes but DO NOT change product_type.",
                ])
            elif context.get("product_type"):
                # Fallback for older flow
                prompt_parts.extend([
                    "",
                    "## EXPLICIT PRODUCT TYPE (USER SPECIFIED - DO NOT CHANGE)",
                    f"The user has explicitly chosen: **{context.get('product_type_name', context['product_type']).upper()}**",
                    f"You MUST set product_type to: {context['product_type']}",
                    "Do NOT infer a different product type from the description.",
                ])

            # Add conversation completeness info
            brief_data = context.get("brief", {})
            topics_covered = brief_data.get("topics_covered", {})
            if topics_covered:
                covered_count = sum(1 for v in topics_covered.values() if v)
                total_topics = len(topics_covered)
                if covered_count >= total_topics * 0.8:
                    prompt_parts.extend([
                        "",
                        "## ✅ THOROUGH INPUT RECEIVED",
                        f"The user conversation covered {covered_count}/{total_topics} required topics.",
                        "This is COMPREHENSIVE input. You have enough information for a HIGH CONFIDENCE (85%+) analysis.",
                        "Only give lower confidence if there are REAL blockers like no differentiation or unrealistic scope.",
                    ])

        prompt_parts.extend([
            "",
            "## Analysis Instructions",
            "",
            "Take your time and be thorough. Follow these steps:",
            "",
            "### Step 1: Identify Product Type & Marketplace",
            "- Use the EXPLICIT PRODUCT TYPE if specified above",
            "- Otherwise determine: printable, document, web, or app",
            "- Identify primary marketplace (Etsy, Amazon KDP, App Store, etc.)",
            "",
            "### Step 2: Research Competition",
            "- Find 3-5 real competitors in the target marketplace",
            "- Note their pricing, features, and apparent sales volume",
            "- Identify gaps and differentiation opportunities",
            "",
            "### Step 3: Define Target Customer",
            "- Be specific: demographics, pain points, buying behavior",
            "- Where do they shop? What do they search for?",
            "",
            "### Step 4: Calculate Realistic Financials",
            "- Base ALL numbers on marketplace research, not guesses",
            "- Include: production cost, platform fees, realistic price point",
            "- Calculate break-even: 'Need X sales at $Y to recover Z investment'",
            "- Use conservative estimates (assume you're a new seller)",
            "- If you don't have data, say 'Requires research' - don't guess",
            "",
            "### Step 5: Define Success Criteria",
            "- Measurable milestones (sales, revenue, reviews)",
            "- Realistic timeline for new products in this marketplace",
            "",
            "### Step 6: Make Recommendation",
            "- GO: Clear market opportunity, realistic path to profit",
            "- NO-GO: Explain what would need to change",
            "- NEEDS-MORE-RESEARCH: Specify what data is missing",
            "",
            "Output your analysis as valid JSON matching the required schema.",
            "Every number must have reasoning. No guessing.",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, response: str) -> BusinessBrief:
        """Parse LLM response into a BusinessBrief.

        Handles JSON extraction from potentially messy LLM output.
        """
        # Try to extract JSON from the response
        json_str = response

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()

        # Try to find JSON object
        if not json_str.startswith("{"):
            # Look for first { and last }
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]

        try:
            data = json.loads(json_str)
            return BusinessBrief.from_dict(data)
        except json.JSONDecodeError as e:
            logger.warning(f"[Analyst] Failed to parse JSON: {e}")
            # Create a minimal brief from the raw response
            return BusinessBrief(
                product_name="Parse Error",
                product_description="Failed to parse LLM response",
                executive_summary=response[:500],
                recommendation="needs-more-research",
                recommendation_reason="Analysis output could not be parsed. Manual review required.",
                confidence=0.0,
                analyst_notes=f"Raw response: {response[:1000]}",
            )

    async def quick_viability_check(self, idea: str) -> dict:
        """Quick viability check before full analysis.

        Returns a simple assessment of whether the idea is worth analyzing further.

        Args:
            idea: The product idea to check

        Returns:
            Dict with viable (bool), reason (str), confidence (float)
        """
        self.status = AgentStatus.THINKING
        self._current_task = f"Quick check: {idea[:30]}..."

        try:
            prompt = f"""Quickly assess this product idea for basic viability.

IDEA: {idea}

Answer in JSON format:
{{
    "viable": true/false,
    "reason": "one sentence explanation",
    "confidence": 0.0-1.0,
    "suggested_type": "printable/document/web/app",
    "red_flags": ["list of concerns if any"]
}}

Be decisive. This is a quick gut-check, not a full analysis.
"""

            self.status = AgentStatus.WORKING

            response, token_info = await self._generate_with_provider(
                prompt,
                temperature=0.2,
            )

            # Parse response
            try:
                # Extract JSON
                json_str = response
                if "```" in response:
                    start = response.find("```") + 3
                    if response[start:start+4] == "json":
                        start += 4
                    end = response.find("```", start)
                    json_str = response[start:end].strip()
                elif "{" in response:
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    json_str = response[start:end]

                result = json.loads(json_str)
                self.status = AgentStatus.COMPLETED
                return result

            except json.JSONDecodeError:
                self.status = AgentStatus.COMPLETED
                return {
                    "viable": True,  # Default to viable, let full analysis decide
                    "reason": "Quick check inconclusive, proceeding to full analysis",
                    "confidence": 0.3,
                    "suggested_type": "unknown",
                    "red_flags": [],
                }

        except Exception as e:
            logger.error(f"[Analyst] Quick viability check failed: {e}")
            self.status = AgentStatus.ERROR
            return {
                "viable": True,  # Default to viable on error
                "reason": f"Check failed: {str(e)}",
                "confidence": 0.0,
                "error": str(e),
            }
        finally:
            self._current_task = None
