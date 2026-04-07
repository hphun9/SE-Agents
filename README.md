# SE-Agents — AI Software Development Team via Telegram

> Describe a project in plain text. The AI team asks clarifying questions, produces formal documents, lets you approve the plan, then the dev team delivers implementation guides with real code — all delivered to your Telegram chat.

---

## Features

| Feature | Detail |
|---------|--------|
| **BA clarification loop** | Up to 4 rounds of Q&A before producing a BRD |
| **Full pipeline** | BA → SA → PM → Tech Lead → Dev (parallel) → QA |
| **Approval gate** | Review planning docs before dev team starts — approve or request changes |
| **Direct agent consult** | `/ask <role> <question>` any time, with or without an active project |
| **Bug fix flow** | `/fix <path> <error>` — Dev fixes it, QA runs tests, screenshot sent to Telegram |
| **Session persistence** | MongoDB stores sessions — server restarts don't lose work |
| **No API billing** | Calls go through `claude` CLI — uses your Claude Max subscription |
| **Structured comms** | All inter-agent messages are typed JSON envelopes, never natural language |

---

## How It Works

```
You (Telegram)
   │
   ▼  plain text requirement
┌──────────────────────────────────────────────────────────────┐
│  BA  ── clarification loop (up to 4 rounds) ──►  BRD         │  Haiku / Sonnet
│  SA  ──► Architecture Document                               │  Opus
│  PM  ──► Project Plan                                        │  Sonnet
│  TL  ──► Technical Specification                             │  Opus
└──────────────────────────────────────────────────────────────┘
   │
   ▼  📋 Approve or Request Changes? (inline keyboard)
   │
   ▼  ✅ Approved
┌──────────────────────────────────────────────────────────────┐
│  Backend Dev  ──► Implementation Guide + code       (Opus)   │
│  Frontend Dev ──► Implementation Guide + code       (Sonnet) │  ← parallel
│  QA           ──► Test Plan + test code             (Sonnet) │
└──────────────────────────────────────────────────────────────┘
   │
   ▼  All documents delivered to your Telegram chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/fix flow (independent of pipeline — works on any project)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/fix /projects/myapp <error description>
   │
   ▼  Haiku triages relevant files  (cheap)
   ▼  Opus analyses + generates fix (precise)
   ▼  Writes patched files to disk
   ▼  Runs test command via subprocess
   ▼  Renders terminal output as PNG
   ▼  Sends screenshot to Telegram  📸
```

---

## Agents & Models

| Agent | Model | Task |
|-------|-------|------|
| **BA** — clarify | `claude-haiku-4-5` | Fast clarifying questions |
| **BA** — BRD | `claude-sonnet-4-6` | Business Requirements Document |
| **Solution Architect** | `claude-opus-4-6` | Architecture, ADRs, tech-stack decisions |
| **Project Manager** | `claude-sonnet-4-6` | Project plan, phases, risks, milestones |
| **Tech Lead** | `claude-opus-4-6` | API design, data models, technical spec |
| **Backend Dev** | `claude-opus-4-6` | Scaffold + real implementation code |
| **Frontend Dev** | `claude-sonnet-4-6` | Components + real UI code |
| **QA Engineer** | `claude-sonnet-4-6` | Test plan, test cases, CI config |
| **Fixer** — triage | `claude-haiku-4-5` | Identify relevant files cheaply |
| **Fixer** — patch | `claude-opus-4-6` | Analyse bug, generate & apply fix |

---

## Project Structure

