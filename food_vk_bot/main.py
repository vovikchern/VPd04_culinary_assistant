"""Точка входа VK-бота «Кулинарный помощник».

Запуск из корня проекта:
    python food_vk_bot/main.py
или:
    python -m food_vk_bot.main
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

#: Корень проекта — чтобы запуск `python food_vk_bot/main.py` видел
#: пакеты spoonacular_api, mymemory_api и food_vk_bot
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
load_dotenv()

from food_vk_bot.bot import attach_http_client, create_bot  # noqa: E402
from food_vk_bot.context import init_context  # noqa: E402
from food_vk_bot.handlers import (  # noqa: E402
    by_ingredients,
    fallback,
    help,
    menu,
    recipe_card,
    search,
)

#: Порядок загрузки лейблеров ВАЖЕН: сначала payload-кнопки,
#: затем state-хендлеры, последним — fallback (state=None)
LABELERS = (
    menu.bl,
    help.bl,
    by_ingredients.bl,
    search.bl,
    recipe_card.bl,
    fallback.bl,
)


def main() -> None:
    """Собирает бота, подключает хендлеры и запускает Long Poll."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("vkbottle").setLevel(logging.WARNING)

    bot = create_bot()
    init_context(bot)
    for labeler in LABELERS:
        bot.labeler.load(labeler)
    # SSL-клиент подключается внутри event loop (aiohttp.TCPConnector
    # требует работающий цикл событий)
    bot.on_startup.append(_setup_http_client(bot))
    # Дедупликация событий Long Poll: VK иногда присылает одно событие
    # дважды (переподключение), из-за чего бот отвечал на сообщение дважды
    _enable_event_deduplication(bot)

    logging.info("Бот запущен (Long Poll). Ожидание сообщений...")
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем.")


def _enable_event_deduplication(bot) -> None:
    """Фильтрует дубликаты сообщений пользователя по содержимому и времени.

    VK может доставить одно сообщение пользователя дважды: Long Poll
    отдаёт событие повторно при переподключении (другой event_id), а
    клиент иногда отправляет сообщение повторно. Фильтр: одинаковые
    (from_id, text) в течение окна DEDUP_WINDOW секунд считаются
    дубликатом и пропускаются.

    Args:
        bot: Бот, у которого оборачивается обработка событий.
    """
    #: Окно дедупликации, секунды
    DEDUP_WINDOW = 3.0
    seen: dict[tuple[int, str], float] = {}
    original_process_event = bot.process_event

    async def process_event_dedup(event: Any, api: Any = None) -> None:
        """Пропускает дубликаты сообщений и вызывает оригинальную обработку.

        Args:
            event: Событие Long Poll.
            api: API-клиент (пробрасывается в оригинальный метод).
        """
        if isinstance(event, dict) and event.get("type") == "message_new":
            message = (event.get("object") or {}).get("message") or {}
            from_id = message.get("from_id")
            text = (message.get("text") or "").strip()
            if from_id is not None and text:
                now = time.monotonic()
                key = (from_id, text)
                # Чистим устаревшие ключи
                for stale in [k for k, t in seen.items() if now - t > DEDUP_WINDOW]:
                    seen.pop(stale, None)
                if key in seen and now - seen[key] <= DEDUP_WINDOW:
                    logger.debug("Дубликат сообщения пропущен: %r от %s", text, from_id)
                    return
                seen[key] = now
        await original_process_event(event, api)

    bot.process_event = process_event_dedup


def _setup_http_client(bot):
    """Startup-задача: подключает SSL-клиент внутри event loop.

    Args:
        bot: Бот для настройки HTTP-клиента.

    Returns:
        Корутина для on_startup.
    """

    async def _setup() -> None:
        attach_http_client(bot)

    return _setup()


if __name__ == "__main__":
    main()
