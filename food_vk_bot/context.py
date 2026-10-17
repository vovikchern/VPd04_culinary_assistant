"""Контекст приложения: единственные экземпляры бота и сервисов.

Инициализируется один раз в main.py (init_context); хендлеры обращаются
к готовым сервисам через ctx.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from vkbottle.bot import Bot

    from food_vk_bot.services.photo_service import PhotoService
    from food_vk_bot.services.recipe_service import RecipeService
    from food_vk_bot.services.translate_service import TranslateService


class AppContext:
    """Контейнер сервисов бота."""

    def __init__(self) -> None:
        self.bot: Optional["Bot"] = None
        self.translator: Optional["TranslateService"] = None
        self.recipes: Optional["RecipeService"] = None
        self.photos: Optional["PhotoService"] = None


#: Единственный экземпляр контекста на процесс
ctx = AppContext()


def init_context(bot: "Bot") -> None:
    """Создаёт сервисы и сохраняет бота в контексте.

    Args:
        bot: Инициализированный Bot (нужен для PhotoService — bot.api).
    """
    from food_vk_bot.services.photo_service import PhotoService
    from food_vk_bot.services.recipe_service import RecipeService
    from food_vk_bot.services.translate_service import TranslateService

    ctx.bot = bot
    ctx.translator = TranslateService()
    ctx.recipes = RecipeService(ctx.translator)
    ctx.photos = PhotoService(bot.api)
