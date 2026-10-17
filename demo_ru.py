"""Демо: кулинарный помощник в консоли — прототип будущего VK-бота.

Объединяет оба модуля: SpoonacularAPI (рецепты) + MyMemoryAPI (перевод).
Сценарий: выбор режима → список рецептов с русскими названиями →
выбор номера → карточка рецепта на русском языке.

Запуск из корня проекта:
    python demo_ru.py

Файл демонстрационный: в боте эта логика станет services/recipe_service.py
и services/formatter.py.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from mymemory_api import MyMemoryAPI
from spoonacular_api import SpoonacularAPI


def ask(prompt: str) -> str:
    """Читает строку от пользователя с обработкой Ctrl+C.

    Args:
        prompt: Текст приглашения.

    Returns:
        Введённая строка (без пробелов по краям).
    """
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nВыход.")
        raise SystemExit(0)


def translate_list(translator: MyMemoryAPI, items: List[str]) -> List[str]:
    """Переводит список коротких строк, склеивая их переводами построчно.

    Экономит квоту: вместо запроса на каждую строку — один запрос на весь
    список (если влезает в лимит 480 символов). Если число переведённых
    строк не совпало с исходным — переводит по одной.

    Args:
        translator: Клиент перевода.
        items: Список строк (например, ингредиентов).

    Returns:
        Список переведённых строк той же длины.
    """
    if not items:
        return []
    joined = "\n".join(items)
    if len(joined) <= 480:
        try:
            translated = translator.translate(joined)
            lines = [line.strip() for line in translated.split("\n") if line.strip()]
            if len(lines) == len(items):
                return lines
        except Exception:  # noqa: BLE001 — демо: любой сбой → поштучный перевод
            pass
    return [translator.translate(item) for item in items]


#: Признак кириллицы во вводе пользователя
_CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")


def to_english(translator: MyMemoryAPI, text: str) -> str:
    """Переводит пользовательский ввод ru→en, если он содержит кириллицу.

    Args:
        translator: Клиент перевода.
        text: Введённый текст (поисковый запрос).

    Returns:
        Текст на английском (или исходный, если кириллицы нет).
    """
    if not _CYRILLIC_RE.search(text):
        return text
    return translator.translate(text, source="ru", target="en")


def ingredients_to_english(translator: MyMemoryAPI, ingredients: str) -> str:
    """Переводит список ингредиентов ru→en по одному элементу.

    Args:
        translator: Клиент перевода.
        ingredients: Строка вида "яблоки, мука, сахар".

    Returns:
        Строка вида "apples,flour,sugar" для SpoonacularAPI.
    """
    if not _CYRILLIC_RE.search(ingredients):
        return ingredients
    items = [part.strip() for part in ingredients.split(",") if part.strip()]
    translated = [translator.translate(item, source="ru", target="en") for item in items]
    return ",".join(translated)


def filter_relevant(recipes: List[Dict[str, Any]], query_en: str) -> List[Dict[str, Any]]:
    """Отсеивает рецепты, не содержащие ни одного слова запроса.

    Индекс ингредиентов Spoonacular иногда даёт ложные совпадения
    (например, "top ginger" склеен с говяжьим отрубом "top round"),
    поэтому проверяем, что слово запроса реально встречается в
    использованных ингредиентах рецепта. Учитываем формы единственного
    и множественного числа (apple/apples). Если после фильтра пусто —
    возвращаем исходный список (лучше показать всё, чем ничего).

    Args:
        recipes: Список рецептов от findByIngredients.
        query_en: Английский запрос вида "apples,flour,sugar".

    Returns:
        Отфильтрованный список (или исходный, если фильтр всё убрал).
    """
    words = {
        w.strip().lower()
        for w in query_en.split(",")
        if w.strip()
    }
    # Добавляем форму без окончания -s (apples → apple)
    words |= {w.rstrip("s") for w in words if w.endswith("s")}
    if not words:
        return recipes

    def is_relevant(recipe: Dict[str, Any]) -> bool:
        """Проверяет вхождение любого слова запроса в used-ингредиенты."""
        used = " | ".join(recipe.get("used_ingredients", [])).lower()
        return any(word in used for word in words)

    filtered = [r for r in recipes if is_relevant(r)]
    return filtered if filtered else recipes


def show_list(recipes: List[Dict[str, Any]], translator: MyMemoryAPI) -> None:
    """Печатает список рецептов с переведёнными названиями.

    Args:
        recipes: Список рецептов от SpoonacularAPI.
        translator: Клиент перевода.
    """
    print(f"\nНайдено рецептов: {len(recipes)}. Перевожу названия...")
    titles = translate_list(translator, [r["title"] for r in recipes])
    for index, (recipe, title) in enumerate(zip(recipes, titles), start=1):
        extra = ""
        if "used_count" in recipe:
            extra = f" | ✅ есть: {recipe['used_count']}, 🛒 докупить: {recipe['missed_count']}"
        print(f"{index}. {title} (👍 {recipe.get('likes', '—')}{extra})")


def show_card(card: Dict[str, Any], translator: MyMemoryAPI) -> None:
    """Печатает карточку рецепта на русском языке.

    Args:
        card: Карточка от SpoonacularAPI.get_recipe_details().
        translator: Клиент перевода.
    """
    print("\nПеревожу карточку (название, ингредиенты, шаги, описание)...")
    title = translator.translate(card["title"])

    print(f"\n🍽 {title} (id={card['id']})")
    print(f"⏱ Время: {card['ready_in_minutes']} мин | Порции: {card['servings']}")

    if card["ingredients"]:
        print("\n🧾 Ингредиенты:")
        for ingredient in translate_list(translator, card["ingredients"]):
            print(f"  • {ingredient}")

    if card["instructions"]:
        print("\n👨‍🍳 Шаги:")
        steps = [translator.translate(step) for step in card["instructions"]]
        for number, step in enumerate(steps, start=1):
            print(f"  {number}. {step}")

    if card["summary"]:
        print(f"\n📖 Описание: {translator.translate(card['summary'])}")


def show_menu() -> None:
    """Печатает главное меню демо-приложения."""
    print("\n────────────────────────────────")
    print("Выберите режим:")
    print("  1 — по ингредиентам («что приготовить из…»)")
    print("  2 — поиск по названию блюда")
    print("  3 — рецепт дня (случайный рецепт)")
    print("  0 — выход")


def run_mode(
    choice: str, api: SpoonacularAPI, translator: MyMemoryAPI
) -> None:
    """Выполняет выбранный режим меню.

    После списка рецептов предлагает выбрать номер для карточки;
    после карточки управление возвращается в главное меню.

    Args:
        choice: Выбранный пункт меню ("1", "2" или "3").
        api: Клиент Spoonacular.
        translator: Клиент перевода.
    """
    if choice == "1":
        ingredients = ask("Продукты через запятую (можно по-русски: яблоки,мука,сахар): ")
        query_en = ingredients_to_english(translator, ingredients)
        recipes = api.find_recipes_by_ingredients(query_en)
        # API сортирует по «максимум использованных ингредиентов», при одном
        # ингредиенте порядок произвольный — сортируем по популярности (лайки)
        recipes.sort(key=lambda r: r.get("likes", 0), reverse=True)
        # Отсекаем ложные совпадения индекса ингредиентов (top ginger ↔ beef)
        recipes = filter_relevant(recipes, query_en)
        if not recipes:
            print("Рецепты не найдены.")
            return
        show_list(recipes, translator)
    elif choice == "2":
        query = ask("Блюдо или кухня (можно по-русски, например: паста): ")
        recipes = api.search_recipes(to_english(translator, query))
        if not recipes:
            print("Ничего не найдено.")
            return
        show_list(recipes, translator)
    elif choice == "3":
        show_card(api.get_recipe_of_the_day(), translator)
        print(f"\nЗаписей в кэше переводов: {translator.get_cache_size()}")
        return
    else:
        print("Неизвестный выбор.")
        return

    pick = ask(f"\nНомер рецепта для карточки (1-{len(recipes)}), Enter — в меню: ")
    if not pick:
        return
    if not pick.isdigit() or not 1 <= int(pick) <= len(recipes):
        print(f"Некорректный номер: введите число от 1 до {len(recipes)}.")
        return
    show_card(api.get_recipe_details(recipes[int(pick) - 1]["id"]), translator)
    print(f"\nЗаписей в кэше переводов: {translator.get_cache_size()}")


def main() -> None:
    """Точка входа демо-сценария: цикл «меню → действие → меню»."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    print("🍳 Кулинарный помощник — демо на русском (прототип VK-бота)")
    api = SpoonacularAPI()
    translator = MyMemoryAPI()

    while True:
        show_menu()
        choice = ask("Ваш выбор: ")
        if choice == "0":
            print("До встречи! 👋")
            break
        run_mode(choice, api, translator)


if __name__ == "__main__":
    main()
