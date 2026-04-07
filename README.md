# SE-Agents v1.0.0 — AI Software Development Team

> Describe a project in plain text. The AI team clarifies requirements, produces formal documents, lets you approve the plan, then the dev team writes real code to your disk — delivered across Telegram, Zalo, or your terminal.

---

## What's New in v1.0.0

| Feature | Detail |
|---------|--------|
| **Multi-channel adapters** | Telegram, Zalo OA, and local CLI all work simultaneously from the same codebase |
| **Workspace writer** | Agent output is written as real files to your project directory — not just chat messages |
| **Git auto-commit** | Each agent stage commits to the project's git repo automatically |
| **Autonomous / queue mode** | Queue multiple projects, auto-approve, and wake up to completed results |
| **Overnight command** | `/overnight <requirement>` — queue with full auto-approve and default tech prefs |
| **Crash recovery** | MongoDB checkpoints save pipeline state; failed projects can be retried |
| **Self-learning KB** | Every `/fix` run saves error + root cause + solution to MongoDB; future fixes search past solutions and never start from zero |

---

## How It Works

```
You (Telegram / Zalo / CLI)
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
   │                    OR  🤖 auto-approved (autonomous mode)
   ▼  ✅ Approved
┌──────────────────────────────────────────────────────────────┐
│  Backend Dev  ──► code + files written to disk      (Opus)   │
│  Frontend Dev ──► code + files written to disk      (Sonnet) │  ← parallel
│  QA           ──► test plan + test code             (Sonnet) │
└──────────────────────────────────────────────────────────────┘
   │
   ▼  📁 Real project files on your machine + git commits
   ▼  All documents delivered to your chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/fix flow  (works on any project — independent of pipeline)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/fix /projects/myapp <error description>
   ▼  Haiku triages relevant files  (cheap)
   ▼  Opus analyses + generates patch
   ▼  Writes fixed files to disk
   ▼  Runs test command via subprocess
   ▼  Renders terminal output as PNG  📸
   ▼  Sends screenshot to Telegram / Zalo / CLI
```

---

## Architecture

```
Telegram ──┐
  Zalo   ──┼──► adapters/    ──► Orchestrator ──► agents/
   CLI   ──┘    (base.py)        (queue, state       (BA, SA, PM, TL
                                  machine, auto)       Dev, QA, Fixer)
                                       │
                                       ▼
                                 workspace/
                                 (write files + git commit)
                                       │
                                       ▼
                                  MongoDB
                                 (sessions + checkpoints)
```

All adapters produce `IncomingMessage` and consume `OutgoingMessage`. The orchestrator never imports Telegram or Zalo — it only knows about the abstract adapter interface.

---

## Agents & Models

| Agent | Model | Task |
|-------|-------|------|
| **BA** — clarify | `claude-haiku-4-5` | Fast clarifying questions |
| **BA** — BRD | `claude-sonnet-4-6` | Business Requirements Document |
| **Solution Architect** | `claude-opus-4-6` | Architecture, ADRs, tech-stack decisions |
| **Project Manager** | `claude-sonnet-4-6` | Project plan, phases, risks, milestones |
| **Tech Lead** | `claude-opus-4-6` | API design, data models, technical spec |
| **Backend Dev** | `claude-opus-4-6` | Scaffold + real implementation code → written to disk |
| **Frontend Dev** | `claude-sonnet-4-6` | Components + real UI code → written to disk |
| **QA Engineer** | `claude-sonnet-4-6` | Test plan, test cases, CI config |
| **Fixer — triage** | `claude-haiku-4-5` | Identify relevant files cheaply |
| **Fixer — patch** | `claude-opus-4-6` | Analyse bug, generate & apply fix |

> All calls go through `claude -p` CLI — uses your **Claude Max subscription**, no API billing.

---

## Project Structure

