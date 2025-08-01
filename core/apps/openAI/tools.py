tools = [
    {
        "type": "function",
        "function": {
            "name": "book_table",
            "description": "Create a table reservation for the customer. Only call this function after collecting ALL required information (name, phone, date, time, guests).",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Customer's full name for the reservation",
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "Phone number for the reservation (WhatsApp number or alternative provided by customer)",
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Reservation date in YYYY-MM-DD format (e.g., 2024-03-15)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "time": {
                        "type": "string",
                        "format": "time",
                        "description": "Reservation time in HH:MM format using 24-hour time (e.g., 19:30 for 7:30 PM)",
                        "pattern": "^\\d{2}:\\d{2}$",
                    },
                    "guests": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of guests for the reservation (minimum 1 person)",
                    },
                    "special_occasion": {
                        "type": "string",
                        "description": "Special reason for the reservation (birthday, anniversary, date, business, celebration, etc.)",
                    },
                    "preferred_position": {
                        "type": "string",
                        "description": "Preferred seating position in the restaurant (e.g., window, corner, outdoor, etc.). This maps to the table's position field.",
                    },
                    "table_category": {
                        "type": "string",
                        "enum": ["FAMILY", "COUPLE", "SINGLE", "GROUP", "PRIVATE"],
                        "description": "Type of seating arrangement based on party size and occasion. Must match TableCategory choices.",
                    },
                    "allergens": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Food allergies or dietary restrictions (vegetarian, vegan, gluten-free, nuts, etc.)",
                    },
                    "birthday": {
                        "type": "string",
                        "format": "date",
                        "description": "Customer's birthday in YYYY-MM-DD format (only if they mention it's their birthday)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "special_notes": {
                        "type": "string",
                        "description": "Any special requests, occasions, or notes for the reservation",
                    },
                },
                "required": ["customer_name", "phone_number", "date", "time", "guests"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu_items",
            "description": "Fetch menu items based on category and classification to show to the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "STARTERS",
                            "MAIN_COURSES",
                            "DESSERTS",
                            "DRINKS_ALCOHOLIC",
                            "DRINKS_NON_ALCOHOLIC",
                            "SPECIALS",
                        ],
                        "description": "Menu category to filter by",
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["MEAT", "FISH", "VEGETARIAN", "VEGAN"],
                        "description": "Menu classification to filter by",
                    },
                },
                "required": ["category", "classification"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_menu_to_reservation",
            "description": "Add selected menu items to an existing reservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_uid": {
                        "type": "string",
                        "description": "The UID of the reservation to add menus to",
                    },
                    "menu_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "menu_name": {
                                    "type": "string",
                                    "description": "Name of the menu item",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "description": "Quantity of this menu item",
                                },
                            },
                            "required": ["menu_name", "quantity"],
                        },
                        "description": "List of menu items to add to the reservation",
                    },
                },
                "required": ["reservation_uid", "menu_items"],
                "additionalProperties": False,
            },
        },
    },
]
