"""Загрузка и отправка фото блюда в VK."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

import requests
from vkbottle import PhotoMessageUploader

if TYPE_CHECKING:  # pragma: no cover
    from vkbottle import API
    from vkbottle.bot import Message

logger = logging.getLogger(__name__)


class PhotoService:
    """Скачивает изображение рецепта и загружает его в VK.

    При любой ошибке возвращает None — бот деградирует к текстовой
    карточке без исключений.
    """

    def __init__(self, api: "API") -> None:
        """Создаёт загрузчик фото на API бота.

        Args:
            api: API-клиент vkbottle (bot.api).
        """
        self._uploader = PhotoMessageUploader(api)

    async def send_photo(self, message: "Message", url: str) -> Optional[str]:
        """Скачивает фото по URL и прикрепляет его к сообщению VK.

        Args:
            message: Сообщение-контекст (нужен peer_id загрузчику).
            url: Ссылка на изображение блюда.

        Returns:
            Строка вложения вида "photo..._..." или None при ошибке.
        """
        if not url:
            return None
        try:
            path = await asyncio.to_thread(self._download, url)
        except Exception:  # noqa: BLE001 — деградация к тексту без исключения
            logger.exception("Не удалось скачать фото блюда: %s", url)
            return None
        try:
            return await self._uploader.upload(path, peer_id=message.peer_id)
        except Exception:  # noqa: BLE001 — деградация к тексту без исключения
            logger.exception("Не удалось загрузить фото в VK")
            return None
        finally:
            _cleanup(path)

    def _download(self, url: str) -> str:
        """Скачивает изображение во временный файл.

        Args:
            url: Ссылка на изображение.

        Returns:
            Путь к временному файлу .jpg.

        Raises:
            requests.HTTPError: при ошибке скачивания.
        """
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        path = Path(tempfile.gettempdir()) / f"vk_dish_{uuid4().hex}.jpg"
        path.write_bytes(response.content)
        return str(path)


def _cleanup(path: str) -> None:
    """Удаляет временный файл фото (ошибки игнорируются)."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:  # pragma: no cover — не критично
        logger.debug("Не удалось удалить временный файл %s", path)