```
se-agents/
│
├── main.py                      ← async entry point; loads adapters from env
├── config.py                    ← model assignments per task
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── adapters/                    ← one file per chat platform
│   ├── base.py                  ← ChatAdapter ABC + IncomingMessage / OutgoingMessage
│   ├── telegram_adapter.py      ← python-telegram-bot v21
│   ├── zalo_adapter.py          ← aiohttp webhook + Zalo OA API v3
│   └── cli_adapter.py           ← local terminal (for dev/testing)
│
├── workspace/                   ← write agent output as real project files
│   ├── writer.py                ← extract code blocks → files on disk
│   └── git_integration.py       ← async git init + commit per agent stage
│
├── core/
│   ├── models.py                ← AgentMessage, SessionState, QueuedProject
│   ├── claude.py                ← calls `claude -p` CLI
│   ├── storage.py               ← MongoDB session persistence (motor async)
│   ├── checkpoint.py            ← pipeline crash recovery
│   ├── knowledge_base.py        ← self-learning KB: save + search error/solution pairs
│   └── formatter.py             ← MarkdownV2 formatters per document type
│
├── agents/
│   ├── orchestrator.py          ← Orchestrator class: adapter-agnostic state machine
│   ├── ba.py                    ← BA: clarification loop → BRD
│   ├── sa.py                    ← SA: BRD → Architecture Document
│   ├── pm.py                    ← PM: BRD + Arch → Project Plan
│   ├── tech_lead.py             ← Tech Lead: → Technical Specification
│   ├── dev_backend.py           ← Backend Dev: → implementation guide + code
│   ├── dev_frontend.py          ← Frontend Dev: → implementation guide + code
│   ├── qa.py                    ← QA: → test plan + test code
│   ├── fixer.py                 ← /fix: triage files, generate & apply patch
│   ├── qa_runner.py             ← run tests, capture output, render PNG
│   └── consult.py               ← /ask: direct per-role consultation
│
├── bot/
│   └── telegram.py              ← DEPRECATED (v1.0.0) — use adapters/ instead
│
└── roles/                       ← 18 agent persona definitions (Claude Code / Cursor)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| AI | Claude Code CLI (`claude -p`) — Max subscription |
| Telegram | python-telegram-bot v21 (async) |
| Zalo | aiohttp webhook server + Zalo OA API v3 |
| Database | MongoDB via motor (async) |
| Screenshots | Pillow — terminal output as PNG |
| Async | asyncio + `asyncio.gather()` for parallel agents |
| Workspace | pathlib + subprocess git |
| Container | Docker + Docker Compose |

---

## Setup

### Option A — Docker (recommended)

```bash
# 1. Clone and configure
git clone https://github.com/hphun9/SE-Agents.git
cd SE-Agents
cp .env.example .env
# Edit .env — at minimum fill in TELEGRAM_BOT_TOKEN

# 2. Authenticate Claude Code on the HOST (one-time)
claude   # log in interactively, then Ctrl+C

# 3. Start everything
PROJECTS_DIR=/absolute/path/to/your/projects docker-compose up -d

# 4. Logs
docker-compose logs -f bot
```

Projects are mounted at `/projects` inside the container.
Use `/fix /projects/myapp ...` or `/overnight build a todo app at /projects/todo`.

---

### Option B — Local

```bash
# Install deps
pip install -r requirements.txt

# Install and authenticate Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude   # log in

# MongoDB
docker run -d -p 27017:27017 mongo

# Configure
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN (and optionally ZALO_OA_ACCESS_TOKEN or ENABLE_CLI=true)

