"""Клавиатура главного меню."""

from vkbottle import Keyboard, KeyboardButtonColor, Text


def empty_keyboard() -> str:
    """Возвращает пустую клавиатуру, чтобы VK скрывал текущее меню."""
    return Keyboard(one_time=True, inline=False).get_json()


def main_keyboard() -> Keyboard:
    """Собирает стандартную постоянную клавиатуру главного меню."""
    return (
        Keyboard(one_time=False, inline=False)
        .add(
            Text("🍳 Что приготовить?", {"cmd": "ingredients"}),
            color=KeyboardButtonColor.PRIMARY,
        )
        .add(Text("🔍 Найти рецепт", {"cmd": "search"}))
        .row()
        .add(Text("🎲 Рецепт дня", {"cmd": "random"}))
        .add(Text("🥗 Расширенный режим", {"cmd": "extended"}))
        .row()
        .add(Text("📖 Карточка рецепта", {"cmd": "card"}))
        .add(Text("ℹ️ Помощь", {"cmd": "help"}), color=KeyboardButtonColor.SECONDARY)
    )
