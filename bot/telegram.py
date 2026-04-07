"""
Telegram Bot

Routes user messages to the Orchestrator based on session state.
Uses inline keyboard buttons for the approval gate.
All user-visible text is natural language; inter-agent traffic stays JSON.
"""

from __future__ import annotations
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from agents.orchestrator import (
    get_session, clear_session,
    start_project,
    handle_clarification_answer,
    handle_approval,
    handle_change_request,
    handle_change_feedback,
)
from agents.consult import consult_agent, resolve_role, list_roles
from core.models import SessionState
from core.formatter import split_message

log = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _send(bot, chat_id: int, text: str) -> None:
    """Send a MarkdownV2 message, falling back to plain text on parse error."""
    for chunk in split_message(text):
        try:
            await bot.send_message(chat_id, chunk, parse_mode="MarkdownV2")
        except Exception:
            # Strip all MarkdownV2 special chars on failure
            plain = chunk.replace("\\", "")
            try:
                await bot.send_message(chat_id, plain)
            except Exception as e2:
                log.error("Failed to send message to %s: %s", chat_id, e2)


def _approval_keyboard(project_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve — Start Dev Team",
                             callback_data=f"approve:{project_id}"),
        InlineKeyboardButton("📝 Request Changes",
                             callback_data=f"changes:{project_id}"),
    ]])


# ─── Callbacks passed to Orchestrator ────────────────────────────────────────

def _make_callbacks(bot, chat_id: int):
    async def on_progress(msg: str) -> None:
        await _send(bot, chat_id, msg)

    async def on_clarify(questions: list[str], analysis: str, iteration: int) -> None:
        from core.formatter import fmt_clarification
        await _send(bot, chat_id, fmt_clarification(analysis, questions, iteration))

    async def on_document(doc_type: str, chunks: list[str]) -> None:
        await _send(bot, chat_id, f"\n📄 *{_esc(doc_type)}*")
        for chunk in chunks:
            await _send(bot, chat_id, chunk)

    async def on_approval_needed(project_id: str) -> None:
        text = (
            "📋 *Planning complete\\!*\n\n"
            "The team has produced:\n"
            "• ✅ Business Requirements Document\n"
            "• 🏗️ Architecture Document\n"
            "• 📅 Project Plan\n"
            "• ⚙️ Technical Specification\n\n"
            "Ready to hand off to the dev team?"
        )
        await bot.send_message(
            chat_id, text,
            parse_mode="MarkdownV2",
            reply_markup=_approval_keyboard(project_id),
        )

    async def on_complete() -> None:
        await _send(
            bot, chat_id,
            "🎉 *All done\\!*\n\n"
            "Your full project package:\n"
            "• ✅ BRD\n"
            "• 🏗️ Architecture\n"
            "• 📅 Project Plan\n"
            "• ⚙️ Tech Spec\n"
            "• 🔧 Backend Implementation Guide\n"
            "• 🎨 Frontend Implementation Guide\n"
            "• 🧪 QA Plan\n\n"
            "Send a new requirement or /new to start another project\\.",
        )

    async def on_error(err: str) -> None:
        await _send(bot, chat_id, f"❌ *Error:* {_esc(err)}")

    return on_progress, on_clarify, on_document, on_approval_needed, on_complete, on_error


