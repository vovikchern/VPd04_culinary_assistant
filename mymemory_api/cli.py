"""Точка входа для тестирования модуля mymemory_api в консоли.

Примеры запуска из корня проекта:
    python -m mymemory_api.cli translate "Hello, world!"
    python -m mymemory_api.cli translate "Cook pasta in boiling water until al dente. Drain and return to warm pot." --source en --target ru
    python -m mymemory_api.cli chunks "Длинный текст для проверки нарезки..."
"""

from __future__ import annotations

import argparse
import sys

from .client import MyMemoryAPI
from .exceptions import MyMemoryAPIError
from .utils import split_into_chunks

#: Рабочий лимит длины части для команды chunks
MAX_QUERY_CHARS = 480


def main() -> int:
    """Разбирает аргументы командной строки и выполняет выбранную команду.

    Returns:
        Код завершения: 0 — успех, 1 — ошибка.
    """
    # Корректный вывод эмодзи и кириллицы в консоли Windows
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Тестирование модуля MyMemoryAPI в консоли"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_translate = subparsers.add_parser("translate", help="Перевод текста")
    parser_translate.add_argument("text", help="Текст для перевода (любой длины)")
    parser_translate.add_argument("--source", default="en", help='Язык источника (по умолчанию "en")')
    parser_translate.add_argument("--target", default="ru", help='Язык перевода (по умолчанию "ru")')

    parser_chunks = subparsers.add_parser(
        "chunks", help="Показать нарезку текста на части (без сетевых запросов)"
    )
    parser_chunks.add_argument("text", help="Текст для проверки нарезки")

    args = parser.parse_args()

    if args.command == "chunks":
        chunks = split_into_chunks(args.text, MAX_QUERY_CHARS)
        print(f"Текст будет нарезан на {len(chunks)} частей (лимит {MAX_QUERY_CHARS} символов):")
        for number, chunk in enumerate(chunks, start=1):
            print(f"  Часть {number} ({len(chunk)} симв.): {chunk}")
        return 0

    try:
        translator = MyMemoryAPI()
        translated = translator.translate(args.text, source=args.source, target=args.target)
        print(f"Перевод ({args.source} → {args.target}):")
        print(translated)
        print(f"\nЗаписей в кэше: {translator.get_cache_size()}")
    except MyMemoryAPIError as exc:
        print(f"Ошибка перевода: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
