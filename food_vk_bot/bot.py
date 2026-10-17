"""Фабрика бота: создание Bot с токеном из .env."""

from __future__ import annotations

import logging
import os
import ssl

import aiohttp
import certifi
from vkbottle.bot import Bot
from vkbottle.http import SingleAiohttpClient

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Создаёт Bot с токеном сообщества из переменной окружения.

    HTTP-клиент с SSL-контекстом certifi подключается отдельно
    (attach_http_client) — внутри работающего event loop.

    Returns:
        Готовый Bot (Long Poll по умолчанию).

    Raises:
        RuntimeError: если VK_BOT_TOKEN не задан в .env.
    """
    token = os.getenv("VK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "VK_BOT_TOKEN не задан. Получите токен сообщества "
            "(Управление → Работа с API) и добавьте строку "
            "VK_BOT_TOKEN=... в файл .env"
        )
    return Bot(token=token)


def attach_http_client(bot: Bot) -> None:
    """Настраивает HTTP-клиент API бота на SSL-контекст certifi.

    Системное хранилище сертификатов Windows не содержит цепочку
    api.vk.ru (aiohttp проверяет сертификаты по нему), поэтому
    используется бандл certifi — как у requests.

    SingleAiohttpClient — синглтон: новый экземпляр вернёт старый объект
    без наших параметров, поэтому модифицируем _session_params
    существующего клиента и сбрасываем ленивую сессию.

    Вызывать ВНУТРИ event loop: aiohttp.TCPConnector требует
    работающий цикл событий.

    Args:
        bot: Бот, чей api.http_client настраивается.
    """
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    client = bot.api.http_client
    client._session_params["connector"] = connector  # noqa: SLF001 — единственный способ настроить синглтон
    client.session = None  # сброс ленивой сессии, чтобы пересоздалась с connector
    logger.info("HTTP-клиент API настроен с SSL-контекстом certifi")
