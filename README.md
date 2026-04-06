# SE-Agents — AI Software Development Team via Telegram

> You describe a project. The team asks clarifying questions, you approve the plan, and the dev team delivers implementation guides — all through Telegram.

---

## How It Works

```
You (Telegram)
   │
   ▼ requirement text
┌──────────────────────────────────────────────────────────┐
│  BA  ──clarification loop (up to 4 rounds)──►  BRD       │  Haiku / Sonnet
│  SA  ──► Architecture Document                           │  Opus
│  PM  ──► Project Plan                                    │  Sonnet
│  TL  ──► Technical Specification                         │  Opus
└──────────────────────────────────────────────────────────┘
   │
   ▼  📋 "Approve or Request Changes?" (inline buttons)
   │
   ▼ ✅ Approved
┌──────────────────────────────────────────────────────────┐
│  Backend Dev  ──► Implementation Guide + code   (Opus)   │
│  Frontend Dev ──► Implementation Guide + code   (Sonnet) │  (parallel)
│  QA           ──► Test Plan + test code         (Sonnet) │
└──────────────────────────────────────────────────────────┘
   │
   ▼ All documents delivered to you in Telegram
```

### Key design principles

| Principle | Detail |
|-----------|--------|
| **Structured inter-agent comms** | Every agent-to-agent message is a typed `AgentMessage` JSON envelope — no natural language between agents |
| **Model tiering** | Haiku → fast Q&A · Sonnet → structured docs · Opus → complex reasoning & code |
| **Approval gate** | Planning phase pauses; you review and either approve or provide feedback |
| **Parallel dev** | Backend Dev and Frontend Dev run concurrently after approval |
| **Async Python** | `asyncio` + `AsyncAnthropic` — non-blocking pipeline |

---

## Agents & Model Assignments

| Agent | Model | Task |
|-------|-------|------|
| **BA** (clarify) | `claude-haiku-4-5` | Generates clarifying questions — fast & cheap |
| **BA** (BRD) | `claude-sonnet-4-6` | Produces Business Requirements Document |
| **Solution Architect** | `claude-opus-4-6` | Architecture design, ADRs, tech stack decisions |
| **Project Manager** | `claude-sonnet-4-6` | Project plan, phases, risks, milestones |
| **Tech Lead** | `claude-opus-4-6` | API design, data models, sprint plan, tech spec |
| **Backend Dev** | `claude-opus-4-6` | Scaffold + real implementation code |
| **Frontend Dev** | `claude-sonnet-4-6` | Components + real UI code |
| **QA Engineer** | `claude-sonnet-4-6` | Test plan, test cases, CI config |

---

## Project Structure

```
se-agents/
│
├── main.py                  ← entry point
├── config.py                ← model assignments & constants
├── requirements.txt
├── .env.example
│
├── core/
│   ├── models.py            ← AgentMessage envelope, SessionState, dataclasses
│   ├── claude.py            ← async Claude API wrapper (streaming)
│   └── formatter.py         ← Telegram MarkdownV2 formatters per document type
│
├── agents/
│   ├── ba.py                ← BA: multi-round clarification loop → BRD
│   ├── sa.py                ← SA: BRD → Architecture Document
│   ├── pm.py                ← PM: BRD + Arch → Project Plan
│   ├── tech_lead.py         ← Tech Lead: all 3 → Technical Spec
│   ├── dev_backend.py       ← Backend Dev: spec → implementation guide + code
│   ├── dev_frontend.py      ← Frontend Dev: spec → implementation guide + code
│   ├── qa.py                ← QA: spec + impls → test plan + test code
│   └── orchestrator.py      ← state machine, session store, pipeline runner
│
├── bot/
│   └── telegram.py          ← python-telegram-bot v21, inline keyboard approval
│
└── src/                     ← legacy TypeScript prototype (reference only)
    └── ...
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- An [Anthropic API key](https://console.anthropic.com)

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   TELEGRAM_BOT_TOKEN=123456789:AAF...
```

### 4. Run

```bash
python main.py
```

---

## Usage

| Action | What to do |
|--------|-----------|
| Start a project | Send any text message with your requirement |
| Answer clarification | Reply to the BA's questions in one message |
| Approve plan | Tap **✅ Approve — Start Dev Team** |
| Request changes | Tap **📝 Request Changes**, then describe what to change |
| New project | Send `/new` or just send a new requirement after completion |
| Check status | Send `/status` |

### Example flow

```
You:  "I want to build a SaaS task management app for small dev teams"

BA:   "Round 1 — I need clarification:
       1. Web only, mobile, or both?
       2. Real-time collaboration or async?
       3. What integrations? (GitHub, Slack, etc.)"

You:  "Web only for now. Real-time. GitHub and Slack integrations."

BA:   "Requirements confirmed! ✅"
      [Delivers BRD]

SA:   [Delivers Architecture Document]
PM:   [Delivers Project Plan]
TL:   [Delivers Technical Specification]

Bot:  "📋 Planning complete! Approve or request changes?"
      [✅ Approve — Start Dev Team]  [📝 Request Changes]

You:  ✅ Approve

Backend Dev:   [Delivers implementation guide + FastAPI code]
Frontend Dev:  [Delivers implementation guide + React code]   ← parallel
QA:            [Delivers test plan + pytest/Playwright tests]

Bot:  "🎉 All done!"
```

---

## Inter-Agent Message Format

All agent-to-agent messages use a structured JSON envelope:

```json
{
  "type": "REQUIREMENTS_CONFIRMED",
  "from_role": "BA",
  "to_role": "ORCHESTRATOR",
  "payload": { "brd": { ... } },
  "metadata": {
    "timestamp": "2026-04-06T10:00:00",
    "project_id": "abc123",
    "session_id": "def456",
    "version": "1.0"
  }
}
```

No natural language between agents — only in Telegram-facing output.

---

## Agent Definition Files

The `roles/` folder contains detailed agent persona definitions for use with Claude Code CLI or Cursor IDE as standalone agents:

| File | Role |
|------|------|
| `roles/ba-business-analyst.md` | Requirements engineering |
| `roles/ba-product-owner.md` | Backlog ownership |
| `roles/sa-solution-architect.md` | System design |
| `roles/sa-security-architect.md` | Security & compliance |
| `roles/sa-data-architect.md` | Data modeling |
| `roles/pm-project-manager.md` | Planning & delivery |
| `roles/pm-scrum-master.md` | Agile ceremonies |
| `roles/pm-technical-program-manager.md` | Cross-team coordination |
| `roles/dev-tech-lead.md` | Code standards & reviews |
| `roles/dev-backend.md` | API & microservices |
| `roles/dev-frontend.md` | React/Vue/Angular |
| `roles/dev-fullstack.md` | Feature ownership |
| `roles/qa-engineer.md` | Test planning |
| `roles/qa-automation-engineer.md` | E2E automation |
| `roles/qa-performance-tester.md` | Load testing |
| `roles/devops-engineer.md` | CI/CD & containers |
| `roles/devops-cloud-architect.md` | Cloud infrastructure |
| `roles/devops-sre.md` | Observability & SLOs |
