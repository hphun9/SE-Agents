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
| **Session persistence** | Active sessions are stored in MongoDB — server restarts don't lose work |
| **Direct agent access** | `/ask <role> <message>` to consult any agent outside the pipeline |
| **Bug fix flow** | `/fix <path> <error>` — Dev fixes it, QA runs tests, screenshot sent to Telegram |
| **Max subscription** | Calls go through the `claude` CLI — no API billing, uses your Claude Max plan |

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
├── .gitignore
│
├── core/
│   ├── models.py            ← AgentMessage envelope, SessionState, dataclasses
│   ├── claude.py            ← Claude wrapper — routes calls through `claude` CLI
│   ├── storage.py           ← MongoDB session persistence (motor async)
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
│   ├── fixer.py             ← Dev fix agent: read project → patch files
│   ├── qa_runner.py         ← Run tests + render terminal output as PNG
│   ├── consult.py           ← Direct /ask <role> consultation handler
│   └── orchestrator.py      ← state machine, session store, pipeline runner
│
├── bot/
│   └── telegram.py          ← python-telegram-bot v21, inline keyboard approval
│
├── roles/                   ← Agent persona definitions (Claude Code / Cursor)
│   ├── ba-business-analyst.md
│   ├── sa-solution-architect.md
│   └── ...                  ← 18 role files total
│
└── src/                     ← legacy TypeScript prototype (reference only)
    └── ...
```

---

## Setup

### Option A — Docker (recommended)

```bash
# 1. Copy and fill in config
cp .env.example .env

# 2. Authenticate Claude Code on the HOST first (one-time)
claude   # log in interactively, then exit

# 3. Build and start everything
PROJECTS_DIR=/path/to/your/projects docker-compose up -d
```

`docker-compose` starts both the bot and a MongoDB instance automatically.
Your projects are mounted at `/projects` inside the container — use that path in `/fix`.

---

### Option B — Local

#### Prerequisites

- Python 3.11+
- [Claude Code CLI](https://claude.ai/code) installed and authenticated
- MongoDB running locally or a [MongoDB Atlas](https://www.mongodb.com/atlas) URI

> **Why Claude Code CLI?**  Agent calls go through `claude -p` — no API billing, uses your Claude Max subscription.

```bash
# Install deps
pip install -r requirements.txt

# Start MongoDB (if local)
docker run -d -p 27017:27017 mongo

# Configure
cp .env.example .env
# Edit .env: TELEGRAM_BOT_TOKEN, MONGODB_URI, MONGODB_DB

# Run
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
| Consult an agent | `/ask <role> <question>` — works anytime, with or without active project |
| Fix a bug | `/fix <project_path> <error description>` — Dev fixes, QA tests, screenshot sent |

### Direct agent consultation — `/ask`

You can address any agent directly outside the pipeline:

```
/ask ba   What requirements am I missing from this spec?
/ask sa   Should I use microservices or a monolith for 10k users/day?
/ask dev  Fix this 401 error — here's my auth middleware: [code]
/ask qa   Write unit tests for the login flow
/ask lead Review this API design
```

**Available roles:**

| Alias | Agent | Model |
|-------|-------|-------|
| `ba`, `business` | Business Analyst | Sonnet |
| `sa`, `architect` | Solution Architect | Opus |
| `pm`, `manager` | Project Manager | Sonnet |
| `lead`, `tl` | Tech Lead | Opus |
| `dev`, `backend`, `be` | Backend Developer | Opus |
| `frontend`, `fe`, `ui` | Frontend Developer | Sonnet |
| `qa`, `test` | QA Engineer | Sonnet |

If you have an active project, the agent automatically receives relevant documents (BRD, tech spec, etc.) as context.

### Example pipeline flow

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

### Bug fix flow — `/fix`

```
You:  /fix /projects/myapp Getting 401 on every POST /api/auth/login

Bot:  🔍 Dev agent is analysing /projects/myapp...

Bot:  🔧 Fix applied
      Analysis: JWT secret was missing from .env — middleware rejected all tokens
      Files changed:
        • auth/middleware.py  (modify)
        • config/settings.py  (modify)
      Summary: Added JWT_SECRET env var lookup; defaulted to raise on missing

      🧪 Running tests...

Bot:  [sends PNG screenshot of terminal output]
      ✓ All tests passed
      Command: pytest tests/test_auth.py -v
```

The fix flow works on **any external project** — it doesn't need to be created through the pipeline.
Just mount the project directory and pass its path.

---

## Inter-Agent Message Format

All agent-to-agent messages use a structured JSON envelope — no natural language between agents:

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
