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


class YearlyCategory(models.TextChoices):
    ANNIVERSARY = "ANNIVERSARY", "Anniversary"
    BIRTHDAY = "BIRTHDAY", "Birthday"


class TriggerType(models.TextChoices):
    YEARLY = "YEARLY", "Yearly"
    MENU_SELECTED = "MENU_SELECTED", "Menu Selected"
    INACTIVITY = "INACTIVITY", "Inactivity"
    RESERVATION_COUNT = "RESERVATION_COUNT", "Reservation Count"


class ReservationCancelledBy(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    CUSTOMER = "CUSTOMER", "Customer"


class ReservationStatus(models.TextChoices):
    PLACED = "PLACED", "Placed"
    INPROGRESS = "INPROGRESS", "In-progress"
    COMPLETED = "COMPLETED", "Completed"
    RESCHEDULED = "RESCHEDULED", "Rescheduled"
    CANCELLED = "CANCELLED", "Cancelled"
    ABSENT = "ABSENT", "Absent"


class TableCategory(models.TextChoices):
    FAMILY = "FAMILY", "Family"
    COUPLE = "COUPLE", "Couple"
    SINGLE = "SINGLE", "Single"
    GROUP = "GROUP", "Group"
    PRIVATE = "PRIVATE", "Private"


class TableStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"
    RESERVED = "RESERVED", "Reserved"


class ClientSource(models.TextChoices):
    WHATSAPP = "WHATSAPP", "WhatsApp"
    MANUAL = "MANUAL", "Manual"


class ClientMessageRole(models.TextChoices):
    USER = "USER", "User"
    ASSISTANT = "ASSISTANT", "Assistant"


class RestaurantDocumentType(models.TextChoices):
    PDF = "pdf", "PDF"
    DOCX = "docx", "DOCX"
    IMAGE = "image", "Image"


class PromotionSentLogStatus(models.TextChoices):
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    DELIVERED = "DELIVERED", "Delivered"
    READ = "READ", "Read"
    USED = "USED", "Used"


class RewardCategory(models.TextChoices):
    PROMOTION = "PROMOTION", "Promotion"
    SALES_LEVEL = "SALES_LEVEL", "Sales Level"


class OrganizationLanguage(models.TextChoices):
    ENGLISH = "ENGLISH", "English"
    GERMAN = "GERMAN", "German"
    FRENCH = "FRENCH", "French"
    SPANISH = "SPANISH", "Spanish"
    ITALIAN = "ITALIAN", "Italian"
    ARABIC = "ARABIC", "Arabic"

    def __str__(self):
        return self.label


class ChatbotTone(models.TextChoices):
    CASUAL = "CASUAL", "Casual"
    FORMAL = "FORMAL", "Formal"
    HUMOROUS = "HUMOROUS", "Humorous"
    PROFESSIONAL = "PROFESSIONAL", "Professional"

    def __str__(self):
        return self.label
