"""Точка входа для тестирования модуля spoonacular_api в консоли.

Примеры запуска из корня проекта:
    python -m spoonacular_api.cli ingredients "apples,flour,sugar" --pick
    python -m spoonacular_api.cli search "pasta" --pick
    python -m spoonacular_api.cli details 716429 --extended
    python -m spoonacular_api.cli random
    python -m spoonacular_api.cli substitutes "butter"

Флаг --pick включает интерактивный выбор: после вывода списка программа
спрашивает номер рецепта и раскрывает его карточку с ингредиентами и шагами.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List

from .client import SpoonacularAPI
from .exceptions import SpoonacularAPIError

#: Русские подписи для флагов диеты
FLAG_LABELS: Dict[str, str] = {
    "vegan": "веган",
    "vegetarian": "вегетарианское",
    "gluten_free": "без глютена",
    "dairy_free": "без молочных продуктов",
}


def _print_recipes_by_ingredients(recipes: List[Dict[str, Any]]) -> None:
    """Печатает список рецептов, найденных по ингредиентам."""
    if not recipes:
        print("Рецепты не найдены. Попробуйте другие ингредиенты.")
        return
    print(f"Найдено рецептов: {len(recipes)}")
    for index, recipe in enumerate(recipes, start=1):
        print(f"\n{index}. {recipe['title']} (id={recipe['id']}, 👍 {recipe['likes']})")
        print(f"   Есть: {recipe['used_count']} | Не хватает: {recipe['missed_count']}")
        if recipe["used_ingredients"]:
            print(f"   ✅ Используются: {', '.join(recipe['used_ingredients'])}")
        if recipe["missed_ingredients"]:
            print(f"   🛒 Докупить: {', '.join(recipe['missed_ingredients'])}")


def _print_search_results(results: List[Dict[str, Any]]) -> None:
    """Печатает результаты поиска по названию."""
    if not results:
        print("Ничего не найдено. Попробуйте другой запрос.")
        return
    print(f"Найдено результатов: {len(results)}")
    for index, item in enumerate(results, start=1):
        print(f"{index}. {item['title']} (id={item['id']})")


def _print_recipe_card(card: Dict[str, Any]) -> None:
    """Печатает карточку рецепта (базовую или расширенную)."""
    print(f"\n🍽 {card['title']} (id={card['id']})")
    print(f"⏱ Время: {card['ready_in_minutes']} мин | Порции: {card['servings']}")
    if card.get("image"):
        print(f"🖼 Фото: {card['image']}")

    print("\n🧾 Ингредиенты:")
    for ingredient in card["ingredients"]:
        print(f"  • {ingredient}")

    if card["instructions"]:
        print("\n👨‍🍳 Шаги:")
        for number, step in enumerate(card["instructions"], start=1):
            print(f"  {number}. {step}")

    if card.get("summary"):
        print(f"\n📖 Описание: {card['summary']}")

    analysis = card.get("nutrition_analysis")
    if analysis:
        print("\n🥗 Анализ питания:")
        print(f"  {analysis['human_summary']}")
        print(
            "  БЖУ на порцию: "
            f"белки {analysis['protein_g']:.1f} г, "
            f"жиры {analysis['fat_g']:.1f} г, "
            f"углеводы {analysis['carbs_g']:.1f} г"
        )
        breakdown = analysis["caloric_breakdown"]
        print(
            "  Распределение калорий: "
            f"белки {breakdown['protein']:.0f}% / "
            f"жиры {breakdown['fat']:.0f}% / "
            f"углеводы {breakdown['carbs']:.0f}%"
        )

    if card.get("health_score") is not None:
        print(f"\n💯 Health score: {card['health_score']}")
    flags = card.get("flags") or {}
    active = [FLAG_LABELS[key] for key, value in flags.items() if value]
    if active:
        print(f"🏷 Метки: {', '.join(active)}")


def _print_substitutes(result: Dict[str, Any]) -> None:
    """Печатает замены для ингредиента."""
    if not result["substitutes"]:
        print(f"Замен для '{result['ingredient']}' не найдено.")
        return
    print(f"Замены для '{result['ingredient']}':")
    for substitute in result["substitutes"]:
        print(f"  • {substitute}")


def _show_picked_card(api: SpoonacularAPI, results: List[Dict[str, Any]]) -> None:
    """Спрашивает номер рецепта из списка и печатает его карточку.

    Реализует сценарий "поиск → выбор → ингредиенты": пользователь вводит
    номер из показанного списка, программа загружает и раскрывает карточку.

    Args:
        api: Экземпляр клиента SpoonacularAPI.
        results: Список рецептов из поиска (должны содержать поле id).
    """
    if not results:
        return
    try:
        choice = input(
            f"\nВведите номер рецепта (1-{len(results)}), чтобы открыть карточку "
            "(Enter — выход): "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not choice:
        return
    if not choice.isdigit() or not 1 <= int(choice) <= len(results):
        print(f"Некорректный номер: введите число от 1 до {len(results)}.")
        return
    chosen = results[int(choice) - 1]
    print("\nЗагружаю карточку рецепта...")
    _print_recipe_card(api.get_recipe_details(chosen["id"]))
    print(
        f"\n💡 Для анализа питания этого рецепта: "
        f"python -m spoonacular_api.cli details {chosen['id']} --extended"
    )


def main() -> int:
    """Разбирает аргументы командной строки и выполняет выбранную команду.

    Returns:
        Код завершения: 0 — успех, 1 — ошибка.
    """
    # Корректный вывод эмодзи в консоли Windows
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Тестирование модуля SpoonacularAPI в консоли"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_ingredients = subparsers.add_parser(
        "ingredients", help="Рецепты по ингредиентам через запятую"
    )
    parser_ingredients.add_argument("ingredients", help='Например: "apples,flour,sugar"')
    parser_ingredients.add_argument(
        "--pick", action="store_true", help="Выбрать рецепт из списка и показать карточку"
    )

    parser_search = subparsers.add_parser("search", help="Поиск рецептов по названию")
    parser_search.add_argument("query", help='Например: "pasta"')
    parser_search.add_argument(
        "--pick", action="store_true", help="Выбрать рецепт из списка и показать карточку"
    )

    parser_details = subparsers.add_parser("details", help="Карточка рецепта по id")
    parser_details.add_argument("recipe_id", type=int, help="id рецепта Spoonacular")
    parser_details.add_argument(
        "--extended", action="store_true", help="Добавить анализ питания (+0.1 очка)"
    )

    subparsers.add_parser("random", help="Случайный рецепт (рецепт дня)")

    parser_substitutes = subparsers.add_parser("substitutes", help="Замены ингредиента")
    parser_substitutes.add_argument("ingredient", help='Например: "butter"')

    args = parser.parse_args()

    try:
        api = SpoonacularAPI()
        if args.command == "ingredients":
            recipes = api.find_recipes_by_ingredients(args.ingredients)
            _print_recipes_by_ingredients(recipes)
            if args.pick:
                _show_picked_card(api, recipes)
        elif args.command == "search":
            results = api.search_recipes(args.query)
            _print_search_results(results)
            if args.pick:
                _show_picked_card(api, results)
        elif args.command == "details":
            _print_recipe_card(api.get_recipe_details(args.recipe_id, extended=args.extended))
        elif args.command == "random":
            _print_recipe_card(api.get_recipe_of_the_day())
        elif args.command == "substitutes":
            _print_substitutes(api.get_substitutes(args.ingredient))
    except SpoonacularAPIError as exc:
        print(f"Ошибка API: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Ошибка ввода: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
