"""FSM-состояния бота (StateDispenser)."""

from vkbottle import BaseStateGroup


class BotState(BaseStateGroup):
    """Группа состояний пользователя.

    WAITING_RECIPE_CARD / WAITING_RECIPE_EXTENDED хранят в payload
    список рецептов последнего поиска: recipes=[{id, title}, ...].
    """

    WAITING_INGREDIENTS = "waiting_ingredients"
    WAITING_SEARCH_QUERY = "waiting_search_query"
    WAITING_RECIPE_CARD = "waiting_recipe_card"
    WAITING_RECIPE_EXTENDED = "waiting_recipe_extended"
