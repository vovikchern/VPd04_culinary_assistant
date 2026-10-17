"""Payload-хендлеры кнопок главного меню.

Загружаются ПЕРВЫМИ: кнопки работают из любого состояния.
"""

from __future__ import annotations

from typing import Any, Dict, List

from vkbottle.bot import BotLabeler, Message

from food_vk_bot.context import ctx
from food_vk_bot.handlers.common import (
    report_error,
    send_recipe_card,
    show_main_menu,
)
from food_vk_bot.keyboards.main_keyboard import empty_keyboard
from food_vk_bot.states import BotState

bl = BotLabeler()


async def _carry_over_recipes(message: Message) -> List[Dict[str, Any]]:
    """Возвращает список рецептов из текущего состояния (если он есть).

    Позволяет кнопкам «📖 Карточка» и «🥗 Расширенный режим» работать
    сразу после поиска: список номеров переносится в новое состояние.

    Args:
        message: Сообщение-контекст.

    Returns:
        Список {id, title} из payload состояния или пустой список.
    """
    peer = await ctx.bot.state_dispenser.get(message.peer_id)  # type: ignore[union-attr]
    if peer is None:
        return []
    recipes = (peer.payload or {}).get("recipes", [])
    return list(recipes) if isinstance(recipes, list) else []


@bl.private_message(payload={"cmd": "menu"})
async def menu_button(message: Message) -> None:
    """Кнопки «⬅️ Назад» и «🏠 Главное меню» — возврат в меню."""
    await show_main_menu(message)


@bl.private_message(payload={"command": "start"})
async def start_button(message: Message) -> None:
    """Кнопка «Начать» сообщества — приветствие и меню."""
    await show_main_menu(message)


@bl.private_message(payload={"cmd": "ingredients"})
async def ingredients_button(message: Message) -> None:
    """Кнопка «🍳 Что приготовить?» — запрос продуктов."""
    await ctx.bot.state_dispenser.set(  # type: ignore[union-attr]
        message.peer_id, BotState.WAITING_INGREDIENTS
    )
    await message.answer(
        "Введите продукты через запятую (можно по-русски):\n"
        "Например: яблоки,мука,сахар",
        keyboard=empty_keyboard(),
    )


@bl.private_message(payload={"cmd": "search"})
async def search_button(message: Message) -> None:
    """Кнопка «🔍 Найти рецепт» — запрос названия блюда."""
    await ctx.bot.state_dispenser.set(  # type: ignore[union-attr]
        message.peer_id, BotState.WAITING_SEARCH_QUERY
    )
    await message.answer(
        "Введите блюдо или кухню (можно по-русски):\nНапример: паста",
        keyboard=empty_keyboard(),
    )


@bl.private_message(payload={"cmd": "card"})
async def card_button(message: Message) -> None:
    """Кнопка «📖 Карточка рецепта» — запрос номера или id.

    Список из последнего поиска (если был) переносится в новое состояние.
    """
    recipes = await _carry_over_recipes(message)
    await ctx.bot.state_dispenser.set(  # type: ignore[union-attr]
        message.peer_id, BotState.WAITING_RECIPE_CARD, recipes=recipes
    )
    if recipes:
        await message.answer(
            "Введите номер из последнего списка или id рецепта Spoonacular:",
            keyboard=empty_keyboard(),
        )
    else:
        await message.answer(
            "Введите id рецепта Spoonacular:\n"
            "(id показан в списках после поиска, например 654959)",
            keyboard=empty_keyboard(),
        )


@bl.private_message(payload={"cmd": "extended"})
async def extended_button(message: Message) -> None:
    """Кнопка «🥗 Расширенный режим» — запрос номера или id.

    Список из последнего поиска (если был) переносится в новое состояние.
    """
    recipes = await _carry_over_recipes(message)
    await ctx.bot.state_dispenser.set(  # type: ignore[union-attr]
        message.peer_id, BotState.WAITING_RECIPE_EXTENDED, recipes=recipes
    )
    if recipes:
        await message.answer(
            "Введите номер из последнего списка или id рецепта.\n"
            "Карточка будет дополнена анализом питания (БЖУ, калории):",
            keyboard=empty_keyboard(),
        )
    else:
        await message.answer(
            "Введите id рецепта Spoonacular.\n"
            "Карточка будет дополнена анализом питания (БЖУ, калории):\n"
            "(id показан в списках после поиска, например 654959)",
            keyboard=empty_keyboard(),
        )


@bl.private_message(payload={"cmd": "random"})
async def random_button(message: Message) -> None:
    """Кнопка «🎲 Рецепт дня» — сразу карточка случайного рецепта."""
    await message.answer("🎲 Подбираю рецепт дня...", keyboard=empty_keyboard())
    try:
        card = await ctx.recipes.random()  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 — ошибки API обрабатываются общим способом
        await report_error(message, exc)
        return
    await send_recipe_card(message, card, extended=False)