# Run
python main.py
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | one of these three | — | From [@BotFather](https://t.me/BotFather) |
| `ZALO_OA_ACCESS_TOKEN` | one of these three | — | From Zalo OA dashboard |
| `ENABLE_CLI` | one of these three | `false` | Set `true` for terminal adapter |
| `ZALO_WEBHOOK_PORT` | | `8080` | Port for Zalo webhook server |
| `ZALO_WEBHOOK_SECRET` | | — | HMAC secret for Zalo payload verification |
| `MONGODB_URI` | ✅ | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB` | | `se_agents` | Database name |
| `PROJECTS_DIR` | | `/tmp/projects` | Directory for workspace file output |

At least one of `TELEGRAM_BOT_TOKEN`, `ZALO_OA_ACCESS_TOKEN`, or `ENABLE_CLI=true` must be set.

---

## Commands

| Command | Description |
|---------|-------------|
| _(any text)_ | Start a new project interactively |
| `/new` | Clear current session |
| `/status` | Show pipeline state, queue size, and mode |
| `/ask <role> <question>` | Consult an agent directly |
| `/fix <path> <error>` | Dev fixes a bug → QA tests → screenshot |
| `/queue <requirement>` | Queue a project |
| `/queue list` | Show the queue |
| `/queue clear` | Clear the queue |
| `/auto on\|off` | Toggle autonomous mode (auto-approve all) |
| `/overnight <requirement>` | Queue + auto-approve + default tech prefs |
| `/kb stats` | Knowledge base statistics (total, success rate, top error types) |
| `/kb search <query>` | Search past solutions in the knowledge base |
| `/help` | All commands + available `/ask` roles |

---

## `/ask` — Direct Agent Consultation

```
/ask ba    What requirements am I missing?
/ask sa    Microservices vs monolith for 10k users/day?
/ask lead  Review this API design: [paste design]
/ask dev   Fix this 401 error: [paste code]
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

If a session is active the agent automatically receives the relevant docs (BRD, tech spec, etc.) as context.

---

## Autonomous Mode

Enable auto-approve so the full pipeline runs without waiting for you:

```
/auto on

I want to build a SaaS invoicing app   ← starts immediately, no approval prompt
```

Or queue projects to run sequentially:

```
/queue Build a REST API for a bookshop
/queue Build an admin dashboard for the bookshop
/queue list    → 2 projects pending
```

Or use `/overnight` for fully unattended runs:

```
/overnight Build a task management SaaS with React + FastAPI
```

All three projects run back-to-back. When the queue finishes you get a summary:

```
🌅 Queue complete — 3/3 succeeded
✅ REST API for a bookshop
✅ Admin dashboard for the bookshop
✅ Task management SaaS
```

---

## Workspace Output

After dev agents finish, real files are written to `PROJECTS_DIR/<project-name>/`:

```
/projects/task-management-saas/
├── docs/
│   ├── 01-business-requirements.md
│   ├── 02-architecture.md
│   ├── 03-project-plan.md
│   ├── 04-technical-specification.md
│   ├── 05-backend-implementation.md
│   ├── 06-frontend-implementation.md
│   └── 07-test-plan.md
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   └── frontend/
│       └── src/
├── tests/
└── se-agents-manifest.json
```

Each stage also creates a git commit:

```
[SE-Agents/dev] 12 files written
```

---

## Self-Learning Knowledge Base

Every time `/fix` runs and QA confirms tests pass, the error + root cause + solution is saved to MongoDB. The **next** time a similar error appears — in any project — the fixer gets the past solution as context, so it never starts from zero on a problem it has already solved.

### How it works

```
/fix /projects/myapp  Getting 401 on POST /api/auth
   │
   ├─► 1. Search KB for similar past errors
   │       → Found: "JWT token not verified in middleware" (confidence 90%, used 3×)
   │       → Inject as context into Opus fix prompt
   │
   ├─► 2. Opus generates fix (guided by past solution)
   ├─► 3. Apply fix to disk
   ├─► 4. QA runs tests → screenshot
   │
   └─► 5. Save to KB:
           error_description, root_cause, solution_summary,
           tech_stack, fix_worked=True, confidence=0.7
```

Each subsequent reuse raises the confidence score by `+0.1` (capped at 1.0), so well-proven solutions naturally bubble up in search rankings.

### Knowledge Base schema

| Field | Description |
|-------|-------------|
| `error_type` | `auth` \| `database` \| `network` \| `config` \| `logic` \| `type` \| `syntax` \| `other` |
| `keywords` | Extracted by Haiku for fast text-index search |
| `tech_stack` | `["python", "fastapi", "jwt", ...]` |
| `root_cause` | What actually caused the error |
| `solution_summary` | What was done to fix it |
| `fix_worked` | `true` if QA passed after applying the fix |
| `confidence` | 0.0–1.0, increases each reuse |
| `use_count` | How many times this solution was applied |

### KB commands

```
/kb stats              → total entries, success rate, top error types & tech stacks
/kb search jwt 401     → search past solutions matching a query
```

### Example — KB growing over time

```
Week 1:  /fix ...  JWT 401 error              → saved (confidence 0.70)
Week 2:  /fix ...  same JWT pattern elsewhere → reused! confidence → 0.80
Week 3:  /fix ...  JWT 401 again              → confidence → 0.90, used 3×

/kb stats
  Total entries:   47
  Successful fixes: 41
  Success rate:    87.2%
  Top error types: auth (12), database (8), config (7)
  Top tech stacks: python (19), fastapi (11), react (9)
```

---

## Example Flows

### Interactive pipeline

```
You:   "Build a SaaS task manager for small dev teams"

BA:    Round 1 — clarifying:
         1. Web only or mobile too?
         2. Real-time or async?
         3. Integrations? (GitHub, Slack…)

You:   "Web only. Real-time. GitHub + Slack."

BA:    ✅ Requirements confirmed  →  [BRD]
SA:    [Architecture Document]
PM:    [Project Plan]
TL:    [Technical Specification]

Bot:   📋 Planning complete — approve or request changes?
       [✅ Approve]   [📝 Request Changes]

You:   ✅ Approve

Dev:   Backend guide + FastAPI code → written to /projects/task-manager/
Dev:   Frontend guide + React code  → written to /projects/task-manager/
QA:    Test plan + pytest tests     → written to /projects/task-manager/

Bot:   🎉 All done! 📁 /projects/task-manager
```

### Bug fix (with KB context)

```
You:   /fix /projects/myapp Getting 401 on every POST /api/auth/login

Bot:   🔍 Dev agent is analysing /projects/myapp...
Bot:   🧠 Found 2 similar past solution(s) in KB — injecting as context.

Bot:   🔧 Fix applied
         Files changed:
           • auth/middleware.py  (modify)
           • config/settings.py  (modify)

       🧪 Running tests...

Bot:   [PNG screenshot — dark terminal, green ✓ PASSED]
```

### Overnight / autonomous

```
/auto on
/overnight Build a REST bookshop API with FastAPI + PostgreSQL
/overnight Build a React admin dashboard for the bookshop API

→ Both projects run while you sleep.
→ Files appear in /projects/ with git history.
→ You receive a summary in the morning.
```

---

## Inter-Agent Message Format

All agent-to-agent communication uses typed JSON envelopes — no natural language between agents:

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

## Adding a New Chat Channel

1. Create `adapters/myplatform_adapter.py` implementing `ChatAdapter`
2. Convert platform events → `IncomingMessage` in `start()`
3. Convert `OutgoingMessage` → platform API calls in `send()`
4. Add the env var check in `main.py`

The orchestrator and all agents need zero changes.

---

## Troubleshooting

**`claude: command not found`**
Install: `npm install -g @anthropic-ai/claude-code`, then run `claude` to authenticate.

**No adapters configured**
Set at least one of: `TELEGRAM_BOT_TOKEN`, `ZALO_OA_ACCESS_TOKEN`, or `ENABLE_CLI=true`.

**`/fix` says project not found**
In Docker, paths must be inside the container. Mount via `PROJECTS_DIR` and use `/projects/myapp`.

**Screenshot font is pixelated**
The Dockerfile installs DejaVu fonts. Running locally: install `fonts-dejavu-core` (Linux) or the fallback bitmap font is used.

**Zalo messages not received**
Your webhook URL must be publicly reachable and registered in the Zalo OA dashboard. Use `ngrok` for local development.

**Session lost after restart**
Sessions are persisted in MongoDB. Verify `MONGODB_URI` is reachable: `docker-compose ps mongo`.

---

## Agent Persona Files

The `roles/` folder contains 18 detailed persona definitions for use as standalone agents in Claude Code CLI or Cursor:

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
