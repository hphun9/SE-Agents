from __future__ import annotations
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler as TGMessageHandler,
    CommandHandler, CallbackQueryHandler, ContextTypes, filters,
)
from adapters.base import ChatAdapter, IncomingMessage, OutgoingMessage, MessageHandler

log = logging.getLogger(__name__)

def _esc(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))

class TelegramAdapter(ChatAdapter):
    def __init__(self, token: str):
        self.token = token
        self._app: Application | None = None
        self._handler: MessageHandler | None = None

    @property
    def platform_name(self) -> str:
        return "telegram"

    async def start(self, handler: MessageHandler) -> None:
        self._handler = handler
        self._app = Application.builder().token(self.token).build()

        # All text messages and commands route to the same handler
        async def _on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            if not update.message or not update.message.text:
                return
            await self._handler(IncomingMessage(
                chat_id=str(update.effective_chat.id),
                text=update.message.text,
                user_name=(update.effective_user.first_name or "User"),
                platform="telegram",
                raw=update.to_dict(),
            ))

        async def _on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            q = update.callback_query
            await q.answer()
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await self._handler(IncomingMessage(
                chat_id=str(update.effective_chat.id),
                text="",
                user_name=(update.effective_user.first_name or "User"),
                platform="telegram",
                callback_data=q.data,
                raw=update.to_dict(),
            ))

        for cmd in ("start", "new", "status", "help", "ask", "fix", "queue", "auto", "overnight"):
            self._app.add_handler(CommandHandler(cmd, _on_message))
        self._app.add_handler(TGMessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))
        self._app.add_handler(CallbackQueryHandler(_on_callback))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

    async def send(self, msg: OutgoingMessage) -> None:
        if self._app is None:
            return
        bot = self._app.bot
        cid = int(msg.chat_id)

        if msg.photo_bytes:
            try:
                await bot.send_photo(
                    chat_id=cid,
                    photo=msg.photo_bytes,
                    caption=msg.photo_caption or "",
                )
            except Exception as e:
                log.error("send_photo failed: %s", e)
            return

        reply_markup = None
        if msg.inline_buttons:
            keyboard = [
                [InlineKeyboardButton(b["text"], callback_data=b["callback_data"]) for b in row]
                for row in msg.inline_buttons
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

        # Split long messages
        from core.formatter import split_message
        chunks = split_message(msg.text)
        for i, chunk in enumerate(chunks):
            kb = reply_markup if i == len(chunks) - 1 else None
            try:
                await bot.send_message(
                    chat_id=cid, text=chunk,
                    parse_mode="MarkdownV2", reply_markup=kb,
                )
            except Exception:
                plain = chunk.replace("\\", "")
                try:
                    await bot.send_message(chat_id=cid, text=plain, reply_markup=kb)
                except Exception as e2:
                    log.error("send_message failed: %s", e2)

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
