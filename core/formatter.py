"""
Format agent JSON outputs as Telegram MarkdownV2 messages.
Telegram limit: 4096 chars/message — we chunk automatically.
"""

from __future__ import annotations
import re

MAX_MSG = 4_000


def split_message(text: str) -> list[str]:
    if len(text) <= MAX_MSG:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        addition = ("\n" if current else "") + line
        if len(current) + len(addition) > MAX_MSG:
            chunks.append(current)
            current = line
        else:
            current += addition
    if current:
        chunks.append(current)
    return chunks


def esc(text: str) -> str:
    """Escape special MarkdownV2 chars."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


# ─── Per-document formatters ─────────────────────────────────────────────────

def fmt_clarification(analysis: str, questions: list[str], iteration: int) -> list[str]:
    lines = [
        f"🔍 *Requirements Analysis — Round {iteration}*",
        "",
        f"*What I understand so far:*",
        esc(analysis),
        "",
        f"*I need clarification on:*",
    ]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}\\. {esc(q)}")
    lines += ["", "_Please answer all questions in one message\\._"]
    return split_message("\n".join(lines))


def fmt_brd(brd: dict) -> list[str]:
    frs = brd.get("functional_requirements", [])
    us  = brd.get("user_stories", [])
    lines = [
        f"✅ *Business Requirements Document*",
        f"📌 *{esc(brd.get('title', ''))}*",
        "",
        "*Overview*",
        esc(brd.get("overview", "")),
        "",
        "*Problem Statement*",
        esc(brd.get("problem_statement", "")),
        "",
        f"*Goals \\({len(brd.get('goals', []))}\\)*",
        *[f"• {esc(g)}" for g in brd.get("goals", [])],
        "",
        f"*Functional Requirements \\({len(frs)}\\)*",
        *[f"• \\[{r['priority']}\\] {esc(r['title'])}" for r in frs[:6]],
        *(["_…and more_"] if len(frs) > 6 else []),
        "",
        f"*User Stories \\({len(us)}\\)*",
        *[f"• As a {esc(s['as_a'])}, I want {esc(s['i_want'])}" for s in us[:4]],
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_architecture(doc: dict) -> list[str]:
    stack = doc.get("tech_stack", [])
    comps = doc.get("components", [])
    adrs  = doc.get("adrs", [])
    lines = [
        "🏗️ *Architecture Document*",
        "",
        f"*Pattern:* {esc(doc.get('architecture_pattern', ''))}",
        "",
        "*System Overview*",
        esc(doc.get("system_overview", "")),
        "",
        f"*Tech Stack \\({len(stack)} layers\\)*",
        *[f"• *{esc(t['layer'])}*: {esc(t['technology'])} — {esc(t['rationale'])}" for t in stack],
        "",
        f"*Components \\({len(comps)}\\)*",
        *[f"• *{esc(c['name'])}* \\({esc(c['type'])}\\): {esc(c['responsibility'])}" for c in comps],
        "",
        "*Security Considerations*",
        *[f"• {esc(s)}" for s in doc.get("security_considerations", [])],
        "",
        f"*Architecture Decisions \\({len(adrs)} ADRs\\)*",
        *[f"• \\[{a['status']}\\] {esc(a['title'])}" for a in adrs],
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_project_plan(plan: dict) -> list[str]:
    phases = plan.get("phases", [])
    team   = plan.get("team_structure", [])
    risks  = plan.get("risks", [])
    lines = [
        "📅 *Project Plan*",
        f"📌 *{esc(plan.get('project_name', ''))}*",
        "",
        f"*Methodology:* {esc(plan.get('methodology', ''))}",
        f"*Duration:* {plan.get('duration_weeks', '?')} weeks",
        "",
        f"*Phases \\({len(phases)}\\)*",
        *[f"• *{esc(p['name'])}* \\({p['duration_weeks']}w\\): {esc(p['description'])}" for p in phases],
        "",
        "*Team Structure*",
        *[f"• {t['count']}× *{esc(t['role'])}*" for t in team],
        "",
        "*Key Milestones*",
        *[f"• Week {m['week']}: {esc(m['name'])}" for m in plan.get("milestones", [])],
        "",
        f"*Risks \\({len(risks)}\\)*",
        *[f"• \\[{r['probability']}/{r['impact']}\\] {esc(r['description'])}" for r in risks[:5]],
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_tech_spec(spec: dict) -> list[str]:
    endpoints = spec.get("api_design", [])
    models    = spec.get("data_models", [])
    sprints   = spec.get("sprint_plan", [])
    lines = [
        "⚙️ *Technical Specification*",
        "",
        esc(spec.get("overview", "")),
        "",
        f"*Development Workflow*",
        esc(spec.get("development_workflow", "")),
        "",
        f"*API Endpoints \\({len(endpoints)}\\)*",
        *[f"• `{esc(e['method'])} {esc(e['path'])}` — {esc(e['description'])}" for e in endpoints[:6]],
        *(["_…and more_"] if len(endpoints) > 6 else []),
        "",
        f"*Data Models \\({len(models)}\\)*",
        *[f"• *{esc(m['name'])}*: {len(m.get('fields', []))} fields" for m in models],
        "",
        f"*Sprint Plan \\({len(sprints)} sprints\\)*",
        *[f"• Sprint {s['sprint']} \\({s['story_points']}pts\\): {esc(s['goal'])}" for s in sprints],
        "",
        "*Testing Strategy*",
        esc(spec.get("testing_strategy", "")),
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_backend_impl(impl: dict) -> list[str]:
    files = impl.get("key_files", [])
    lines = [
        "🔧 *Backend Implementation Guide*",
        "",
        esc(impl.get("overview", "")),
        "",
        "*Setup Guide*",
        esc(impl.get("setup_guide", "")),
        "",
        f"*Key Files \\({len(files)}\\)*",
        *[f"• `{esc(f['path'])}` — {esc(f['purpose'])}" for f in files],
        "",
        "*Database Setup*",
        esc(impl.get("database_setup", "")),
        "",
        "*Environment Variables*",
        *[f"• `{esc(v)}`" for v in impl.get("environment_variables", [])],
        "",
        "*Deployment Notes*",
        esc(impl.get("deployment_notes", "")),
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_frontend_impl(impl: dict) -> list[str]:
    comps = impl.get("key_components", [])
    lines = [
        "🎨 *Frontend Implementation Guide*",
        "",
        esc(impl.get("overview", "")),
        "",
        "*Setup Guide*",
        esc(impl.get("setup_guide", "")),
        "",
        f"*Key Components \\({len(comps)}\\)*",
        *[f"• *{esc(c['name'])}* — {esc(c['purpose'])}" for c in comps],
        "",
        "*State Management*",
        esc(impl.get("state_management", "")),
        "",
        "*Routing Structure*",
        *[f"• `{esc(r)}`" for r in impl.get("routing_structure", [])],
        "",
        "*Deployment Notes*",
        esc(impl.get("deployment_notes", "")),
    ]
    return split_message("\n".join(filter(None, lines)))


def fmt_qa_plan(plan: dict) -> list[str]:
    suites = plan.get("test_suites", [])
    lines = [
        "🧪 *QA Plan*",
        "",
        esc(plan.get("strategy_overview", "")),
        "",
        f"*Test Framework:* {esc(plan.get('test_framework', ''))}",
        "",
        f"*Test Suites \\({len(suites)}\\)*",
        *[f"• *{esc(s['name'])}* \\({s['type']}\\): {len(s.get('cases', []))} cases" for s in suites],
        "",
        "*Automation Setup*",
        esc(plan.get("automation_setup", "")),
        "",
        "*Coverage Targets*",
        *[f"• {esc(k)}: {esc(str(v))}" for k, v in plan.get("coverage_targets", {}).items()],
        "",
        "*CI Integration*",
        esc(plan.get("ci_integration", "")),
    ]
    return split_message("\n".join(filter(None, lines)))
