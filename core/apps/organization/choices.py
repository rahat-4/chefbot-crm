from django.db import models


class OrganizationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DELETED = "DELETED", "Deleted"


class OrganizationType(models.TextChoices):
    RESTAURANT = "RESTAURANT", "Restaurant"
    BAR = "BAR", "Bar"
    CAFE = "CAFE", "Cafe"


class DaysOfWeek(models.TextChoices):
    MONDAY = "MONDAY", "Monday"
    TUESDAY = "TUESDAY", "Tuesday"
    WEDNESDAY = "WEDNESDAY", "Wednesday"
    THURSDAY = "THURSDAY", "Thursday"
    FRIDAY = "FRIDAY", "Friday"
    SATURDAY = "SATURDAY", "Saturday"
    SUNDAY = "SUNDAY", "Sunday"

    def __str__(self):
        return self.label


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


class ReservationDuration(models.IntegerChoices):
    HOUR_1 = 60, "1 hour"
    HOUR_1_5 = 90, "1.5 hours"
    HOUR_2 = 120, "2 hours"
    HOUR_3 = 180, "3 hours"
    HOUR_4 = 240, "4 hours"

    def __str__(self):
        return self.label


class ReservationReminder(models.IntegerChoices):
    MINUTES_30 = 30, "30 minutes"
    MINUTES_45 = 45, "45 minutes"
    HOUR_1 = 60, "1 hour"

    def __str__(self):
        return self.label


class MessageTemplateType(models.TextChoices):
    BIRTHDAY = "BIRTHDAY", "Birthday"
    MENU_SELECTED = "MENU_SELECTED", "Menu Selected"
    INACTIVITY = "INACTIVITY", "Inactivity"
    RESERVATION_COUNT = "RESERVATION_COUNT", "Reservation Count"
    REMINDER = "REMINDER", "Reminder"

    def __str__(self):
        return self.label
