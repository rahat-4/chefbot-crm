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


class MenuStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DELETED = "DELETED", "Deleted"


class RewardType(models.TextChoices):
    DRINK = "DRINK", "Drink"
    DESSERT = "DESSERT", "Dessert"
    DISCOUNT = "DISCOUNT", "Discount"
    CUSTOM = "CUSTOM", "Custom"


class TriggerType(models.TextChoices):
    BIRTHDAY = "BIRTHDAY", "Birthday"
    MENU_SELECTED = "MENU_SELECTED", "Menu Selected"
    INACTIVITY = "INACTIVITY", "Inactivity"
    RESERVATION = "RESERVATION", "Reservation"
