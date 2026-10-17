"""Иерархия исключений модуля spoonacular_api."""


class SpoonacularAPIError(Exception):
    """Базовое исключение для всех ошибок Spoonacular API."""


class InvalidAPIKeyError(SpoonacularAPIError):
    """Ошибка аутентификации: неверный или отсутствующий API-ключ (HTTP 401)."""


class QuotaExceededError(SpoonacularAPIError):
    """Превышен дневной лимит очков бесплатного тарифа (HTTP 402)."""


class RecipeNotFoundError(SpoonacularAPIError):
    """Запрошенный рецепт или ресурс не найден (HTTP 404)."""


class APIConnectionError(SpoonacularAPIError):
    """Сетевая ошибка: таймаут, недоступность сервиса или ответ 5xx."""
