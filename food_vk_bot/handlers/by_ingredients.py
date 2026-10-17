"""Сценарий «🍳 Что приготовить?» — ввод продуктов."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from food_vk_bot.context import ctx
from food_vk_bot.handlers.common import is_exit_command, report_error, show_main_menu
from food_vk_bot.services import formatter
from food_vk_bot.states import BotState

bl = BotLabeler()


@bl.private_message(state=BotState.WAITING_INGREDIENTS)
async def ingredients_input(message: Message) -> None:
    """Обрабатывает список продуктов и показывает рецепты.

    После списка бот переходит в состояние WAITING_RECIPE_CARD
    с payload recipes (id + русские названия).
    """
    text = (message.text or "").strip()
    if is_exit_command(text):
        await show_main_menu(message)
        return
    if not text:
        await message.answer(
            f"{formatter.ERROR_EMPTY_INPUT}\nВведите продукты через запятую:",
        )
        return
    try:
        recipes = await ctx.recipes.find_by_ingredients(text)  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 — ошибки API обрабатываются общим способом
        await report_error(message, exc)
        return
    if not recipes:
        await message.answer(
            "Рецепты не найдены. Попробуйте другие продукты:",
        )
        return
    await ctx.bot.state_dispenser.set(  # type: ignore[union-attr]
        message.peer_id,
        BotState.WAITING_RECIPE_CARD,
        recipes=[
            {"id": recipe["id"], "title": recipe.get("title_ru", recipe["title"])}
            for recipe in recipes
        ],
    )
    await message.answer(
        formatter.format_recipe_list(recipes, show_likes=True),
    )
