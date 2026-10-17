"""Вспомогательные функции модуля mymemory_api."""

from __future__ import annotations

import re
from typing import List

#: Разбиение на предложения: [.!?] + пробел или перевод строки
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    """Режет одиночное предложение по словам на части не длиннее max_chars.

    Слово длиннее max_chars разрезается по символам.

    Args:
        sentence: Предложение без переводов строк.
        max_chars: Максимальная длина части.

    Returns:
        Список частей предложения.
    """
    parts: List[str] = []
    current = ""
    for word in sentence.split():
        if len(word) > max_chars:
            if current:
                parts.append(current)
                current = ""
            for start in range(0, len(word), max_chars):
                parts.append(word[start : start + max_chars])
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current = f"{current} {word}"
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts


def split_into_chunks(text: str, max_chars: int) -> List[str]:
    """Нарезает текст на части не длиннее max_chars по предложениям.

    Алгоритм:
    1. Текст делится на предложения по границам [.!?] + пробел и по
       переводам строк.
    2. Предложения накапливаются в часть, пока длина части + очередное
       предложение + пробел не превысят max_chars.
    3. Одиночное предложение длиннее max_chars режется по словам.
    4. Слово длиннее max_chars режется по символам.

    Args:
        text: Исходный текст любой длины.
        max_chars: Максимальная длина одной части.

    Returns:
        Список частей (может быть пустым для пустого текста).
    """
    if not text or not text.strip():
        return []

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s and s.strip()]

    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_sentence(sentence, max_chars))
            continue
        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= max_chars:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks
