"""Общие помощники хендлеров: меню, карточка, ошибки."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mymemory_api import TranslationQuotaExceededError
from spoonacular_api import (
    InvalidAPIKeyError,
    QuotaExceededError,
    RecipeNotFoundError,
)
from vkbottle.bot import Message

from food_vk_bot.context import ctx
from food_vk_bot.keyboards.main_keyboard import main_keyboard
from food_vk_bot.services import formatter

logger = logging.getLogger(__name__)

#: Слова-команды выхода в главное меню из любого состояния
#: (кнопки клавиатуры в VK спрятаны за значком ⊞, поэтому дублируем текстом)
EXIT_WORDS = {
    "0",
    "меню",
    "назад",
    "главное меню",
    "выход",
    "отмена",
    "стоп",
    "start",
    "начать",
}

#: Подсказка о выходе, добавляется к сообщениям об ошибках
EXIT_HINT = "\n\nДля выхода в меню отправьте 0 (меню закреплено в панели ввода)."


def is_exit_command(text: str) -> bool:
    """Проверяет, является ли ввод командой выхода в меню.

    Args:
        text: Введённый пользователем текст.

    Returns:
        True для слов из EXIT_WORDS (регистр не важен).
    """
    return text.strip().lower() in EXIT_WORDS


async def show_main_menu(message: Message, text: Optional[str] = None) -> None:
    """Сбрасывает состояние и показывает главное меню.

    Клавиатура отправляется ТОЛЬКО здесь: каждый ответ с клавиатурой
    перерисовывает панель ввода в VK (визуально «сворачивает» меню).
    В остальных сообщениях клавиатура не указывается — панель остаётся
    на месте.

    Args:
        message: Сообщение-контекст.
        text: Дополнительный текст перед меню (по умолчанию — стандартный).
    """
    await ctx.bot.state_dispenser.delete(message.peer_id)  # type: ignore[union-attr]
    await message.answer(
        text or formatter.format_main_menu(),
        keyboard=main_keyboard().get_json(),
    )


async def send_recipe_card(
    message: Message, card: Dict[str, Any], extended: bool = False
) -> None:
    """Отправляет карточку рецепта (текст частями + фото) и меню.

    Args:
        message: Сообщение-контекст.
        card: Карточка от RecipeService.card()/random().
        extended: Карточка с анализом питания.
    """
    for chunk in formatter.format_recipe_card(card, extended=extended):
        await message.answer(chunk)
    attachment = await ctx.photos.send_photo(message, card.get("image", ""))
    if attachment:
        await message.answer("🖼 Фото блюда", attachment=attachment)
    else:
        await message.answer("🏠 Главное меню")


async def report_error(message: Message, exc: Exception) -> None:
    """Логирует исключение и отправляет пользователю понятный текст.

    Args:
        message: Сообщение-контекст.
        exc: Перехваченное исключение API.
    """
    logger.exception("Ошибка API в хендлере", exc_info=exc)
    if isinstance(exc, RecipeNotFoundError):
        text = formatter.ERROR_NOT_FOUND
    elif isinstance(exc, (QuotaExceededError, TranslationQuotaExceededError)):
        text = formatter.ERROR_QUOTA
    elif isinstance(exc, InvalidAPIKeyError):
        text = formatter.ERROR_API_KEY
    else:
        text = formatter.ERROR_NETWORK
    await message.answer(text + EXIT_HINT)