```
se-agents/
│
├── main.py                   ← entry point
├── config.py                 ← model assignments per task
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── core/
│   ├── models.py             ← AgentMessage envelope, SessionState, dataclasses
│   ├── claude.py             ← calls `claude -p` CLI (uses Max subscription)
│   ├── storage.py            ← MongoDB session persistence (motor async)
│   └── formatter.py          ← Telegram MarkdownV2 formatters per document type
│
├── agents/
│   ├── orchestrator.py       ← pipeline state machine + session store
│   ├── ba.py                 ← BA: clarification loop → BRD
│   ├── sa.py                 ← SA: BRD → Architecture Document
│   ├── pm.py                 ← PM: BRD + Arch → Project Plan
│   ├── tech_lead.py          ← Tech Lead: → Technical Specification
│   ├── dev_backend.py        ← Backend Dev: → implementation guide + code
│   ├── dev_frontend.py       ← Frontend Dev: → implementation guide + code
│   ├── qa.py                 ← QA: → test plan + test code
│   ├── fixer.py              ← /fix: triage files, generate & apply patch
│   ├── qa_runner.py          ← run tests, capture output, render PNG screenshot
│   └── consult.py            ← /ask: direct per-role consultation
│
├── bot/
│   └── telegram.py           ← python-telegram-bot v21, all command handlers
│
├── roles/                    ← 18 agent persona definitions (Claude Code / Cursor)
│   ├── ba-business-analyst.md
│   ├── sa-solution-architect.md
│   └── ...
│
└── src/                      ← legacy TypeScript prototype (reference only)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| AI | Claude Code CLI (`claude -p`) — Max subscription, no API billing |
| Telegram | python-telegram-bot v21 (async) |
| Database | MongoDB via motor (async driver) |
| Screenshots | Pillow — terminal output rendered as PNG |
| Async | asyncio + `asyncio.gather()` for parallel dev agents |
| Container | Docker + Docker Compose |

---

## Setup

### Option A — Docker (recommended)

**Prerequisites:** Docker, Docker Compose, a Claude Max subscription, a Telegram bot token.

```bash
# 1. Clone and configure
git clone https://github.com/hphun9/SE-Agents.git
cd SE-Agents
cp .env.example .env
# Edit .env — fill in TELEGRAM_BOT_TOKEN and PROJECTS_DIR

# 2. Authenticate Claude Code on the HOST machine (one-time)
#    This saves auth tokens to ~/.claude which the container mounts read-only
claude

# 3. Start bot + MongoDB
PROJECTS_DIR=/absolute/path/to/your/projects docker-compose up -d

# 4. View logs
docker-compose logs -f bot
```

Your projects are mounted at `/projects` inside the container.
Use container paths in `/fix`: `/fix /projects/myapp Fix the login error`.

---

### Option B — Local (development)

**Prerequisites:** Python 3.11+, Node.js, MongoDB.

```bash
# Install Python deps
pip install -r requirements.txt

# Install and authenticate Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude   # log in

# Start MongoDB
docker run -d -p 27017:27017 mongo
# or use MongoDB Atlas — set MONGODB_URI in .env

# Configure
cp .env.example .env
# Fill in: TELEGRAM_BOT_TOKEN, MONGODB_URI, MONGODB_DB

