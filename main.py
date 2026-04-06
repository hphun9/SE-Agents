"""SE-Agents — Multi-agent software development team via Telegram."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("se_agents")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


def main() -> None:
    telegram_token = _require("TELEGRAM_BOT_TOKEN")

    log.info("Starting SE-Agents")
    log.info("Pipeline: BA(Haiku/Sonnet) → SA(Opus) → PM(Sonnet) → Tech Lead(Opus)")
    log.info("          → [USER APPROVAL]")
    log.info("          → Backend Dev(Opus) ‖ Frontend Dev(Sonnet) → QA(Sonnet)")

    from bot.telegram import create_app
    app = create_app(telegram_token)
    log.info("Bot is running — send a message on Telegram to start")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
