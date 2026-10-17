"""Конфигурация модуля spoonacular_api.

Читает API-ключ из переменной окружения SPOONACULAR_API_KEY.
Файл .env ищется в корне проекта (на уровень выше модуля) и в текущей директории.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import InvalidAPIKeyError

#: Корень проекта (родительская папка модуля)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Загружаем .env из корня проекта, затем из текущей рабочей директории
load_dotenv(BASE_DIR / ".env")
load_dotenv()

#: Имя переменной окружения с ключом Spoonacular
API_KEY_ENV: str = "SPOONACULAR_API_KEY"

#: Базовый URL Spoonacular API
BASE_URL: str = "https://api.spoonacular.com"

#: Таймаут HTTP-запросов, секунд
REQUEST_TIMEOUT: int = 10


def get_api_key() -> str:
    """Возвращает API-ключ Spoonacular из окружения.

    Returns:
        Непустое значение переменной SPOONACULAR_API_KEY.

    Raises:
        InvalidAPIKeyError: если ключ не задан в .env или переменных окружения.
    """
    key = os.getenv(API_KEY_ENV, "").strip()
    if not key:
        raise InvalidAPIKeyError(
            "API-ключ не найден. Задайте переменную SPOONACULAR_API_KEY в файле .env"
        )
    return key
