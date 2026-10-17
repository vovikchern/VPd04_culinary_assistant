"""Иерархия исключений модуля mymemory_api."""


class MyMemoryAPIError(Exception):
    """Базовое исключение для всех ошибок модуля перевода."""


class TranslationQuotaExceededError(MyMemoryAPIError):
    """Исчерпана дневная квота переводчика (5000/50000 символов в сутки)."""


class InvalidLanguagePairError(MyMemoryAPIError):
    """Неверная пара языков: unsupported пара или совпадающие языки."""


class APIConnectionError(MyMemoryAPIError):
    """Сетевая ошибка: таймаут, недоступность сервиса или HTTP 5xx."""


class QueryTooLongError(MyMemoryAPIError):
    """Часть запроса длиннее 500 символов — защита от программной ошибки."""
