def function_tools(sales_level):
    """
    Returns function tools for restaurant customer support based on sales level.

    Args:
        sales_level (int): Level determining available functions

    Returns:
        list: List of function tool definitions
    """

    if sales_level == 1:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_restaurant_information",
                    "description": "Retrieve specific restaurant details such as contact information, location, hours, or website. Use this when customers ask about basic restaurant information.",
                    "parameters": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "title": "Information Query",
                                "description": "The specific information requested by the customer. Examples: 'name', 'phone number', 'email', 'website', 'address', 'location', 'opening hours', 'closing time'.",
                                "enum": [
                                    "name",
                                    "phone_number",
                                    "email",
                                    "website",
                                    "address",
                                    "location",
                                    "opening_hours",
                                    "contact_info",
                                    "all_info",
                                ],
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_menu_items",
                    "description": "Retrieve menu items filtered by category and dietary classification. Always collect both category and classification preferences before calling this function.",
                    "parameters": {
                        "type": "object",
                        "required": ["category", "classification"],
                        "properties": {
                            "category": {
                                "type": "string",
                                "title": "Menu Category",
                                "enum": [
                                    "STARTERS",
                                    "MAIN_COURSES",
                                    "DESSERTS",
                                    "DRINKS_ALCOHOLIC",
                                    "DRINKS_NON_ALCOHOLIC",
                                    "SPECIALS",
                                ],
                                "description": "Menu category to filter by. Use 'ALL' to show items from all categories.",
                            },
                            "classification": {
                                "type": "string",
                                "title": "Dietary Classification",
                                "enum": ["MEAT", "FISH", "VEGETARIAN", "VEGAN"],
                                "description": "Dietary classification to filter by.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_available_tables",
                    "description": "Check table availability for a specific date and optionally time. Always ask customers for their preferred date, and time if possible, before calling this function.",
                    "parameters": {
                        "type": "object",
                        "required": ["date", "guests"],
                        "properties": {
                            "date": {
                                "type": "string",
                                "format": "date",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                                "title": "Reservation Date",
                                "description": "Reservation date in YYYY-MM-DD format (e.g., 2024-12-25).",
                            },
                            "time": {
                                "type": "string",
                                "format": "time",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "title": "Preferred Time",
                                "description": "Optional preferred reservation time in HH:MM 24-hour format (e.g., 19:30, 14:00).",
                            },
                            "guests": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "title": "Number of Guests",
                                "description": "Total number of guests including the person making the reservation (minimum 1, maximum 50).",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "book_table",
                    "description": "Create a new table reservation. Ensure ALL required information is collected from the customer before calling this function. Do not proceed with incomplete information.",
                    "parameters": {
                        "type": "object",
                        "required": [
                            "name",
                            "phone_number",
                            "date",
                            "time",
                            "guests",
                            "booking_reason",
                        ],
                        "properties": {
                            "reservation_name": {
                                "type": "string",
                                "title": "Name for Reservation",
                                "description": "Full name of the person making the reservation.",
                                "minLength": 1,
                            },
                            "phone_number": {
                                "type": "string",
                                "title": "Contact Number",
                                "description": "Customer's phone number (WhatsApp preferred) with country code if international.",
                                "pattern": "^[+]?[0-9\\s\\-\\(\\)]{10,15}$",
                            },
                            "date": {
                                "type": "string",
                                "format": "date",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                                "title": "Reservation Date",
                                "description": "Reservation date in YYYY-MM-DD format.",
                            },
                            "time": {
                                "type": "string",
                                "format": "time",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "title": "Reservation Time",
                                "description": "Reservation time in HH:MM 24-hour format (e.g., 19:30, 13:00).",
                            },
                            "guests": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "title": "Number of Guests",
                                "description": "Total number of guests including the person making the reservation (minimum 1, maximum 50).",
                            },
                            "booking_reason": {
                                "type": "string",
                                "title": "Occasion/Reason",
                                "description": "Reason for the reservation (e.g., 'Birthday', 'Anniversary', 'Business Meeting', 'Family Dinner', 'Casual Dining').",
                                "minLength": 1,
                            },
                            "special_notes": {
                                "type": "string",
                                "title": "Special Requests",
                                "description": "Optional special requests, dietary restrictions, seating preferences, or other notes.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_menu_to_reservation",
                    "description": "Add selected menu items to an existing confirmed reservation. Only use this after a reservation has been successfully created and customer wants to pre-order food.",
                    "parameters": {
                        "type": "object",
                        "required": ["reservation_uid", "menu_items"],
                        "properties": {
                            "reservation_uid": {
                                "type": "string",
                                "title": "Reservation ID",
                                "description": "Unique identifier of the existing reservation to update.",
                                "minLength": 1,
                            },
                            "menu_items": {
                                "type": "array",
                                "title": "Menu Items",
                                "description": "List of menu items to add to the reservation.",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "required": ["menu_name", "quantity"],
                                    "properties": {
                                        "menu_name": {
                                            "type": "string",
                                            "title": "Menu Item Name",
                                            "description": "Exact name of the menu item as it appears in the menu.",
                                            "minLength": 1,
                                        },
                                        "quantity": {
                                            "type": "integer",
                                            "minimum": 1,
                                            "maximum": 20,
                                            "title": "Quantity",
                                            "description": "Number of this menu item to add (minimum 1, maximum 20 per item).",
                                        },
                                        "special_instructions": {
                                            "type": "string",
                                            "title": "Special Instructions",
                                            "description": "Optional cooking preferences or modifications for this item.",
                                        },
                                    },
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_reservation",
                    "description": "Cancel an existing table reservation. Always ask for both customer's phone number and cancellation reason before proceeding.",
                    "parameters": {
                        "type": "object",
                        "required": ["reservation_code", "cancellation_reason"],
                        "properties": {
                            "reservation_code": {
                                "type": "string",
                                "title": "Reservation Code",
                                "description": "Unique identifier of the reservation to cancel.",
                                "minLength": 1,
                            },
                            "cancellation_reason": {
                                "type": "string",
                                "title": "Cancellation Reason",
                                "description": "Customer's reason for cancelling the reservation (e.g., 'Change of plans', 'Emergency', 'Schedule conflict').",
                                "minLength": 1,
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
        ]

    else:
        # Handle other sales levels if needed in the future
        tools = []

    return tools
