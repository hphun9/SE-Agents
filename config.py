"""
Model assignment strategy — optimise cost vs capability.

Haiku  → fast, cheap   — simple Q&A, routing decisions
Sonnet → balanced      — structured document generation
Opus   → most capable  — complex reasoning, code generation
"""

# Model IDs
HAIKU  = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
OPUS   = "claude-opus-4-6"

# Per-task model assignment
MODELS: dict[str, str] = {
    # BA — clarification questions are simple; BRD needs more reasoning
    "ba_clarify":     HAIKU,
    "ba_brd":         SONNET,
    "ba_chat":        HAIKU,   # Secretary & consult routing (cheap + fast)

    # Planning phase — SA is the most complex (architecture decisions)
    "sa":             OPUS,
    "pm":             SONNET,
    "tech_lead":      OPUS,

    # Dev phase — backend code is complex; frontend / QA are moderate
    "dev_backend":    OPUS,
    "dev_frontend":   SONNET,
    "qa":             SONNET,

    # Fix flow — Opus for analysis + fix generation, Haiku for file triage
    "fixer":          OPUS,
    "fixer_triage":   HAIKU,
}

# BA clarification limits
MAX_BA_ROUNDS = 4
