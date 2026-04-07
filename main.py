"""SE-Agents v1.0.0 — Multi-channel AI development team."""
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("se_agents")


async def main() -> None:
    from core.storage import init_db
    from core.knowledge_base import init_kb
    await init_db()
    await init_kb()
    log.info("MongoDB initialised (sessions + knowledge base)")

    from agents.orchestrator import Orchestrator
    orchestrator = Orchestrator()

    adapters = []

    if token := os.getenv("TELEGRAM_BOT_TOKEN"):
        from adapters.telegram_adapter import TelegramAdapter
        adapters.append(TelegramAdapter(token))

    if token := os.getenv("ZALO_OA_ACCESS_TOKEN"):
        from adapters.zalo_adapter import ZaloAdapter
        port = int(os.getenv("ZALO_WEBHOOK_PORT", "8080"))
        adapters.append(ZaloAdapter(token, port, os.getenv("ZALO_WEBHOOK_SECRET", "")))

    if os.getenv("ENABLE_CLI", "false").lower() == "true":
        from adapters.cli_adapter import CLIAdapter
        adapters.append(CLIAdapter())

    if not adapters:
        log.error("No adapters configured! Set TELEGRAM_BOT_TOKEN, ZALO_OA_ACCESS_TOKEN, or ENABLE_CLI=true")
        return

    for adapter in adapters:
        orchestrator.register_adapter(adapter)
        await adapter.start(orchestrator.handle_message)
        log.info("✅ %s adapter started", adapter.platform_name)

    log.info("SE-Agents v1.0.0 running — %d adapter(s) active", len(adapters))
    try:
        await asyncio.Event().wait()
    finally:
        for adapter in adapters:
            await adapter.stop()


if __name__ == "__main__":
    asyncio.run(main())
