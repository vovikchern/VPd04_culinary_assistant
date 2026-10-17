"""Конфигурация модуля mymemory_api.

Читает настройки из переменных окружения (файл .env):
- MYMEMORY_EMAIL — email для повышения дневного лимита (не секрет);
- MYMEMORY_USE_FALLBACK — включать резервный переводчик Google.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

#: Логгер модуля
logger = logging.getLogger(__name__)

#: Шаблон корректного email (только ASCII — MyMemory отвергает кириллицу)
_EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")

#: Корень проекта (родительская папка модуля)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv()

#: Имя переменной окружения с email для MyMemory
MYMEMORY_EMAIL_ENV: str = "MYMEMORY_EMAIL"

#: Имя переменной окружения с флагом резервного переводчика
MYMEMORY_USE_FALLBACK_ENV: str = "MYMEMORY_USE_FALLBACK"

#: Таймаут HTTP-запросов, секунд
REQUEST_TIMEOUT: int = 15

#: Рабочий лимит длины одного запроса (запас 20 символов до официального 500)
MAX_QUERY_CHARS: int = 480

#: Жёсткий лимит MyMemory на длину запроса
HARD_LIMIT_CHARS: int = 500


def get_email() -> str:
    """Возвращает email для MyMemory из окружения (может быть пустым).

    Некорректное значение (плейсхолдер, кириллица, опечатка) игнорируется
    с предупреждением в лог — запросы пойдут анонимно (5000 символов/сутки).
    С корректным email лимит повышается до 50000 символов/сутки.

    Returns:
        Корректный email или пустую строку.
    """
    email = os.getenv(MYMEMORY_EMAIL_ENV, "").strip()
    if email and not _EMAIL_RE.match(email):
        logger.warning(
            "MYMEMORY_EMAIL выглядит некорректно (%r) — параметр de "
            "не будет отправлен, запросы пойдут анонимно. Впишите "
            "реальный email латиницей в .env для лимита 50000 симв/сутки.",
            email,
        )
        return ""
    return email


def use_fallback() -> bool:
    """Возвращает флаг включения резервного переводчика Google.

    Значения "1", "true", "yes", "да" (в любом регистре) считаются включённым
    флагом; по умолчанию fallback включён.

    Returns:
        True, если резервный переводчик разрешён.
    """
    return os.getenv(MYMEMORY_USE_FALLBACK_ENV, "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "да",
    )
