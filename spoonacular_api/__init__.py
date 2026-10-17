"""spoonacular_api — клиент Spoonacular API для кулинарного VK-бота.

Публичный интерфейс:
    from spoonacular_api import SpoonacularAPI

    api = SpoonacularAPI()
    recipes = api.find_recipes_by_ingredients("apples,flour,sugar")
    card = api.get_recipe_details(716429, extended=True)
    print(card["nutrition_analysis"]["human_summary"])
"""

from .client import SpoonacularAPI
from .exceptions import (
    APIConnectionError,
    InvalidAPIKeyError,
    QuotaExceededError,
    RecipeNotFoundError,
    SpoonacularAPIError,
)

__version__ = "1.0.0"

__all__ = [
    "SpoonacularAPI",
    "SpoonacularAPIError",
    "RecipeNotFoundError",
    "APIConnectionError",
    "QuotaExceededError",
    "InvalidAPIKeyError",
]
