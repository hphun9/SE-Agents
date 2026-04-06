/**
 * Telegram Bot
 *
 * Routes user messages to the Orchestrator based on session state.
 * All user-facing communication goes through here.
 */

import TelegramBot from 'node-telegram-bot-api';
import {
  getSession,
  startProject,
  handleClarificationAnswer,
  clearSession,
} from '../agents/orchestrator.js';
import {
  formatClarificationRequest,
  formatBRDSummary,
  splitMessage,
} from '../utils/formatter.js';

export function createBot(token: string): TelegramBot {
  const bot = new TelegramBot(token, { polling: true });

  // ─── Commands ──────────────────────────────────────────────────────────────

  bot.onText(/\/start/, async (msg) => {
    await send(
      bot,
      msg.chat.id,
      `👋 *Welcome to SE\\-Agents\\!*\n\n` +
      `I'm your AI\\-powered software development team\\. I have:\n` +
      `• 🔍 *BA* — Gathers & clarifies requirements\n` +
      `• 🏗️ *SA* — Designs the architecture\n` +
      `• 📅 *PM* — Creates the project plan\n` +
      `• ⚙️ *Tech Lead* — Writes the technical spec\n\n` +
      `*Just send me your project requirement to get started\\!*\n\n` +
      `_e\\.g\\. "I want to build a task management app for small teams"_`
    );
  });

  bot.onText(/\/new/, async (msg) => {
    clearSession(msg.chat.id);
    await send(
      bot,
      msg.chat.id,
      `🆕 *New project started\\.*\n\nSend me your requirement and the team will get to work\\!`
    );
  });

  bot.onText(/\/status/, async (msg) => {
    const session = getSession(msg.chat.id);
    if (!session) {
      await send(bot, msg.chat.id, `📭 No active project\\. Send a requirement to start one\\.`);
      return;
    }

    const stateLabels: Record<string, string> = {
      BA_CLARIFYING: '🔍 BA is gathering requirements',
      SA_PROCESSING: '🏗️ SA is designing architecture',
      PM_PROCESSING: '📅 PM is creating project plan',
      TECH_LEAD_PROCESSING: '⚙️ Tech Lead is writing spec',
      COMPLETE: '✅ Pipeline complete',
    };

    const label = stateLabels[session.state] ?? session.state;
    const rounds = session.clarification_rounds.length;
    await send(
      bot,
      msg.chat.id,
      `📊 *Project Status*\n\n` +
      `*ID:* \`${session.project_id.slice(0, 8)}\`\n` +
      `*State:* ${label}\n` +
      `*BA rounds:* ${rounds}\n` +
      `*Started:* ${session.created_at.slice(0, 10)}`
    );
  });

  bot.onText(/\/help/, async (msg) => {
    await send(
      bot,
      msg.chat.id,
      `📖 *Commands*\n\n` +
      `/start — Welcome message\n` +
      `/new — Start a fresh project\n` +
      `/status — Check current pipeline status\n` +
      `/help — This message\n\n` +
      `*Usage:* Just send your requirement as a message to begin\\!`
    );
  });

  // ─── Message Handler ───────────────────────────────────────────────────────

  bot.on('message', async (msg) => {
    if (!msg.text || msg.text.startsWith('/')) return;

    const chatId = msg.chat.id;
    const session = getSession(chatId);

    if (!session || session.state === 'COMPLETE') {
      // No active session or previous one completed — start fresh
      if (session?.state === 'COMPLETE') {
        clearSession(chatId);
      }
      await handleNewProject(bot, chatId, msg.text);
    } else if (session.state === 'BA_CLARIFYING') {
      await handleClarificationReply(bot, chatId, msg.text);
    } else {
      // Pipeline is running — let the user know
      await send(
        bot,
        chatId,
        `⏳ The team is still working on your project\\. Please wait\\.\\.\\.`
      );
    }
  });

  return bot;
}

// ─── Project Start ─────────────────────────────────────────────────────────

async function handleNewProject(
  bot: TelegramBot,
  chatId: number,
  requirement: string
): Promise<void> {
  await send(
    bot,
    chatId,
    `🚀 *Starting your project\\!*\n\nYour requirement:\n_${escapeMarkdown(requirement)}_\n\nThe team is spinning up\\.\\.\\.`
  );

  await startProject(
    chatId,
    requirement,

    // onProgress
    async (msg) => {
      await send(bot, chatId, msg);
    },

    // onClarify — BA asking questions
    async (questions, analysis, iteration) => {
      const payload = {
        status: 'NEEDS_CLARIFICATION' as const,
        analysis,
        questions,
        context: '',
        iteration,
      };
      const formatted = formatClarificationRequest(payload);
      await send(bot, chatId, formatted);
    },

    // onDocument — agent produced a document
    async (docType, chunks) => {
      await send(bot, chatId, `\n📄 *${escapeMarkdown(docType)}*`);
      for (const chunk of chunks) {
        await send(bot, chatId, chunk);
      }
    },

    // onComplete
    async () => {
      await send(
        bot,
        chatId,
        `🎉 *All done\\!*\n\n` +
        `Your project documents have been delivered:\n` +
        `• ✅ Business Requirements Document\n` +
        `• 🏗️ Architecture Document\n` +
        `• 📅 Project Plan\n` +
        `• ⚙️ Technical Specification\n\n` +
        `Send a new requirement to start another project, or /new to reset\\.`
      );
    },

    // onError
    async (err) => {
      await send(bot, chatId, `❌ *Error:* ${escapeMarkdown(err)}`);
    }
  );
}

// ─── Clarification Reply ──────────────────────────────────────────────────

async function handleClarificationReply(
  bot: TelegramBot,
  chatId: number,
  answers: string
): Promise<void> {
  await handleClarificationAnswer(
    chatId,
    answers,

    // onProgress
    async (msg) => {
      await send(bot, chatId, msg);
    },

    // onClarify
    async (questions, analysis, iteration) => {
      const payload = {
        status: 'NEEDS_CLARIFICATION' as const,
        analysis,
        questions,
        context: '',
        iteration,
      };
      const formatted = formatClarificationRequest(payload);
      await send(bot, chatId, formatted);
    },

    // onDocument
    async (docType, chunks) => {
      await send(bot, chatId, `\n📄 *${escapeMarkdown(docType)}*`);
      for (const chunk of chunks) {
        await send(bot, chatId, chunk);
      }
    },

    // onComplete
    async () => {
      await send(
        bot,
        chatId,
        `🎉 *All done\\!*\n\n` +
        `Your project documents have been delivered:\n` +
        `• ✅ Business Requirements Document\n` +
        `• 🏗️ Architecture Document\n` +
        `• 📅 Project Plan\n` +
        `• ⚙️ Technical Specification\n\n` +
        `Send a new requirement to start another project, or /new to reset\\.`
      );
    },

    // onError
    async (err) => {
      await send(bot, chatId, `❌ *Error:* ${escapeMarkdown(err)}`);
    }
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────

async function send(bot: TelegramBot, chatId: number, text: string): Promise<void> {
  const chunks = splitMessage(text);
  for (const chunk of chunks) {
    try {
      await bot.sendMessage(chatId, chunk, { parse_mode: 'MarkdownV2' });
    } catch {
      // Fallback: send as plain text if MarkdownV2 fails
      try {
        await bot.sendMessage(chatId, chunk.replace(/[\\*_[\]()~`>#+=|{}.!-]/g, ''));
      } catch (err2) {
        console.error('Failed to send message:', err2);
      }
    }
  }
}

function escapeMarkdown(text: string): string {
  return text.replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, '\\$&');
}
