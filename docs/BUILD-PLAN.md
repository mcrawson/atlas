# ATLAS 3.0 Build Plan

**Project:** ATLAS Rebuild - "Watch AI Teams Build Your Products"
**Started:** 2026-03-13
**Updated:** 2026-03-20
**Status:** Phase 4 - Agent Collaboration Engine

---

## The Mission

> **ATLAS is a product studio that combines human creativity with ethical AI to build transformative solutions for our clients and the public.**

This mission is the foundation. Every agent, every decision, every product ties back to this.

| Word | Meaning |
|------|---------|
| **Product studio** | We make finished, sellable products. Not demos. Not prototypes. |
| **Human creativity** | You bring the ideas and vision. AI doesn't replace you. |
| **Ethical AI** | We build responsibly. Quality matters. No shortcuts. |
| **Transformative solutions** | Products that solve real problems. That matter. |
| **Clients and the public** | For paying customers AND broader impact. |

---

## The Vision: Layla-Style Agent Collaboration

ATLAS should work like this:

1. **You describe ANY idea** - a planner, an app, a book, a website, anything
2. **ATLAS analyzes the goal** and dynamically assembles a team of AI agents specific to that goal
3. **You WATCH the agents work** - they discuss, debate, and refine in real-time
4. **A Director orchestrates** - managing the conversation, resolving conflicts, keeping things moving
5. **Agents actually BUILD** - producing sellable products, not just reports
6. **You review and approve** - the human is always final authority

