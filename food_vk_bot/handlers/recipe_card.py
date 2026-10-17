"""Сценарии «📖 Карточка рецепта» и «🥗 Расширенный режим» — выбор номера."""

from __future__ import annotations

from typing import Any, Dict, List

from vkbottle.bot import BotLabeler, Message

from food_vk_bot.context import ctx
from food_vk_bot.handlers.common import (
    is_exit_command,
    report_error,
    send_recipe_card,
    show_main_menu,
)
from food_vk_bot.states import BotState

bl = BotLabeler()


async def _process_pick(message: Message, extended: bool) -> None:
    """Разбирает номер/id рецепта и отправляет карточку.

    Число в диапазоне списка → id из payload состояния;
    другое число → трактуется как id рецепта Spoonacular;
    не-число → повторный запрос номера.

    Args:
        message: Сообщение-контекст.
        extended: Карточка с анализом питания.
    """
    peer = await ctx.bot.state_dispenser.get(message.peer_id)  # type: ignore[union-attr]
    recipes: List[Dict[str, Any]] = (peer.payload or {}).get("recipes", []) if peer else []

    text = (message.text or "").strip()
    if is_exit_command(text):
        await show_main_menu(message)
        return
    if not text.isdigit():
        await message.answer(
            "Введите число — номер рецепта из списка или id рецепта.\n"
            "Для выхода в меню отправьте 0.",
        )
        return
    number = int(text)
    if 1 <= number <= len(recipes):
        recipe_id = recipes[number - 1]["id"]
    else:
        recipe_id = number

    try:
        card = await ctx.recipes.card(recipe_id, extended=extended)  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 — ошибки API обрабатываются общим способом
        await report_error(message, exc)
        return

    await ctx.bot.state_dispenser.delete(message.peer_id)  # type: ignore[union-attr]
    await send_recipe_card(message, card, extended=extended)


@bl.private_message(state=BotState.WAITING_RECIPE_CARD)
async def card_pick(message: Message) -> None:
    """Выбор рецепта для обычной карточки."""
    await _process_pick(message, extended=False)


@bl.private_message(state=BotState.WAITING_RECIPE_EXTENDED)
async def extended_pick(message: Message) -> None:
    """Выбор рецепта для расширенной карточки (с анализом питания)."""
    await _process_pick(message, extended=True)
