---
title: Multi-Model Routing
description: Intelligent AI model selection
tags:
  - routing
  - models
  - ai
created: 2024-02-10
---

# Multi-Model Routing

ATLAS intelligently routes queries to the best AI model based on task type, availability, and quotas.

---

## Supported Providers

| Provider | Best For | Local/Cloud |
|----------|----------|-------------|
| Claude | Code review, analysis, nuanced tasks | Cloud |
| GPT-4 | Code generation, technical writing | Cloud |
| Gemini | Research, summarization, drafts | Cloud |
| Ollama | Quick tasks, privacy-sensitive, unlimited | Local |

---

## Automatic Routing

ATLAS analyzes your query and routes to the optimal model:

```
You: Write a Python sorting algorithm
→ Routes to GPT (code task)

You: Review this pull request for issues
→ Routes to Claude (review task)

You: Research Kubernetes security practices
→ Routes to Gemini (research task)

You: What time is it?
→ Routes to Ollama (simple task)
```

---

## Routing Rules

| Task Type | Primary | Fallback 1 | Fallback 2 |
|-----------|---------|------------|------------|
| Code | GPT | Claude | CodeLlama |
| Review | Claude | Gemini | GPT |
| Research | Gemini | Claude | Ollama |
| Draft | Gemini | Claude | Ollama |
| Simple | Ollama | Gemini | Claude |

---

## Task Detection

ATLAS detects task types from keywords:

**Code Tasks:**
- "write", "implement", "function", "code", "script"
- "debug", "fix this bug", "refactor"

**Review Tasks:**
- "review", "analyze", "check", "evaluate"
- "what do you think", "is this correct"

**Research Tasks:**
- "research", "find out", "investigate"
- "what are the best", "how does X work"

**Draft Tasks:**
- "write", "draft", "compose", "email"
- "document", "explain"

---

## Quota Management

Each cloud provider has daily limits:

```yaml
providers:
  claude:
    daily_limit: 45
  openai:
    daily_limit: 40
  gemini:
    daily_limit: 100
```

When a provider reaches its limit:
1. ATLAS automatically falls back to next best option
2. You're notified: "Sir, we've reached our Claude quota. Routing to Gemini."

---

## Check Provider Status

```
You: /status

[ATLAS] Current provider status, sir:

Provider    │ Used Today │ Limit │ Status
────────────┼────────────┼───────┼────────
Claude      │ 42         │ 45    │ ⚠️ Low
GPT-4       │ 12         │ 40    │ ✓
Gemini      │ 3          │ 100   │ ✓
Ollama      │ Local      │ ∞     │ ✓
```

---

## Force a Specific Model

Override automatic routing:

```
You: /model claude
You: [Your query here - will use Claude]

You: /model gpt
You: [Your query here - will use GPT]

You: /model ollama
You: [Your query here - will use Ollama]

You: /model auto
[Back to automatic routing]
```

> [!warning] Quota Still Applies
> Forcing a model still counts against its daily quota.

---

## Ollama Models

Configure multiple Ollama models for different tasks:

```yaml
providers:
  ollama:
    models:
      default: "llama3"        # General tasks
      code: "codellama:13b"    # Code generation
      fast: "llama3.2:3b"      # Quick responses
```

ATLAS selects the appropriate Ollama model based on task type.

---

## Fallback Behavior

When the primary model is unavailable:

1. **Quota exceeded** → Next model in fallback chain
2. **API error** → Retry once, then fallback
3. **Timeout** → Fallback with notification
4. **All cloud providers down** → Ollama (always available)

> [!info] Ollama as Safety Net
> Local Ollama models are always available as the final fallback, ensuring ATLAS never fails completely.

---

## See Also

- [[Configuration]] - Provider settings
- [[Commands]] - Model override commands

---

#routing #models #ai
