"""mymemory_api — клиент перевода через MyMemory для кулинарного VK-бота.

Публичный интерфейс:
    from mymemory_api import MyMemoryAPI

    translator = MyMemoryAPI()
    russian = translator.translate("Pasta with tuna. Cook until al dente.")
    print(russian)  # Паста с тунцом. Готовьте до состояния аль денте.
"""

from .client import MyMemoryAPI
from .exceptions import (
    APIConnectionError,
    InvalidLanguagePairError,
    MyMemoryAPIError,
    QueryTooLongError,
    TranslationQuotaExceededError,
)

__version__ = "1.0.0"

__all__ = [
    "MyMemoryAPI",
    "MyMemoryAPIError",
    "TranslationQuotaExceededError",
    "InvalidLanguagePairError",
    "APIConnectionError",
    "QueryTooLongError",
]