# Run
python main.py
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | From [@BotFather](https://t.me/BotFather) |
| `MONGODB_URI` | ✅ | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB` | | `se_agents` | Database name |
| `PROJECTS_DIR` | | `/tmp/projects` | Host path mounted as `/projects` in Docker |

---

## Commands

| Command | Description |
|---------|-------------|
| _(any text)_ | Start a new project with that requirement |
| `/new` | Clear current session and start fresh |
| `/status` | Show current pipeline state |
| `/ask <role> <question>` | Consult a specific agent directly |
| `/fix <path> <error>` | Dev fixes a bug, QA tests it, screenshot sent |
| `/help` | Show all commands and available roles |

### `/ask` — direct agent consultation

Address any agent directly, with or without an active project. If a session exists the agent automatically receives relevant documents as context.

```
/ask ba    What requirements am I missing?
/ask sa    Should I use microservices or a monolith for 10k users/day?
/ask lead  Review this API design: [paste design]
/ask dev   Fix this 401 error — here's my middleware: [paste code]
/ask qa    Write unit tests for the login flow
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

### `/fix` — bug fix with QA screenshot

Works on **any project** on your filesystem — no pipeline session required.

```
/fix /projects/myapp Getting 401 on every POST /api/auth/login
```

Flow:
1. **Haiku** triages which files are relevant (cheap)
2. **Opus** reads files, analyses the bug, generates a patch
3. Bot writes the patched files to disk
4. Runs the test command via subprocess
5. Renders terminal output as a PNG and sends it to Telegram

---

## Example Flows

### Full pipeline

```
You:   "Build a SaaS task manager for small dev teams"

BA:    Round 1 — clarifying:
         1. Web only or mobile too?
         2. Real-time or async collaboration?
         3. Any integrations? (GitHub, Slack…)

You:   "Web only. Real-time. GitHub + Slack."

BA:    ✅ Requirements confirmed  →  [BRD delivered]
SA:    [Architecture Document delivered]
PM:    [Project Plan delivered]
TL:    [Technical Specification delivered]

Bot:   📋 Planning complete — approve or request changes?
       [✅ Approve]   [📝 Request Changes]

You:   ✅ Approve

Dev:   Backend guide + FastAPI code       ← parallel
Dev:   Frontend guide + React code        ← parallel
QA:    Test plan + pytest/Playwright      ← after both devs finish

Bot:   🎉 All done!
```

### Bug fix

```
You:   /fix /projects/myapp Getting 401 on every POST /api/auth/login

Bot:   🔍 Dev agent is analysing /projects/myapp...

Bot:   🔧 Fix applied
         Analysis: JWT secret missing from config — middleware rejected all tokens
         Files changed:
           • auth/middleware.py  (modify)
           • config/settings.py  (modify)
         Summary: Added JWT_SECRET env var read; raises on missing value

       🧪 Running tests...

Bot:   [PNG screenshot — dark terminal, green ✓ PASSED]
       ✓ All tests passed  |  pytest tests/test_auth.py -v
```

---

## Inter-Agent Message Format

All agent-to-agent communication uses a typed JSON envelope — no natural language between agents:

```json
{
  "type": "REQUIREMENTS_CONFIRMED",
  "from_role": "BA",
  "to_role": "ORCHESTRATOR",
  "payload": { "brd": { "..." : "..." } },
  "metadata": {
    "timestamp": "2026-04-07T10:00:00",
    "project_id": "abc123",
    "session_id": "def456",
    "version": "1.0"
  }
}
```

---

## Troubleshooting

**`claude: command not found`**
Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`, then run `claude` to authenticate.

**Bot doesn't respond after restart**
Sessions are persisted in MongoDB. Check that `MONGODB_URI` is reachable: `python -c "import motor"`.

**`/fix` says project not found**
When using Docker, paths must be inside the container. Mount your project dir via `PROJECTS_DIR` and use `/projects/your-app` as the path.

**Screenshot font is pixelated**
The Dockerfile installs DejaVu fonts. If running locally, install `fonts-dejavu-core` (Linux) or the font will fall back to PIL's default bitmap font.

**Telegram `Bad Request: can't parse entities`**
The bot falls back to plain text automatically on MarkdownV2 parse errors. If a document looks garbled, this is the fallback kicking in — the content is still correct.

---

## Agent Persona Files

The `roles/` folder contains detailed persona definitions you can load directly into Claude Code CLI or Cursor as standalone agents:

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
| `roles/dev-frontend.md` | React / Vue / Angular |
| `roles/dev-fullstack.md` | Feature ownership |
| `roles/qa-engineer.md` | Test planning |
| `roles/qa-automation-engineer.md` | E2E automation |
| `roles/qa-performance-tester.md` | Load & performance testing |
| `roles/devops-engineer.md` | CI/CD & containers |
| `roles/devops-cloud-architect.md` | Cloud infrastructure |
| `roles/devops-sre.md` | Observability & SLOs |
