DAY_TRANSLATIONS = {
    "ENGLISH": {
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
    },
    "GERMAN": {
        "monday": "Montag",
        "tuesday": "Dienstag",
        "wednesday": "Mittwoch",
        "thursday": "Donnerstag",
        "friday": "Freitag",
        "saturday": "Samstag",
        "sunday": "Sonntag",
    },
}


def translate_day(language, day_key):
    lang = language.upper()
    return DAY_TRANSLATIONS.get(lang, {}).get(day_key.lower(), day_key)