# ─── Command handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(
        context.bot, update.effective_chat.id,
        "👋 *Welcome to SE\\-Agents\\!*\n\n"
        "I'm your AI\\-powered software development team:\n\n"
        "🔍 *BA* — Clarifies requirements \\(Haiku/Sonnet\\)\n"
        "🏗️ *SA* — Designs architecture \\(Opus\\)\n"
        "📅 *PM* — Creates project plan \\(Sonnet\\)\n"
        "⚙️ *Tech Lead* — Writes technical spec \\(Opus\\)\n"
        "🔧 *Backend Dev* — Implements backend \\(Opus\\)\n"
        "🎨 *Frontend Dev* — Implements frontend \\(Sonnet\\)\n"
        "🧪 *QA* — Writes test plan \\(Sonnet\\)\n\n"
        "Just send me your project requirement to begin\\!",
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_session(update.effective_chat.id)
    await _send(context.bot, update.effective_chat.id,
                "🆕 Session cleared\\. Send your requirement to start a new project\\.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    if not session:
        await _send(context.bot, chat_id,
                    "📭 No active project\\. Send a requirement to start one\\.")
        return
    labels = {
        SessionState.BA_CLARIFYING:           "🔍 BA is gathering requirements",
        SessionState.SA_PROCESSING:           "🏗️ SA is designing architecture",
        SessionState.PM_PROCESSING:           "📅 PM is creating project plan",
        SessionState.TECH_LEAD_PROCESSING:    "⚙️ Tech Lead is writing spec",
        SessionState.AWAITING_APPROVAL:       "🔔 Awaiting your approval",
        SessionState.FEEDBACK_PENDING:        "📝 Awaiting your change feedback",
        SessionState.DEV_PROCESSING:          "💻 Dev team is implementing",
        SessionState.QA_PROCESSING:           "🧪 QA is writing test plan",
        SessionState.COMPLETE:                "✅ Pipeline complete",
    }
    label = labels.get(session.state, session.state)
    await _send(
        context.bot, chat_id,
        f"📊 *Project Status*\n\n"
        f"*ID:* `{_esc(session.project_id[:8])}`\n"
        f"*State:* {_esc(label)}\n"
        f"*BA rounds:* {len(session.clarification_rounds)}\n"
        f"*Started:* {_esc(session.created_at[:10])}",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(
        context.bot, update.effective_chat.id,
        "📖 *Commands*\n\n"
        "/start — Welcome\n"
        "/new — Start fresh project\n"
        "/status — Pipeline status\n"
        "/ask \\<role\\> \\<message\\> — Consult a specific agent directly\n"
        "/help — This message\n\n"
        "Just send your requirement as a plain message to begin\\!\n\n"
        f"*Available roles for /ask:*\n{list_roles()}",
    )


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Directly consult a specific agent role.

    Usage: /ask <role> <message>
    Example: /ask dev fix the auth bug — getting 401 on every request
    """
    chat_id = update.effective_chat.id
    args = (context.args or [])

    if not args:
        await _send(
            context.bot, chat_id,
            "Usage: `/ask <role> <message>`\n\n"
            f"*Available roles:*\n{list_roles()}",
        )
        return

    role_key = resolve_role(args[0])
    if not role_key:
        await _send(
            context.bot, chat_id,
            f"Unknown role: `{_esc(args[0])}`\n\n"
            f"*Available roles:*\n{list_roles()}",
        )
        return

    question = " ".join(args[1:]).strip()
    if not question:
        await _send(context.bot, chat_id, "Please include your question after the role name\\.")
        return

    session = get_session(chat_id)

    async def _run() -> None:
        await _send(context.bot, chat_id, f"⏳ Consulting {_esc(args[0])}\\.\\.\\.")
        try:
            response = await consult_agent(role_key, question, session)
            await _send(context.bot, chat_id, response)
        except Exception as exc:
            log.exception("consult_agent error")
            await _send(context.bot, chat_id, f"❌ *Error:* {_esc(str(exc))}")

    asyncio.create_task(_run())


# ─── Message handler ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    text     = update.message.text or ""
    session  = get_session(chat_id)
    bot      = context.bot

    cbs = _make_callbacks(bot, chat_id)

    if not session or session.state == SessionState.COMPLETE:
        # Fresh start
        if session and session.state == SessionState.COMPLETE:
            clear_session(chat_id)
        await _send(bot, chat_id,
                    f"🚀 *Starting your project\\!*\n\n"
                    f"Requirement:\n_{_esc(text)}_\n\nThe team is spinning up\\.\\.\\."),
        asyncio.create_task(start_project(chat_id, text, *cbs))

    elif session.state == SessionState.BA_CLARIFYING:
        asyncio.create_task(handle_clarification_answer(chat_id, text, *cbs))

    elif session.state == SessionState.FEEDBACK_PENDING:
        on_progress, _, on_document, on_approval_needed, on_complete, on_error = cbs
        asyncio.create_task(
            handle_change_feedback(
                chat_id, text,
                on_progress, on_document, on_approval_needed, on_complete, on_error,
            )
        )

    else:
        await _send(bot, chat_id,
                    f"⏳ The team is still working\\. Current state: *{_esc(session.state)}*")


# ─── Inline button handler ────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    chat_id = query.message.chat_id
    bot     = context.bot
    data    = query.data or ""

    await query.answer()   # remove loading spinner

    on_progress, _, on_document, on_approval_needed, on_complete, on_error = _make_callbacks(bot, chat_id)

    if data.startswith("approve:"):
        await query.edit_message_reply_markup(reply_markup=None)  # remove buttons
        await _send(bot, chat_id, "✅ *Approved\\! Handing off to the dev team\\.\\.\\.*")
        asyncio.create_task(
            handle_approval(chat_id, on_progress, on_document, on_complete, on_error)
        )

    elif data.startswith("changes:"):
        await query.edit_message_reply_markup(reply_markup=None)
        await handle_change_request(chat_id)
        await _send(
            bot, chat_id,
            "📝 *What would you like to change?*\n\n"
            "Describe your feedback and the team \\(SA, PM, Tech Lead\\) will revise the documents\\.",
        )


# ─── Bot factory ─────────────────────────────────────────────────────────────

def create_app(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("new",    cmd_new))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ask",    cmd_ask))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    return app


# ─── Util ─────────────────────────────────────────────────────────────────────

import re as _re

def _esc(text: str) -> str:
    return _re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))
