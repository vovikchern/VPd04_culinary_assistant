"""Форматирование сообщений бота: только строки, без логики.

Все сообщения нарезаются на части не длиннее 4000 символов
(лимит VK — 4096).
"""

from __future__ import annotations

from typing import Any, Dict, List

#: Максимальная длина одного сообщения (запас до лимита VK 4096)
MAX_MESSAGE_LEN = 4000

#: Готовые тексты ошибок для хендлеров
ERROR_NOT_FOUND = "Рецепт не найден, попробуйте другой номер."
ERROR_QUOTA = "Квота API на сегодня исчерпана. Приходите завтра!"
ERROR_API_KEY = "Ключ API не настроен — проверьте файл .env."
ERROR_NETWORK = "Сервис недоступен, попробуйте позже."
ERROR_EMPTY_INPUT = "Ввод пустой."

#: Русские подписи диетических флагов карточки
FLAG_LABELS: Dict[str, str] = {
    "vegan": "веган",
    "vegetarian": "вегетарианское",
    "gluten_free": "без глютена",
    "dairy_free": "без молочных продуктов",
}


def format_main_menu() -> str:
    """Возвращает текст главного меню."""
    return "🍳 Кулинарный помощник\nЧто приготовить сегодня?\nВыберите действие:"


def format_help() -> str:
    """Возвращает текст справки по командам."""
    return (
        "ℹ️ Справка — Кулинарный помощник\n\n"
        "🍳 Что приготовить? — рецепты из ваших продуктов\n"
        "🔍 Найти рецепт — поиск по названию блюда или кухне\n"
        "🎲 Рецепт дня — случайный рецепт\n"
        "📖 Карточка рецепта — по номеру из списка или id\n"
        "🥗 Расширенный режим — карточка с анализом питания (БЖУ, калории)\n\n"
        "Вводить можно по-русски — бот сам переведёт запрос.\n"
        "🏠 Главное меню — вернуться в меню из любого раздела."
    )


def format_recipe_list(recipes: List[Dict[str, Any]], show_likes: bool) -> str:
    """Форматирует список рецептов с русскими названиями.

    Args:
        recipes: Рецепты от RecipeService (с title_ru).
        show_likes: Показывать лайки (режим «по ингредиентам»).

    Returns:
        Текст списка с приглашением ввести номер.
    """
    lines = [f"Найдено рецептов: {len(recipes)}"]
    for index, recipe in enumerate(recipes, start=1):
        title = recipe.get("title_ru") or recipe.get("title", "")
        extras: List[str] = [f"id {recipe.get('id', '?')}"]
        if show_likes and "likes" in recipe:
            extras.append(f"👍 {recipe['likes']}")
        if "used_count" in recipe:
            extras.append(
                f"✅ есть: {recipe['used_count']}, 🛒 докупить: {recipe['missed_count']}"
            )
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"{index}. {title}{suffix}")
    lines.append("")
    lines.append(
        f"Введите номер рецепта (1-{len(recipes)}) или его id, чтобы открыть карточку."
    )
    return "\n".join(lines)


def format_recipe_card(card: Dict[str, Any], extended: bool = False) -> List[str]:
    """Форматирует карточку рецепта, при необходимости — на несколько сообщений.

    Args:
        card: Карточка от RecipeService (с полями *_ru).
        extended: Показывать блок анализа питания.

    Returns:
        Список сообщений, каждое не длиннее MAX_MESSAGE_LEN.
    """
    title = card.get("title_ru") or card.get("title", "")
    header = (
        f"🍽 {title}\n"
        f"⏱ Время: {card.get('ready_in_minutes', '?')} мин | "
        f"Порции: {card.get('servings', '?')}"
    )
    sections: List[str] = [header]

    ingredients = card.get("ingredients_ru") or card.get("ingredients") or []
    if ingredients:
        sections.append(
            "🧾 Ингредиенты:\n" + "\n".join(f"• {item}" for item in ingredients)
        )

    steps = card.get("instructions_ru") or card.get("instructions") or []
    if steps:
        numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, start=1))
        sections.append(f"👨‍🍳 Шаги:\n{numbered}")

    summary = card.get("summary_ru") or card.get("summary") or ""
    if summary:
        sections.append(f"📖 Описание: {summary}")

    if extended:
        nutrition = _format_nutrition(card)
        if nutrition:
            sections.append(nutrition)

    return _pack_sections(sections)


def _format_nutrition(card: Dict[str, Any]) -> str:
    """Форматирует блок анализа питания расширенной карточки.

    Args:
        card: Карточка с nutrition_analysis и расширенными полями.

    Returns:
        Текст блока или пустая строка, если анализа нет.
    """
    analysis = card.get("nutrition_analysis")
    if not analysis:
        return ""
    breakdown = analysis.get("caloric_breakdown", {})
    lines = [
        "🥗 Анализ питания:",
        str(analysis.get("human_summary", "")),
        (
            f"БЖУ: белки {analysis.get('protein_g', 0):.1f} г / "
            f"жиры {analysis.get('fat_g', 0):.1f} г / "
            f"углеводы {analysis.get('carbs_g', 0):.1f} г"
        ),
        (
            f"Распределение калорий: "
            f"Б {breakdown.get('protein', 0):.0f}% / "
            f"Ж {breakdown.get('fat', 0):.0f}% / "
            f"У {breakdown.get('carbs', 0):.0f}%"
        ),
    ]
    lines.extend(str(warning) for warning in analysis.get("warnings", []))

    extra: List[str] = []
    if card.get("health_score") is not None:
        extra.append(f"💯 Health score: {card['health_score']}")
    labels = [
        FLAG_LABELS[key] for key, value in (card.get("flags") or {}).items() if value
    ]
    if labels:
        extra.append(f"🏷 Метки: {', '.join(labels)}")
    if extra:
        lines.append("")
        lines.extend(extra)
    return "\n".join(lines)


def _pack_sections(sections: List[str]) -> List[str]:
    """Собирает секции в сообщения не длиннее MAX_MESSAGE_LEN.

    Секции склеиваются пустой строкой; слишком длинная секция
    режется по строкам (нумерация шагов сохраняется).

    Args:
        sections: Список секций карточки.

    Returns:
        Список готовых сообщений.
    """
    messages: List[str] = []
    current = ""
    for section in sections:
        if len(section) > MAX_MESSAGE_LEN:
            if current:
                messages.append(current)
                current = ""
            messages.extend(_split_by_lines(section))
            continue
        candidate = f"{current}\n\n{section}" if current else section
        if len(candidate) <= MAX_MESSAGE_LEN:
            current = candidate
        else:
            messages.append(current)
            current = section
    if current:
        messages.append(current)
    return messages


def _split_by_lines(section: str) -> List[str]:
    """Режет одну длинную секцию по строкам на части ≤ MAX_MESSAGE_LEN.

    Args:
        section: Секция, превышающая лимит.

    Returns:
        Список частей секции.
    """
    parts: List[str] = []
    current = ""
    for line in section.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= MAX_MESSAGE_LEN:
            current = candidate
        else:
            parts.append(current)
            current = line
    if current:
        parts.append(current)
    return parts
