"""Хендлер справки."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from food_vk_bot.services import formatter

bl = BotLabeler()


from food_vk_bot.keyboards.main_keyboard import empty_keyboard


@bl.private_message(payload={"cmd": "help"})
async def help_handler(message: Message) -> None:
    """Кнопка «ℹ️ Помощь» — справка по командам."""
    await message.answer(formatter.format_help(), keyboard=empty_keyboard())
