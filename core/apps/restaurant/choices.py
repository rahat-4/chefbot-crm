from django.db import models


class CategoryChoices(models.TextChoices):
    STARTERS = "STARTERS", "Starters"
    MAIN_COURSES = "MAIN_COURSES", "Main Courses"
    DESSERTS = "DESSERTS", "Desserts"
    DRINKS_ALCOHOLIC = "DRINKS_ALCOHOLIC", "Drinks Alcoholic"
    DRINKS_NON_ALCOHOLIC = "DRINKS_NON_ALCOHOLIC", "Drinks Non Alcoholic"
    SPECIALS = "SPECIALS", "Specials"


class ClassificationChoices(models.TextChoices):
    MEAT = "MEAT", "Meat"
    FISH = "FISH", "Fish"
    VEGETARIAN = "VEGETARIAN", "Vegetarian"
    VEGAN = "VEGAN", "Vegan"
