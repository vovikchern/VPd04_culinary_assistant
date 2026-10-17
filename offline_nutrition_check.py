"""Офлайн-проверка бизнес-логики _analyze_nutrition без расхода квоты API.

Запуск: python offline_nutrition_check.py
Файл временный — можно удалить после проверки.
"""

from spoonacular_api.client import SpoonacularAPI

# Пример объекта nutrition из документации Spoonacular
SAMPLE = {
    "nutrients": [
        {"name": "Calories", "amount": 584.0, "unit": "kcal", "percentOfDailyNeeds": 29.2},
        {"name": "Fat", "amount": 20.0, "unit": "g", "percentOfDailyNeeds": 30.77},
        {"name": "Saturated Fat", "amount": 12.09, "unit": "g", "percentOfDailyNeeds": 60.45},
        {"name": "Carbohydrates", "amount": 49.25, "unit": "g", "percentOfDailyNeeds": 16.42},
        {"name": "Sugar", "amount": 21.98, "unit": "g", "percentOfDailyNeeds": 24.42},
        {"name": "Sodium", "amount": 279.1, "unit": "mg", "percentOfDailyNeeds": 12.13},
        {"name": "Protein", "amount": 19.0, "unit": "g", "percentOfDailyNeeds": 38.0},
    ],
    "caloricBreakdown": {"percentProtein": 4.72, "percentFat": 33.9, "percentCarbs": 61.38},
    "weightPerServing": {"amount": 138, "unit": "g"},
}

# Экземпляр без инициализации сессии и ключа — нужен только анализатор
api = SpoonacularAPI.__new__(SpoonacularAPI)

result = api._analyze_nutrition(SAMPLE)
print("human_summary:", result["human_summary"])
assert result["label"] == "Умеренное", result["label"]
assert len(result["warnings"]) == 2, result["warnings"]
assert result["calories_per_serving"] == 584.0
assert result["protein_g"] == 19.0


def label_for(calories: float) -> str:
    """Возвращает метку шкалы для заданного значения калорий."""
    sample = {
        "nutrients": [{"name": "Calories", "amount": calories, "unit": "kcal"}],
        "caloricBreakdown": {},
    }
    return api._analyze_nutrition(sample)["label"]


assert label_for(250) == "Лёгкое"
assert label_for(350) == "Умеренное"
assert label_for(650) == "Сытное"
assert label_for(900) == "Тяжёлое"

print("OK: шкала калорийности и выбросы работают корректно")
