"""Клиент Spoonacular API для кулинарного VK-бота.

Модуль возвращает структурированные данные и человекочитаемый анализ
питания на русском языке. Перевод рецептов выполняет отдельный модуль
DeepL — здесь тексты не переводятся.

Все endpoint'ы и параметры строго соответствуют официальной документации
Spoonacular (spoonacular.com/food-api/docs).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .config import BASE_URL, REQUEST_TIMEOUT, get_api_key
from .exceptions import (
    APIConnectionError,
    InvalidAPIKeyError,
    QuotaExceededError,
    RecipeNotFoundError,
    SpoonacularAPIError,
)
from .utils import find_nutrient, normalize_ingredients, strip_html


class SpoonacularAPI:
    """Обёртка над Spoonacular API с анализом питания.

    Использует одну HTTP-сессию (requests.Session) на экземпляр класса.
    Ключ читается из .env; хардкод ключей запрещён.
    """

    #: Базовый URL API
    BASE_URL: str = BASE_URL
    #: Поиск рецептов по ингредиентам ("что приготовить из того, что есть")
    ENDPOINT_FIND_BY_INGREDIENTS: str = "/recipes/findByIngredients"
    #: Расширенный поиск рецептов по названию/кухне/диете
    ENDPOINT_COMPLEX_SEARCH: str = "/recipes/complexSearch"
    #: Карточка рецепта по id (шаблон с {recipe_id})
    ENDPOINT_RECIPE_INFORMATION: str = "/recipes/{recipe_id}/information"
    #: Случайный рецепт ("рецепт дня")
    ENDPOINT_RANDOM: str = "/recipes/random"
    #: Замены ингредиента
    ENDPOINT_SUBSTITUTES: str = "/food/ingredients/substitutes"

    # Границы шкалы калорийности, ккал на порцию
    #: Верхняя граница "Лёгкое"
    CALORIE_LIGHT: float = 300.0
    #: Верхняя граница "Умеренное"
    CALORIE_MODERATE: float = 600.0
    #: Верхняя граница "Сытное"
    CALORIE_HEAVY: float = 800.0

    # Пороги "выбросов" питания
    #: Сахар, г на порцию
    SUGAR_LIMIT_G: float = 20.0
    #: Насыщенные жиры, г на порцию
    SATURATED_FAT_LIMIT_G: float = 10.0
    #: Натрий, мг на порцию
    SODIUM_LIMIT_MG: float = 800.0

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Инициализирует клиент и открывает HTTP-сессию.

        Args:
            api_key: Ключ Spoonacular. Если не передан — берётся из .env.

        Raises:
            InvalidAPIKeyError: если ключ не задан ни параметром, ни в окружении.
        """
        self._api_key: str = api_key or get_api_key()
        self._session: requests.Session = requests.Session()

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Выполняет GET-запрос к API и возвращает разобранный JSON.

        Подставляет apiKey, применяет таймаут и единообразно обрабатывает
        коды ответа HTTP.

        Args:
            endpoint: Путь endpoint'а, например "/recipes/random".
            params: Дополнительные query-параметры запроса.

        Returns:
            JSON-ответ API (словарь или список).

        Raises:
            InvalidAPIKeyError: HTTP 401.
            QuotaExceededError: HTTP 402.
            RecipeNotFoundError: HTTP 404.
            APIConnectionError: таймаут, сетевая ошибка или HTTP 5xx.
            SpoonacularAPIError: прочие неожиданные коды ответа.
        """
        url = f"{self.BASE_URL}{endpoint}"
        request_params: Dict[str, Any] = {"apiKey": self._api_key}
        if params:
            request_params.update(params)

        try:
            response = self._session.get(url, params=request_params, timeout=REQUEST_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise APIConnectionError(f"Сетевая ошибка при запросе {url}: {exc}") from exc

        if response.status_code == 401:
            raise InvalidAPIKeyError("Неверный API-ключ Spoonacular (HTTP 401).")
        if response.status_code == 402:
            raise QuotaExceededError(
                "Дневной лимит очков Spoonacular исчерпан (HTTP 402). Попробуйте завтра."
            )
        if response.status_code == 404:
            raise RecipeNotFoundError(f"Ресурс не найден (HTTP 404): {endpoint}")
        if response.status_code >= 500:
            raise APIConnectionError(
                f"Сервис Spoonacular недоступен (HTTP {response.status_code})."
            )
        if response.status_code != 200:
            raise SpoonacularAPIError(
                f"Неожиданный ответ API (HTTP {response.status_code})."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise SpoonacularAPIError("API вернул некорректный JSON.") from exc

    def _find_by_ingredients(self, ingredients: str, number: int) -> List[Dict[str, Any]]:
        """Запрашивает рецепты по списку ингредиентов.

        Args:
            ingredients: Нормализованная строка ингредиентов через запятую.
            number: Максимальное количество рецептов.

        Returns:
            Сырой список рецептов из API (может быть пустым).
        """
        data = self._make_request(
            self.ENDPOINT_FIND_BY_INGREDIENTS,
            {
                "ingredients": ingredients,
                "number": number,
                "ranking": 1,
                "ignorePantry": "true",
            },
        )
        return data if isinstance(data, list) else []

    def _search_recipes(self, query: str, number: int) -> Dict[str, Any]:
        """Запрашивает рецепты по названию/кухне/диете.

        Args:
            query: Поисковый запрос.
            number: Количество результатов.

        Returns:
            Сырой ответ complexSearch со списком results.
        """
        return self._make_request(
            self.ENDPOINT_COMPLEX_SEARCH,
            {"query": query, "number": number, "instructionsRequired": "true"},
        )

    def _get_recipe_info(self, recipe_id: int, include_nutrition: bool) -> Dict[str, Any]:
        """Запрашивает полную карточку рецепта по id.

        Args:
            recipe_id: Идентификатор рецепта.
            include_nutrition: Включать ли объект nutrition (+0.1 очка).

        Returns:
            Сырая карточка рецепта.
        """
        return self._make_request(
            self.ENDPOINT_RECIPE_INFORMATION.format(recipe_id=recipe_id),
            {"includeNutrition": "true" if include_nutrition else "false"},
        )

    def _get_random_recipe(self) -> Dict[str, Any]:
        """Запрашивает один случайный рецепт.

        Returns:
            Сырая карточка случайного рецепта.

        Raises:
            RecipeNotFoundError: если API не вернул ни одного рецепта.
        """
        data = self._make_request(self.ENDPOINT_RANDOM, {"number": 1})
        recipes = data.get("recipes", []) if isinstance(data, dict) else []
        if not recipes:
            raise RecipeNotFoundError("API не вернул случайный рецепт.")
        return recipes[0]

    def _get_substitutes(self, ingredient: str) -> Dict[str, Any]:
        """Запрашивает замены для ингредиента.

        Args:
            ingredient: Название ингредиента в нижнем регистре.

        Returns:
            Сырой ответ с ключами ingredient/substitutes/message.
        """
        return self._make_request(
            self.ENDPOINT_SUBSTITUTES, {"ingredientName": ingredient}
        )

    def _analyze_nutrition(self, nutrition: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует питание рецепта и формирует человекочитаемый вывод.

        Шкала калорийности НА ПОРЦИЮ (нутриент "Calories"):
            Лёгкое    — Calories < 300
            Умеренное — 300 <= Calories < 600
            Сытное    — 600 <= Calories < 800
            Тяжёлое   — Calories >= 800

        Дополнительно выделяет "выбросы": сахар > 20 г, насыщенные жиры > 10 г,
        натрий > 800 мг на порцию.

        Args:
            nutrition: Объект nutrition из ответа /recipes/{id}/information.

        Returns:
            Словарь с меткой, БЖУ, предупреждениями и human_summary.
        """
        nutrients = nutrition.get("nutrients", []) if isinstance(nutrition, dict) else []
        calories = find_nutrient(nutrients, "Calories")
        protein = find_nutrient(nutrients, "Protein")
        fat = find_nutrient(nutrients, "Fat")
        sat_fat = find_nutrient(nutrients, "Saturated Fat")
        carbs = find_nutrient(nutrients, "Carbohydrates")
        sugar = find_nutrient(nutrients, "Sugar")
        sodium = find_nutrient(nutrients, "Sodium")

        def _amount(nutrient: Optional[Dict[str, Any]]) -> float:
            """Достаёт числовое значение нутриента или возвращает 0.0."""
            if not nutrient:
                return 0.0
            try:
                return float(nutrient.get("amount", 0.0))
            except (TypeError, ValueError):
                return 0.0

        calories_value = _amount(calories)

        if calories_value < self.CALORIE_LIGHT:
            label = "Лёгкое"
            summary = (
                f"Блюдо лёгкое ({calories_value:.0f} ккал на порцию). "
                "Подходит для перекуса."
            )
        elif calories_value < self.CALORIE_MODERATE:
            label = "Умеренное"
            summary = (
                f"Блюдо умеренной калорийности ({calories_value:.0f} ккал на порцию). "
                "Сбалансированный приём пищи."
            )
        elif calories_value < self.CALORIE_HEAVY:
            label = "Сытное"
            summary = (
                f"Блюдо сытное ({calories_value:.0f} ккал на порцию). "
                "Основательный обед или ужин."
            )
        else:
            label = "Тяжёлое"
            summary = (
                f"Блюдо очень калорийное ({calories_value:.0f} ккал на порцию). "
                "Учтите в дневном рационе."
            )

        warnings: List[str] = []
        sugar_value = _amount(sugar)
        sat_fat_value = _amount(sat_fat)
        sodium_value = _amount(sodium)
        if sugar_value > self.SUGAR_LIMIT_G:
            warnings.append(f"⚠️ Много сахара: {sugar_value:.0f} г на порцию.")
        if sat_fat_value > self.SATURATED_FAT_LIMIT_G:
            warnings.append(
                f"⚠️ Много насыщенных жиров: {sat_fat_value:.0f} г на порцию."
            )
        if sodium_value > self.SODIUM_LIMIT_MG:
            warnings.append(f"⚠️ Много соли: {sodium_value:.0f} мг на порцию.")

        breakdown = (
            nutrition.get("caloricBreakdown", {}) if isinstance(nutrition, dict) else {}
        )
        human_summary = summary + (" " + " ".join(warnings) if warnings else "")

        return {
            "label": label,
            "calories_per_serving": calories_value,
            "protein_g": _amount(protein),
            "fat_g": _amount(fat),
            "carbs_g": _amount(carbs),
            "sugar_g": sugar_value,
            "sodium_mg": sodium_value,
            "caloric_breakdown": {
                "protein": breakdown.get("percentProtein", 0.0),
                "fat": breakdown.get("percentFat", 0.0),
                "carbs": breakdown.get("percentCarbs", 0.0),
            },
            "warnings": warnings,
            "human_summary": human_summary,
        }

    # ------------------------------------------------------------------
    # Форматирование карточек
    # ------------------------------------------------------------------

    def _format_recipe_card(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Приводит сырой ответ API к формату карточки рецепта.

        Args:
            raw: Сырой объект рецепта в формате /recipes/{id}/information.

        Returns:
            Карточка с полями id, title, image, servings, ready_in_minutes,
            ingredients, instructions, summary.
        """
        return {
            "id": raw.get("id"),
            "title": raw.get("title", ""),
            "image": raw.get("image", ""),
            "servings": raw.get("servings", 0),
            "ready_in_minutes": raw.get("readyInMinutes", 0),
            "ingredients": [
                ing.get("original", "")
                for ing in raw.get("extendedIngredients", [])
                if ing.get("original")
            ],
            "instructions": self._extract_instructions(raw.get("analyzedInstructions", [])),
            "summary": strip_html(raw.get("summary", "")),
        }

    @staticmethod
    def _extract_instructions(analyzed: List[Dict[str, Any]]) -> List[str]:
        """Извлекает тексты шагов приготовления из analyzedInstructions.

        Args:
            analyzed: Значение поля analyzedInstructions из ответа API.

        Returns:
            Список текстов шагов по порядку.
        """
        steps: List[str] = []
        for block in analyzed or []:
            for step in block.get("steps", []):
                text = step.get("step", "")
                if text:
                    steps.append(text)
        return steps

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def find_recipes_by_ingredients(
        self, ingredients: str, number: int = 5
    ) -> List[Dict[str, Any]]:
        """Ищет рецепты, которые можно приготовить из указанных ингредиентов.

        Args:
            ingredients: Строка ингредиентов через запятую, например
                "apples, flour, sugar" (пробелы нормализуются).
            number: Максимальное количество рецептов (1–100).

        Returns:
            Список словарей: id, title, image, likes, used_count,
            missed_count, used_ingredients, missed_ingredients.

        Raises:
            ValueError: если список ингредиентов пуст.
            SpoonacularAPIError: ошибки API (401/402/404/сеть).
        """
        normalized = normalize_ingredients(ingredients)
        raw_recipes = self._find_by_ingredients(normalized, number)

        results: List[Dict[str, Any]] = []
        for item in raw_recipes:
            results.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "image": item.get("image", ""),
                    "likes": item.get("likes", 0),
                    "used_count": item.get("usedIngredientCount", 0),
                    "missed_count": item.get("missedIngredientCount", 0),
                    "used_ingredients": [
                        ing.get("original") or ing.get("name", "")
                        for ing in item.get("usedIngredients", [])
                    ],
                    "missed_ingredients": [
                        ing.get("original") or ing.get("name", "")
                        for ing in item.get("missedIngredients", [])
                    ],
                }
            )
        return results

    def search_recipes(self, query: str, number: int = 5) -> List[Dict[str, Any]]:
        """Ищет рецепты по названию блюда или кухне.

        Args:
            query: Поисковый запрос, например "pasta".
            number: Количество результатов (1–100).

        Returns:
            Список словарей: id, title, image.

        Raises:
            ValueError: если запрос пуст.
            SpoonacularAPIError: ошибки API.
        """
        if not query or not query.strip():
            raise ValueError("Поисковый запрос пуст")
        data = self._search_recipes(query.strip(), number)
        results = data.get("results", []) if isinstance(data, dict) else []
        return [
            {
                "id": item.get("id"),
                "title": item.get("title", ""),
                "image": item.get("image", ""),
            }
            for item in results
        ]

    def get_recipe_details(self, recipe_id: int, extended: bool = False) -> Dict[str, Any]:
        """Возвращает карточку рецепта по id.

        Args:
            recipe_id: Идентификатор рецепта в Spoonacular.
            extended: True — добавить анализ питания и расширенные поля
                (health_score, price_per_serving, diets, cuisines, dish_types,
                flags). Внимание: включение nutrition стоит +0.1 очка.

        Returns:
            Карточка рецепта; при extended=True содержит также
            nutrition_analysis — результат _analyze_nutrition().

        Raises:
            RecipeNotFoundError: рецепт не найден.
            SpoonacularAPIError: прочие ошибки API.
        """
        raw = self._get_recipe_info(recipe_id, include_nutrition=extended)
        card = self._format_recipe_card(raw)

        if extended:
            card["nutrition_analysis"] = self._analyze_nutrition(raw.get("nutrition") or {})
            card["health_score"] = raw.get("healthScore")
            card["price_per_serving"] = raw.get("pricePerServing")
            card["diets"] = raw.get("diets", [])
            card["cuisines"] = raw.get("cuisines", [])
            card["dish_types"] = raw.get("dishTypes", [])
            card["flags"] = {
                "vegan": bool(raw.get("vegan")),
                "vegetarian": bool(raw.get("vegetarian")),
                "gluten_free": bool(raw.get("glutenFree")),
                "dairy_free": bool(raw.get("dairyFree")),
            }
        return card

    def get_recipe_of_the_day(self) -> Dict[str, Any]:
        """Возвращает карточку случайного рецепта ("рецепт дня").

        Нутриенты здесь не запрашиваются (+0.5 очка за рецепт) — для БЖУ
        используйте get_recipe_details(id, extended=True).

        Returns:
            Карточка рецепта в базовом формате.

        Raises:
            RecipeNotFoundError: если API не вернул рецепт.
            SpoonacularAPIError: прочие ошибки API.
        """
        return self._format_recipe_card(self._get_random_recipe())

    def get_substitutes(self, ingredient: str) -> Dict[str, Any]:
        """Возвращает замены для ингредиента.

        Args:
            ingredient: Название ингредиента, например "butter".

        Returns:
            Словарь: ingredient, substitutes (список строк), message.
            Если замен нет — substitutes будет пустым списком
            (это НЕ сетевая ошибка).

        Raises:
            ValueError: если название пустое.
            SpoonacularAPIError: ошибки API.
        """
        if not ingredient or not ingredient.strip():
            raise ValueError("Название ингредиента пусто")
        normalized = ingredient.strip().lower()
        data = self._get_substitutes(normalized)
        return {
            "ingredient": data.get("ingredient", normalized),
            "substitutes": list(data.get("substitutes") or []),
            "message": data.get("message", ""),
        }
