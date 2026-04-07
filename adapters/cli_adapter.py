"""Local terminal adapter — no external service needed. Great for development."""
from __future__ import annotations
import asyncio
import logging
from adapters.base import ChatAdapter, IncomingMessage, OutgoingMessage, MessageHandler

log = logging.getLogger(__name__)
_CLI_CHAT_ID = "cli-local"

class CLIAdapter(ChatAdapter):
    def __init__(self, user_name: str = "dev"):
        self.user_name = user_name
        self._handler: MessageHandler | None = None
        self._running = False

    @property
    def platform_name(self) -> str:
        return "cli"

    async def start(self, handler: MessageHandler) -> None:
        self._handler = handler
        self._running = True
        asyncio.create_task(self._input_loop())
        print("\n🤖 SE-Agents CLI ready. Type your requirement or a command.\n")

    async def _input_loop(self) -> None:
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                text = await loop.run_in_executor(None, input, "You: ")
            except (EOFError, KeyboardInterrupt):
                break
            if text.strip() and self._handler:
                await self._handler(IncomingMessage(
                    chat_id=_CLI_CHAT_ID,
                    text=text.strip(),
                    user_name=self.user_name,
                    platform="cli",
                ))

    async def send(self, msg: OutgoingMessage) -> None:
        # Strip MarkdownV2 escaping for terminal
        text = msg.text.replace("\\", "")
        print(f"\n{'─'*60}\n{text}")

        if msg.photo_bytes:
            print("[QA Screenshot: saved to /tmp/se-agents-qa-screenshot.png]")
            try:
                with open("/tmp/se-agents-qa-screenshot.png", "wb") as f:
                    f.write(msg.photo_bytes)
            except Exception:
                pass

        if msg.inline_buttons:
            flat = [b for row in msg.inline_buttons for b in row]
            for i, btn in enumerate(flat):
                print(f"  [{i+1}] {btn['text']}")
            print(f"{'─'*60}")
            if self._handler:
                loop = asyncio.get_event_loop()
                choice = await loop.run_in_executor(None, input, "Choose (number): ")
                if choice.strip().isdigit():
                    idx = int(choice.strip()) - 1
                    if 0 <= idx < len(flat):
                        await self._handler(IncomingMessage(
                            chat_id=_CLI_CHAT_ID, text="",
                            user_name=self.user_name, platform="cli",
                            callback_data=flat[idx]["callback_data"],
                        ))
        else:
            print(f"{'─'*60}\n")

    async def stop(self) -> None:
        self._running = False
