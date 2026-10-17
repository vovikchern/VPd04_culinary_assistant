"""Клиент перевода через MyMemory для кулинарного VK-бота.

Переводит тексты любой длины: нарезает на части по предложениям (лимит
MyMemory — 500 символов на запрос), переводит каждую часть и склеивает
результат. При сбоях MyMemory используется резервный публичный endpoint
Google Translate (если включён флаг MYMEMORY_USE_FALLBACK).

Повторные переводы кэшируются в памяти экземпляра — сетевые запросы
не выполняются, дневная квота экономится.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .config import (
    HARD_LIMIT_CHARS,
    MAX_QUERY_CHARS,
    REQUEST_TIMEOUT,
    get_email,
    use_fallback,
)
from .exceptions import (
    APIConnectionError,
    InvalidLanguagePairError,
    MyMemoryAPIError,
    QueryTooLongError,
    TranslationQuotaExceededError,
)
from .utils import split_into_chunks


class MyMemoryAPI:
    """Обёртка над MyMemory API с нарезкой текста, кэшем и fallback.

    Использует одну HTTP-сессию (requests.Session) на экземпляр класса.
    Сервис не требует API-ключей; email повышает дневной лимит.
    """

    #: Endpoint перевода MyMemory
    BASE_URL: str = "https://api.mymemory.translated.net/get"
    #: Резервный публичный endpoint Google Translate
    GOOGLE_FALLBACK_URL: str = "https://translate.googleapis.com/translate_a/single"
    #: Рабочий лимит длины запроса
    MAX_QUERY_CHARS: int = MAX_QUERY_CHARS
    #: Жёсткий лимит длины запроса MyMemory
    HARD_LIMIT_CHARS: int = HARD_LIMIT_CHARS

    def __init__(
        self,
        email: Optional[str] = None,
        fallback: Optional[bool] = None,
    ) -> None:
        """Инициализирует клиент и открывает HTTP-сессию.

        Args:
            email: Email для MyMemory; по умолчанию — из переменной
                окружения MYMEMORY_EMAIL.
            fallback: Включать ли резервный переводчик; по умолчанию — из
                переменной окружения MYMEMORY_USE_FALLBACK.
        """
        self._email: str = get_email() if email is None else email
        self._use_fallback: bool = use_fallback() if fallback is None else fallback
        self._session: requests.Session = requests.Session()
        # Стандартный User-Agent python-requests часто блокируется Google (429)
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            }
        )
        self._cache: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _make_request(self, url: str, params: Dict[str, str]) -> Any:
        """Выполняет GET-запрос и возвращает разобранный JSON.

        Args:
            url: Полный адрес endpoint'а.
            params: Query-параметры запроса.

        Returns:
            JSON-ответ (словарь или список).

        Raises:
            APIConnectionError: таймаут, сетевая ошибка, HTTP 5xx или
                некорректный JSON.
        """
        try:
            response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise APIConnectionError(f"Сетевая ошибка при запросе {url}: {exc}") from exc

        if response.status_code >= 500:
            raise APIConnectionError(
                f"Сервис перевода недоступен (HTTP {response.status_code})."
            )
        if response.status_code != 200:
            raise APIConnectionError(
                f"Неожиданный ответ переводчика (HTTP {response.status_code})."
            )
        try:
            return response.json()
        except ValueError as exc:
            raise APIConnectionError("Переводчик вернул некорректный JSON.") from exc

    def _split_into_chunks(self, text: str) -> List[str]:
        """Нарезает текст на части не длиннее MAX_QUERY_CHARS.

        Args:
            text: Исходный текст.

        Returns:
            Список частей текста.
        """
        return split_into_chunks(text, self.MAX_QUERY_CHARS)

    def _translate_chunk_mymemory(self, chunk: str, source: str, target: str) -> str:
        """Переводит одну часть текста через MyMemory.

        Args:
            chunk: Часть текста не длиннее 500 символов.
            source: Код языка исходного текста.
            target: Код языка перевода.

        Returns:
            Переведённый текст части.

        Raises:
            QueryTooLongError: часть длиннее жёсткого лимита.
            TranslationQuotaExceededError: исчерпана дневная квота.
            InvalidLanguagePairError: неверная пара языков.
            MyMemoryAPIError: прочие ошибки сервиса.
        """
        if len(chunk) > self.HARD_LIMIT_CHARS:
            raise QueryTooLongError(
                f"Часть запроса длиннее {self.HARD_LIMIT_CHARS} символов "
                f"({len(chunk)}). Это программная ошибка нарезки."
            )

        params: Dict[str, str] = {"q": chunk, "langpair": f"{source}|{target}"}
        if self._email:
            params["de"] = self._email

        data = self._make_request(self.BASE_URL, params)
        response_data = data.get("responseData") or {}
        translated = str(response_data.get("translatedText") or "")
        status = data.get("responseStatus")
        details = str(data.get("responseDetails") or "").upper()

        quota_marker = "YOU USED ALL TRANSLATION QUOTA"
        if (
            status == 429
            or data.get("quotaFinished")
            or quota_marker in details
            or quota_marker in translated.upper()
        ):
            raise TranslationQuotaExceededError(
                "Дневная квота MyMemory исчерпана. Сработает резервный "
                "переводчик или повторите завтра."
            )

        if "INVALID LANGUAGE PAIR" in details or "DISTINCT LANGUAGES" in details:
            raise InvalidLanguagePairError(
                f"Неверная пара языков {source}|{target}: {data.get('responseDetails', '')}"
            )

        if "QUERY LENGTH LIMIT EXCEEDED" in details or "QUERY LENGTH LIMIT EXCEEDED" in translated.upper():
            raise QueryTooLongError("MyMemory отклонил запрос: превышен лимит длины.")

        if status != 200 or not translated.strip():
            raise MyMemoryAPIError(
                f"MyMemory вернул ошибку (status={status}): {data.get('responseDetails', '')}"
            )
        return translated

    def _translate_chunk_google(self, chunk: str, source: str, target: str) -> str:
        """Переводит одну часть текста через резервный endpoint Google.

        Ответ — список сегментов; сегменты уже содержат завершающие пробелы,
        поэтому склеиваются вплотную.

        Args:
            chunk: Часть текста не длиннее 500 символов.
            source: Код языка исходного текста.
            target: Код языка перевода.

        Returns:
            Переведённый текст части.

        Raises:
            QueryTooLongError: часть длиннее жёсткого лимита.
            APIConnectionError: неожиданный формат ответа или сетевая ошибка.
        """
        if len(chunk) > self.HARD_LIMIT_CHARS:
            raise QueryTooLongError(
                f"Часть запроса длиннее {self.HARD_LIMIT_CHARS} символов "
                f"({len(chunk)}). Это программная ошибка нарезки."
            )

        params: Dict[str, str] = {
            "client": "gtx",
            "sl": source,
            "tl": target,
            "dt": "t",
            "q": chunk,
        }
        data = self._make_request(self.GOOGLE_FALLBACK_URL, params)

        if not isinstance(data, list) or not data or not isinstance(data[0], list):
            raise APIConnectionError("Неожиданный формат ответа Google Translate.")

        segments: List[str] = []
        for item in data[0]:
            if isinstance(item, list) and item and item[0]:
                segments.append(str(item[0]))
        if not segments:
            raise APIConnectionError("Google Translate вернул пустой перевод.")
        return "".join(segments)

    def _translate_chunk(self, chunk: str, source: str, target: str) -> str:
        """Переводит одну часть: сначала MyMemory, при сбое — fallback.

        Args:
            chunk: Часть текста.
            source: Код языка исходного текста.
            target: Код языка перевода.

        Returns:
            Переведённый текст части.

        Raises:
            MyMemoryAPIError: оба переводчика завершились ошибкой.
        """
        try:
            return self._translate_chunk_mymemory(chunk, source, target)
        except (
            APIConnectionError,
            TranslationQuotaExceededError,
            MyMemoryAPIError,
        ) as primary_error:
            if not self._use_fallback:
                raise
            try:
                return self._translate_chunk_google(chunk, source, target)
            except MyMemoryAPIError as fallback_error:
                raise MyMemoryAPIError(
                    f"Основной и резервный переводчик недоступны. "
                    f"Основной: {primary_error} Резервный: {fallback_error}"
                ) from fallback_error

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def translate(self, text: str, source: str = "en", target: str = "ru") -> str:
        """Переводит текст любой длины с нарезкой, кэшем и fallback.

        Пустой/пробельный текст возвращается как пустая строка без
        сетевых запросов. Повторный перевод того же текста берётся из кэша.

        Args:
            text: Исходный текст.
            source: Код языка исходного текста (по умолчанию "en").
            target: Код языка перевода (по умолчанию "ru").

        Returns:
            Переведённый текст.

        Raises:
            InvalidLanguagePairError: совпадающие или неподдерживаемые языки.
            MyMemoryAPIError: оба переводчика недоступны.
        """
        if not text or not text.strip():
            return ""
        if source.strip().lower() == target.strip().lower():
            raise InvalidLanguagePairError(
                "Языки источника и перевода совпадают: выберите два разных языка."
            )

        cache_key = f"{source}|{target}|{text}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        chunks = self._split_into_chunks(text)
        translated_parts = [
            self._translate_chunk(chunk, source, target) for chunk in chunks
        ]
        result = " ".join(part.strip() for part in translated_parts if part.strip())
        self._cache[cache_key] = result
        return result

    def get_cache_size(self) -> int:
        """Возвращает количество записей в кэше переводов.

        Returns:
            Размер кэша.
        """
        return len(self._cache)
