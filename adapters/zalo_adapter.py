"""
Zalo Official Account adapter.
Listens on a webhook (aiohttp) and sends via Zalo OA API v3.

Env vars required:
  ZALO_OA_ACCESS_TOKEN  — OA access token from Zalo OA dashboard
  ZALO_WEBHOOK_PORT     — port for the local webhook server (default 8080)
  ZALO_WEBHOOK_SECRET   — optional HMAC secret to verify Zalo payloads

Zalo OA API: https://developers.zalo.me/docs/official-account
"""
from __future__ import annotations
import hashlib
import hmac
import logging
import os
import aiohttp
from aiohttp import web
from adapters.base import ChatAdapter, IncomingMessage, OutgoingMessage, MessageHandler

log = logging.getLogger(__name__)

_SEND_URL = "https://openapi.zalo.me/v3.0/oa/message/cs"

class ZaloAdapter(ChatAdapter):
    def __init__(self, access_token: str, port: int = 8080, secret: str = ""):
        self.access_token = access_token
        self.port = port
        self.secret = secret
        self._handler: MessageHandler | None = None
        self._runner: web.AppRunner | None = None

    @property
    def platform_name(self) -> str:
        return "zalo"

    async def start(self, handler: MessageHandler) -> None:
        self._handler = handler
        app = web.Application()
        app.router.add_post("/zalo/webhook", self._on_webhook)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        await web.TCPSite(self._runner, "0.0.0.0", self.port).start()
        log.info("Zalo webhook listening on :%d/zalo/webhook", self.port)

    async def _on_webhook(self, request: web.Request) -> web.Response:
        body = await request.read()
        if self.secret:
            sig = request.headers.get("X-Zalo-Signature", "")
            expected = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return web.Response(status=403, text="Invalid signature")

        data = await request.json()
        event = data.get("event_name", "")

        if event in ("user_send_text", "oa_send_text"):
            sender = data.get("sender", {})
            text = data.get("message", {}).get("text", "")
            if text and self._handler:
                await self._handler(IncomingMessage(
                    chat_id=sender.get("id", ""),
                    text=text,
                    user_name=sender.get("display_name", "User"),
                    platform="zalo",
                    raw=data,
                ))
        return web.Response(text="OK")

    async def send(self, msg: OutgoingMessage) -> None:
        headers = {
            "access_token": self.access_token,
            "Content-Type": "application/json",
        }
        # Zalo doesn't support MarkdownV2 — strip escape characters
        plain_text = msg.text.replace("\\", "").replace("*", "").replace("`", "")

        body: dict = {
            "recipient": {"user_id": msg.chat_id},
            "message": {"text": plain_text[:2000]},
        }

        # Zalo quick replies for approval buttons
        if msg.inline_buttons:
            elements = [
                {"title": b["text"], "image_url": "", "subtitle": "",
                 "default_action": {"type": "oa.query.show", "payload": b["callback_data"]}}
                for row in msg.inline_buttons for b in row
            ]
            body["message"] = {
                "attachment": {
                    "type": "template",
                    "payload": {"template_type": "list", "elements": elements},
                }
            }

        async with aiohttp.ClientSession() as session:
            resp = await session.post(_SEND_URL, json=body, headers=headers)
            if resp.status != 200:
                log.error("Zalo send failed %d: %s", resp.status, await resp.text())

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
