"""
Abstract chat adapter — one implementation per platform.
All agents communicate through OutgoingMessage; all input arrives as IncomingMessage.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

@dataclass
class IncomingMessage:
    chat_id: str          # platform-specific user/chat ID (always string)
    text: str
    user_name: str
    platform: str         # "telegram" | "zalo" | "cli"
    callback_data: Optional[str] = None
    raw: Optional[dict] = field(default=None, repr=False)

@dataclass
class OutgoingMessage:
    chat_id: str
    text: str
    parse_mode: Optional[str] = "markdown"   # "markdown" | "html" | None
    inline_buttons: Optional[list[list[dict]]] = None  # [[{"text":"..","callback_data":".."}]]
    photo_bytes: Optional[bytes] = None      # PNG bytes → send_photo
    photo_caption: Optional[str] = None

MessageHandler = Callable[[IncomingMessage], Awaitable[None]]

class ChatAdapter(ABC):
    @abstractmethod
    async def start(self, handler: MessageHandler) -> None: ...
    @abstractmethod
    async def send(self, msg: OutgoingMessage) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        """Send a transient chat action (e.g. 'typing'). No-op by default."""
        pass
