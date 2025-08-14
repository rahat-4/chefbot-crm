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


class OpeningHoursStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    BREAK = "BREAK", "Break"
    CLOSED = "CLOSED", "Closed"
