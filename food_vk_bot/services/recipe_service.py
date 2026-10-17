"""Связующее звено: SpoonacularAPI + TranslateService.

Все вызовы синхронных модулей выполняются через asyncio.to_thread,
чтобы не блокировать цикл событий бота. Логика повторяет проверенный
консольный прототип demo_ru.py.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List

from spoonacular_api import SpoonacularAPI

from food_vk_bot.services.translate_service import TranslateService

#: Рецепт в формате, который возвращают методы сервиса
Recipe = Dict[str, Any]

#: Признак кириллицы (для документации; проверка — в TranslateService)
_CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")


def _filter_relevant(recipes: List[Recipe], query_en: str) -> List[Recipe]:
    """Отсеивает рецепты, не содержащие ни одного слова запроса.

    Индекс ингредиентов Spoonacular иногда даёт ложные совпадения
    (например, "top ginger" склеен с говяжьим отрубом "top round"),
    поэтому проверяем, что слово запроса реально встречается в
    использованных ингредиентах. Учитываем формы единственного и
    множественного числа (apple/apples). Если после фильтра пусто —
    возвращаем исходный список (лучше показать всё, чем ничего).

    Args:
        recipes: Список рецептов от findByIngredients.
        query_en: Английский запрос вида "apples,flour,sugar".

    Returns:
        Отфильтрованный список (или исходный, если фильтр всё убрал).
    """
    words = {w.strip().lower() for w in query_en.split(",") if w.strip()}
    words |= {w.rstrip("s") for w in words if w.endswith("s")}
    if not words:
        return recipes

    def is_relevant(recipe: Recipe) -> bool:
        """Проверяет вхождение любого слова запроса в used-ингредиенты."""
        used = " | ".join(recipe.get("used_ingredients", [])).lower()
        return any(word in used for word in words)

    filtered = [r for r in recipes if is_relevant(r)]
    return filtered if filtered else recipes


class RecipeService:
    """Бизнес-логика рецептов: поиск, карточки, замены — с переводом."""

    def __init__(self, translator: TranslateService) -> None:
        """Сохраняет переводчик и создаёт клиент Spoonacular.

        Args:
            translator: Общий сервис перевода бота.
        """
        self._api = SpoonacularAPI()
        self._translator = translator

    # ------------------------------------------------------------------
    # Публичные методы (async)
    # ------------------------------------------------------------------

    async def find_by_ingredients(self, ingredients_input: str) -> List[Recipe]:
        """Ищет рецепты по продуктам пользователя (можно по-русски).

        Args:
            ingredients_input: Строка вида "яблоки,мука,сахар".

        Returns:
            Список рецептов с title_ru, отсортированный по лайкам и
            очищенный от ложных совпадений.
        """
        query_en = await asyncio.to_thread(
            self._translator.ingredients_to_english, ingredients_input
        )
        recipes = await asyncio.to_thread(
            self._api.find_recipes_by_ingredients, query_en, 5
        )
        # При одном ингредиенте порядок API произволен — сортируем по лайкам
        recipes.sort(key=lambda r: r.get("likes", 0), reverse=True)
        recipes = _filter_relevant(recipes, query_en)
        await self._attach_translated_titles(recipes)
        return recipes

    async def search(self, query_input: str) -> List[Recipe]:
        """Ищет рецепты по названию блюда или кухне (можно по-русски).

        Args:
            query_input: Поисковый запрос пользователя.

        Returns:
            Список рецептов с title_ru.
        """
        query_en = await asyncio.to_thread(self._translator.to_english, query_input)
        recipes = await asyncio.to_thread(self._api.search_recipes, query_en, 5)
        await self._attach_translated_titles(recipes)
        return recipes

    async def card(self, recipe_id: int, extended: bool = False) -> Recipe:
        """Возвращает карточку рецепта на русском языке.

        Args:
            recipe_id: id рецепта в Spoonacular.
            extended: True — добавить анализ питания (БЖУ, калории).

        Returns:
            Карточка с title_ru, ingredients_ru, instructions_ru, summary_ru.
        """
        raw = await asyncio.to_thread(self._api.get_recipe_details, recipe_id, extended)
        return await self._translate_card(raw)

    async def random(self) -> Recipe:
        """Возвращает случайный рецепт ("рецепт дня") на русском.

        Returns:
            Карточка рецепта с переводом.
        """
        raw = await asyncio.to_thread(self._api.get_recipe_of_the_day)
        return await self._translate_card(raw)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    async def _attach_translated_titles(self, recipes: List[Recipe]) -> None:
        """Добавляет каждому рецепту переведённое название title_ru.

        Названия переводятся ОДНИМ запросом (экономия квоты MyMemory).

        Args:
            recipes: Список рецептов от SpoonacularAPI.
        """
        titles = await asyncio.to_thread(
            self._translator.translate_lines,
            [r.get("title", "") for r in recipes],
        )
        for recipe, title in zip(recipes, titles):
            recipe["title_ru"] = title

    async def _translate_card(self, card: Recipe) -> Recipe:
        """Переводит поля карточки рецепта на русский язык.

        Args:
            card: Карточка от SpoonacularAPI (title, ingredients,
                instructions, summary, при extended — nutrition_analysis).

        Returns:
            Та же карточка с полями *_ru.
        """
        card["title_ru"] = await asyncio.to_thread(
            self._translator.translate, card.get("title", "")
        )
        ingredients = card.get("ingredients") or []
        if ingredients:
            card["ingredients_ru"] = await asyncio.to_thread(
                self._translator.translate_lines, ingredients
            )
        steps = card.get("instructions") or []
        if steps:
            card["instructions_ru"] = [
                await asyncio.to_thread(self._translator.translate, step) for step in steps
            ]
        summary = card.get("summary") or ""
        if summary:
            card["summary_ru"] = await asyncio.to_thread(
                self._translator.translate, summary
            )
        return card
