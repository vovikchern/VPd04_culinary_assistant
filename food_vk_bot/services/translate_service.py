"""Обёртка над MyMemoryAPI: один экземпляр на весь бот, общий кэш."""

from __future__ import annotations

import logging
import re
from typing import List

from mymemory_api import MyMemoryAPI

logger = logging.getLogger(__name__)

#: Признак кириллицы во вводе пользователя
_CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
#: Шаблон для удаления HTML-тегов из переведённых текстов
_HTML_RE = re.compile(r"<[^>]+>")

#: Рабочий лимит длины одного запроса к MyMemory (запас до 500)
_MAX_QUERY_CHARS = 480


class TranslateService:
    """Перевод текстов рецептов и пользовательского ввода.

    Использует единственный экземпляр MyMemoryAPI — кэш переводов общий,
    повторные тексты не тратят дневную квоту.
    """

    def __init__(self) -> None:
        """Создаёт клиент MyMemory (email и fallback читаются из .env)."""
        self._api = MyMemoryAPI()

    def translate(self, text: str) -> str:
        """Переводит текст en→ru и очищает от HTML-тегов.

        Args:
            text: Исходный текст (обычно английский).

        Returns:
            Переведённый текст без HTML-тегов.
        """
        translated = self._api.translate(text)
        return _HTML_RE.sub(" ", translated).strip()

    def to_english(self, text: str) -> str:
        """Переводит пользовательский ввод ru→en при наличии кириллицы.

        Args:
            text: Введённый текст (запрос или ингредиент).

        Returns:
            Текст на английском; исходный, если кириллицы нет.
        """
        if not _CYRILLIC_RE.search(text):
            return text
        return self._api.translate(text, source="ru", target="en")

    def ingredients_to_english(self, ingredients: str) -> str:
        """Переводит список ингредиентов ru→en по одному элементу.

        Args:
            ingredients: Строка вида "яблоки, мука, сахар".

        Returns:
            Строка вида "apples,flour,sugar" для SpoonacularAPI.
        """
        if not _CYRILLIC_RE.search(ingredients):
            return ingredients
        items = [part.strip() for part in ingredients.split(",") if part.strip()]
        translated = [
            self._api.translate(item, source="ru", target="en") for item in items
        ]
        return ",".join(translated)

    def translate_lines(self, items: List[str]) -> List[str]:
        """Переводит список коротких строк, экономя квоту.

        Если все строки вместе влезают в один запрос (лимит MyMemory —
        500 символов), они склеиваются переводом "\\n" и отправляются
        одним запросом; при несовпадении числа строк — поштучный перевод.

        Args:
            items: Список строк (названия рецептов, ингредиенты, замены).

        Returns:
            Список переведённых строк той же длины.
        """
        if not items:
            return []
        joined = "\n".join(items)
        if len(joined) <= _MAX_QUERY_CHARS:
            try:
                translated = self.translate(joined)
                lines = [line.strip() for line in translated.split("\n") if line.strip()]
                if len(lines) == len(items):
                    return lines
                logger.warning(
                    "Пакетный перевод дал %d строк из %d — перевожу поштучно",
                    len(lines),
                    len(items),
                )
            except Exception:  # noqa: BLE001 — демо-устойчивость: любой сбой → поштучно
                logger.exception("Пакетный перевод не удался, перевожу поштучно")
        return [self.translate(item) for item in items]
