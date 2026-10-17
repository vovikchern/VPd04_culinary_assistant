"""Вспомогательные функции модуля spoonacular_api."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: Шаблон для удаления HTML-тегов
_HTML_TAG_RE = re.compile(r"<[^>]+>")
#: Шаблон для сжатия последовательных пробелов
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """Удаляет HTML-теги из строки и нормализует пробелы.

    Args:
        text: Исходная строка, возможно с HTML-разметкой.

    Returns:
        Чистый текст без тегов; пустая строка для пустого ввода.
    """
    if not text:
        return ""
    cleaned = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def normalize_ingredients(ingredients: str) -> str:
    """Нормализует строку ингредиентов, введённую пользователем.

    Убирает пробелы вокруг запятых и внутри названий, приводит к нижнему
    регистру и отбрасывает пустые элементы.

    Args:
        ingredients: Строка вида "apples, flour , sugar".

    Returns:
        Нормализованная строка вида "apples,flour,sugar".

    Raises:
        ValueError: если после нормализации список пуст.
    """
    if not ingredients or not ingredients.strip():
        raise ValueError("Список ингредиентов пуст")
    items = [part.strip().lower() for part in ingredients.split(",") if part.strip()]
    if not items:
        raise ValueError("Список ингредиентов пуст")
    return ",".join(items)


def find_nutrient(nutrients: Optional[List[Dict[str, Any]]], name: str) -> Optional[Dict[str, Any]]:
    """Ищет нутриент по точному совпадению поля name.

    Args:
        nutrients: Список нутриентов из объекта nutrition.
        name: Точное английское название, например "Calories".

    Returns:
        Словарь нутриента или None, если не найден.
    """
    for nutrient in nutrients or []:
        if nutrient.get("name") == name:
            return nutrient
    return None