**Reference:** [Layla AI](https://layla-ai.app/) - This is the experience we're building.

---

## What Makes This Different

### Before (ATLAS 2.0)
```
User → Agent 1 → Agent 2 → Agent 3 → Output
         ↓          ↓          ↓
      (silent)  (silent)   (silent)
```
- Sequential pipeline
- Pre-defined agents
- User can't see what's happening
- Agents don't talk to each other

### After (ATLAS 3.0)
```
User → Director → ┌─────────────────────────────────┐
                  │     AGENT CONVERSATION ROOM      │
                  │                                  │
                  │  🧠 Expert: "For this planner,   │
                  │     we should use weekly spread" │
                  │                                  │
                  │  📋 Planner: "I'll structure it  │
                  │     with habit tracking sections"│
                  │                                  │
                  │  ✅ QC: "Make sure pages print   │
                  │     correctly at A5 size"        │
                  │                                  │
                  │  🎨 Builder: "Starting design... │
                  │     using minimalist palette"    │
                  │                                  │
                  └─────────────────────────────────┘
                              ↑
                         USER WATCHES
                         IN REAL-TIME
```
- Dynamic agent creation
- Agents debate and collaborate
- User sees everything happening
- Director keeps things moving

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    CONVERSATION VIEWER                               │    │
│  │  Real-time stream of agent discussion                               │    │
│  │  WebSocket connection shows live agent-to-agent messages            │    │
│  │  User can see reasoning, debates, decisions                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   Agent Panel    │  │   Build Status   │  │   Deliverables   │          │
│  │   (who's active) │  │   (progress)     │  │   (outputs)      │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONVERSATION ENGINE                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         DIRECTOR AGENT                               │    │
│  │  • Analyzes user's goal                                             │    │
│  │  • Spawns appropriate agents dynamically                            │    │
│  │  • Manages conversation flow                                        │    │
│  │  • Resolves conflicts between agents                                │    │
│  │  • Decides when to move to next phase                               │    │
│  │  • Streams all messages to UI in real-time                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      DYNAMIC AGENT POOL                               │   │
│  │                                                                       │   │
│  │  🧠 Custom Expert     📋 Planner        ✅ QC Agent                  │   │
│  │  (spawned per project) (build strategy)  (quality gates)             │   │
│  │                                                                       │   │
│  │  🎨 PrintableBuilder  📚 DocumentBuilder  🌐 WebBuilder  📱 AppBuilder│   │
│  │  (planners, cards)     (books, guides)    (websites)    (mobile apps)│   │
│  │                                                                       │   │
│  │  More agents spawned as needed based on project requirements...      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MESSAGE BROKER                                     │
│                                                                              │
│  • Agent-to-agent messaging                                                  │
│  • Conversation history                                                      │
│  • Real-time broadcast to all participants                                   │
│  • WebSocket fan-out to UI                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components to Build

### 1. Director Agent
The orchestrator that runs the show.

```python
class DirectorAgent:
    """Orchestrates the agent conversation."""

    async def analyze_goal(self, user_input: str) -> TeamComposition:
        """Analyze what the user wants and determine which agents to spawn."""

    async def spawn_team(self, composition: TeamComposition) -> List[Agent]:
        """Dynamically create the agent team for this project."""

    async def run_conversation(self, team: List[Agent], goal: str) -> None:
        """Manage the agent discussion until consensus/completion."""

    async def broadcast_message(self, message: AgentMessage) -> None:
        """Send message to all agents AND stream to UI."""

    async def resolve_conflict(self, positions: List[Position]) -> Decision:
        """When agents disagree, make a decision."""

    async def advance_phase(self) -> None:
        """Move from planning → design → build → review."""
```

### 2. Message Broker
Handles all agent-to-agent and agent-to-UI communication.

```python
class MessageBroker:
    """Central hub for all agent communication."""

    async def send(self, message: AgentMessage) -> None:
        """Send message to specific agent(s)."""

    async def broadcast(self, message: AgentMessage) -> None:
        """Send message to all agents in conversation."""

    async def stream_to_ui(self, message: AgentMessage) -> None:
        """Push message to WebSocket for real-time UI display."""

    def get_conversation_history(self) -> List[AgentMessage]:
        """Full conversation log."""
```

### 3. Agent Factory
Dynamically creates agents based on project needs.

```python
class AgentFactory:
    """Creates agents on-demand based on project requirements."""

    def create_expert(self, domain: str, brief: BusinessBrief) -> CustomExpert:
        """Spawn a domain expert for this specific project."""

    def create_builder(self, product_type: str) -> Builder:
        """Get the right builder for this product type."""

    def create_specialist(self, specialty: str) -> Agent:
        """Create any specialized agent needed."""
```

### 4. WebSocket Manager
Real-time connection to the UI.

```python
class ConversationStream:
    """WebSocket handler for real-time UI updates."""

    async def connect(self, project_id: str) -> None:
        """Establish WebSocket connection for a project."""

    async def push_message(self, message: AgentMessage) -> None:
        """Send agent message to connected UI."""

    async def push_status(self, status: BuildStatus) -> None:
        """Send build progress update."""

    async def push_deliverable(self, deliverable: Deliverable) -> None:
        """Send completed artifact to UI."""
```

---

## Conversation Flow

### Phase 1: Goal Analysis
```
User: "Build me a weekly planner for fitness tracking"
        │
        ▼
Director: [Analyzes goal]
        │
        ├── Product Type: Printable (planner)
        ├── Domain: Fitness/Health
        ├── Features Needed: Weekly layout, habit tracking, workout logging
        └── Team Required: Expert (fitness), Planner, PrintableBuilder, QC
        │
        ▼
Director: "I've analyzed your goal. Spawning a fitness planning expert
          and assembling the team. Watch us work..."
```

### Phase 2: Team Assembly (Visible to User)
```
Director: "Team assembled. Let me introduce everyone."
        │
        ▼
🧠 FitnessExpert: "I'm your fitness planning specialist. I know what
                  makes workout trackers effective - we need space for
                  sets, reps, and progressive overload tracking."
        │
📋 Planner: "I'll structure the weekly spread. Should we do
            single-page or two-page weekly view?"
        │
✅ QC: "I'll make sure this is printable at standard sizes and
       looks professional enough to sell on Etsy."
        │
🎨 PrintableBuilder: "Ready to design. I work in clean, modern layouts
                      optimized for both screen viewing and printing."
```

### Phase 3: Agent Discussion (Real-Time, Visible)
```
📋 Planner: "For fitness tracking, I recommend:
            - Two-page weekly spread (more space for workouts)
            - Daily workout section with exercise rows
            - Weekly goal summary at the top
            - Habit tracker on the side"

🧠 FitnessExpert: "Good structure. Add a 'Personal Best' tracking
                  section - users love seeing progress. Also need
                  rest day indicators."

✅ QC: "Two-page spread works, but make sure it prints correctly
       as facing pages. Margins need to account for binding."

🎨 PrintableBuilder: "I'll use a clean sans-serif font and muted
                      color palette - professional but motivating.
                      Thinking charcoal gray with accent blue."

Director: "Consensus reached on structure. Moving to design phase."
```

### Phase 4: Build Phase (Progress Visible)
```
🎨 PrintableBuilder: "Starting design..."
        │
        ├── [Generating weekly spread layout...]
        ├── [Adding workout tracking rows...]
        ├── [Styling habit tracker...]
        ├── [Creating cover page...]
        │
🎨 PrintableBuilder: "First draft complete. Sending to QC."
        │
        ▼
✅ QC: "Reviewing against brief and sellability criteria..."
        │
        ├── ✓ Layout is clean and professional
        ├── ✓ Printable at A5 and Letter sizes
        ├── ⚠ Workout rows might be too small for handwriting
        │
✅ QC: "One issue: workout rows are 6mm - recommend 8mm for
       comfortable handwriting. Otherwise looks sellable."
        │
        ▼
🎨 PrintableBuilder: "Adjusting row height to 8mm..."
        │
🎨 PrintableBuilder: "Revision complete. Ready for user review."
```

### Phase 5: User Review
```
Director: "Your fitness planner is ready for review."
        │
        ▼
[UI shows PDF preview]
[User can: Approve / Request Changes / Reject]
        │
        ▼
User: [Approves]
        │
Director: "Excellent! Generating final files for Etsy listing..."
```

---

## Build Phases (Updated)

### Phase 1: Foundation ✅ COMPLETE
- Clean codebase
- Builder architecture
- Business Brief model
- Basic agent structure

### Phase 2: Analyst Agent ✅ COMPLETE
- Business Brief generation
- Go/No-Go decision
- Market analysis

### Phase 3: Specialized Builders ✅ COMPLETE
- PrintableBuilder
- DocumentBuilder
- WebBuilder
- AppBuilder

### Phase 4: Agent Conversation Engine 🔄 IN PROGRESS

**Goal:** Build the real-time agent collaboration system

**Tasks:**
1. [ ] **Director Agent** - Orchestrates everything
   - Goal analysis and team composition
   - Conversation management
   - Conflict resolution
   - Phase advancement

2. [ ] **Message Broker** - Agent communication hub
   - Agent-to-agent messaging
   - Conversation history
   - Event broadcasting

3. [ ] **WebSocket Manager** - Real-time UI streaming
   - `/ws/projects/{id}/conversation` endpoint
   - Push messages as they happen
   - Handle reconnection

4. [ ] **Agent Factory** - Dynamic agent creation
   - Spawn custom experts based on domain
   - Get appropriate builder
   - Create specialists as needed

5. [ ] **Conversation UI** - Watch it happen
   - Real-time message stream
   - Agent avatars/identification
   - Phase indicators
   - Typing indicators

**Deliverable:** Users watch agents discuss and build in real-time

### Phase 5: QC Integration

**Goal:** Quality gates throughout the conversation

**Tasks:**
1. [ ] QC participates in agent conversation
2. [ ] QC reviews at each phase transition
3. [ ] Warning → Retry → Block flow
4. [ ] QC reports visible in conversation stream
5. [ ] Sellability scoring

**Deliverable:** QC is a conversation participant, not a post-process check

### Phase 6: Polish & Learning

**Goal:** Refinement and improvement over time

**Tasks:**
1. [ ] Polish agent for design refinement
2. [ ] User feedback collection
3. [ ] Agent performance tracking
4. [ ] Knowledge base updates

**Deliverable:** System improves based on feedback

### Phase 7: Multi-Platform (OpenClaw)

**Goal:** Access ATLAS from any chat platform

**Tasks:**
1. [ ] ATLAS skill for OpenClaw
2. [ ] WhatsApp, Telegram, Discord integration
3. [ ] Same conversation experience everywhere

**Deliverable:** Message ATLAS from any platform

---

## Technical Requirements

### WebSocket Protocol
```typescript
// Client connects
ws://localhost:8000/ws/projects/123/conversation

// Server pushes messages as they happen
{
  "type": "agent_message",
  "sender": "planner",
  "content": "I recommend a two-page weekly spread...",
  "timestamp": "2026-03-20T10:30:00Z"
}

{
  "type": "status_update",
  "phase": "design",
  "progress": 45,
  "current_action": "Generating layout..."
}

{
  "type": "deliverable",
  "name": "weekly_spread.pdf",
  "preview_url": "/projects/123/preview/weekly_spread.pdf"
}
```

### Agent Message Format
```python
@dataclass
class AgentMessage:
    sender: str           # Agent identifier
    content: str          # Message text
    message_type: str     # 'discussion', 'decision', 'question', 'deliverable'
    recipient: str | None # Specific agent or None for broadcast
    timestamp: datetime
    metadata: dict        # Phase, confidence, etc.
```

### Director Decision Flow
```python
async def run_conversation(self, team, goal):
    # Phase 1: Analysis
    await self.broadcast("Analyzing your goal...")
    composition = await self.analyze_goal(goal)

    # Phase 2: Team Assembly
    await self.broadcast("Assembling your team...")
    agents = await self.spawn_team(composition)
    await self.introduce_team(agents)

    # Phase 3: Discussion
    while not self.consensus_reached():
        # Let agents discuss
        for agent in agents:
            response = await agent.respond_to_conversation()
            await self.broadcast(response)
            await self.stream_to_ui(response)

        # Director checks progress
        if self.needs_intervention():
            await self.intervene()

    # Phase 4: Build
    await self.advance_to_build()
    builder = self.get_active_builder()
    async for progress in builder.build():
        await self.stream_to_ui(progress)

    # Phase 5: Review
    await self.qc_review()
    await self.request_user_approval()
```

---

## Success Criteria

### The Test
Can a user:
1. Submit any idea (planner, app, book, website)
2. Watch agents discuss and debate in real-time
3. See the product being built with progress updates
4. Receive a sellable, finished product

### Specific Metrics
- [ ] Real-time conversation visible within 2 seconds of agent response
- [ ] Dynamic expert spawned matches the domain (fitness → fitness expert)
- [ ] Agents reference each other's points in discussion
- [ ] QC catches issues before user review
- [ ] Final product looks professional, not prototype-y

---

## What We Keep From Current Build

| Component | Keep | Modify |
|-----------|------|--------|
| BusinessBrief model | ✓ | Used by Director for team composition |
| Specialized Builders | ✓ | Become conversation participants |
| QC Agent | ✓ | Participates in conversation |
| Web templates | ✓ | Add real-time conversation viewer |
| FastAPI backend | ✓ | Add WebSocket endpoints |

## What's New

| Component | Purpose |
|-----------|---------|
| Director Agent | Orchestrates everything |
| Message Broker | Agent-to-agent communication |
| WebSocket Manager | Real-time UI streaming |
| Agent Factory | Dynamic agent creation |
| Conversation UI | Watch agents work |

---

## Decisions Made

| Decision | Choice | Date |
|----------|--------|------|
| Mobile framework | React Native | 2026-03-13 |
| Builder architecture | Specialized builders | 2026-03-13 |
| Agent collaboration | Layla-style real-time conversation | 2026-03-20 |
| UI experience | Watch agents work in real-time | 2026-03-20 |
| Agent spawning | Dynamic based on goal analysis | 2026-03-20 |
| Communication | WebSocket streaming | 2026-03-20 |

---

## Living Documents

| Document | Purpose | Update When |
|----------|---------|-------------|
| **MISSION.md** | Why ATLAS exists | Rarely |
| **BUILD-PLAN.md** | What we're building | Decisions made, phases complete |
| **USER-MANUAL.md** | How to use ATLAS | Features added |
| **LESSONS-LEARNED.md** | Issues and fixes | Bugs found, patterns discovered |

**Last Updated:** 2026-03-20 (Rewritten for Layla-style agent collaboration)
