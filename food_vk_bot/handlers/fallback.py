"""Fallback-хендлер: любые сообщения без состояния и payload.

Загружается ПОСЛЕДНИМ — обрабатывает всё, что не совпало
с кнопками и активными сценариями.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from food_vk_bot.handlers.common import show_main_menu

bl = BotLabeler()


@bl.private_message(state=None)
async def fallback(message: Message) -> None:
    """Показывает главное меню на любой непонятный ввод."""
    if message.payload:
        return
    await show_main_menu(message)
