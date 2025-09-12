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
                    "description": "Retrieve specific restaurant details such as contact information, location, hours, or website. Use when customers ask about basic restaurant info.",
                    "parameters": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "title": "Information Query",
                                "description": "Specific info requested. Examples: name, phone number, email, website, address, location, opening hours.",
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
                    "description": "Retrieve menu items filtered by category and dietary classification. Collect both from customer before calling.",
                    "parameters": {
                        "type": "object",
                        "required": ["category", "classification"],
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
                                "description": "Menu category to filter by.",
                            },
                            "classification": {
                                "type": "string",
                                "enum": ["MEAT", "FISH", "VEGETARIAN", "VEGAN"],
                                "description": "Dietary preference.",
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
                    "description": "Check table availability for a given date (and optional time). Accept natural expressions like 'today', 'tomorrow', or 'next Saturday'.",
                    "parameters": {
                        "type": "object",
                        "required": ["date", "guests"],
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Reservation date. Accepts natural phrases like 'today', 'tomorrow', 'next Saturday', or exact YYYY-MM-DD.",
                            },
                            "time": {
                                "type": "string",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "description": "Preferred reservation time in 24h HH:MM format. Optional.",
                            },
                            "guests": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "description": "Total number of guests including the one making the booking.",
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
                    "description": "Create a new reservation. Ensure all info is collected. Phone number is only needed if WhatsApp is not used.",
                    "parameters": {
                        "type": "object",
                        "required": [
                            "reservation_name",
                            "date",
                            "time",
                            "guests",
                            "booking_reason",
                            "use_whatsapp",
                        ],
                        "properties": {
                            "reservation_name": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Full name of the guest making the reservation.",
                            },
                            "reservation_phone": {
                                "type": "string",
                                "pattern": "^[+]?[0-9\\s\\-\\(\\)]{10,15}$",
                                "description": "Phone number (only if WhatsApp is not used).",
                            },
                            "use_whatsapp": {
                                "type": "boolean",
                                "description": "True if WhatsApp number should be used automatically.",
                            },
                            "date": {
                                "type": "string",
                                "description": "Reservation date. Accepts natural phrases like 'today', 'tomorrow', 'next Saturday', or exact YYYY-MM-DD.",
                            },
                            "time": {
                                "type": "string",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "description": "Reservation time in HH:MM format.",
                            },
                            "guests": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Total guests including the reserving person.",
                            },
                            "booking_reason": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Occasion or reason (e.g. 'Birthday', 'Family', 'Business').",
                            },
                            "special_notes": {
                                "type": "string",
                                "description": "Optional notes like seating preferences, allergies, etc.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reschedule_reservation",
                    "description": "Reschedule an existing reservation to a new date and time. This will create a new booking with all existing data and mark the original reservation as RESCHEDULED. Use same parameters as book_table but with original reservation identifiers.",
                    "parameters": {
                        "type": "object",
                        "required": [
                            "original_reservation_date",
                            "reservation_name",
                            "date",
                            "time",
                            "guests",
                            "booking_reason",
                            "use_whatsapp",
                        ],
                        "properties": {
                            "original_reservation_date": {
                                "type": "string",
                                "description": "Original reservation date to identify the reservation to reschedule. Accepts natural phrases like 'today', 'tomorrow', 'next Saturday', or exact YYYY-MM-DD.",
                            },
                            "original_reservation_time": {
                                "type": "string",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "description": "Original reservation time (only needed if multiple bookings on same date).",
                            },
                            "reservation_name": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Full name of the guest (from original reservation).",
                            },
                            "reservation_phone": {
                                "type": "string",
                                "pattern": "^[+]?[0-9\\s\\-\\(\\)]{10,15}$",
                                "description": "Phone number (only if WhatsApp is not used).",
                            },
                            "use_whatsapp": {
                                "type": "boolean",
                                "description": "True if WhatsApp number should be used automatically.",
                            },
                            "date": {
                                "type": "string",
                                "description": "NEW reservation date. Accepts natural phrases like 'today', 'tomorrow', 'next Saturday', or exact YYYY-MM-DD.",
                            },
                            "time": {
                                "type": "string",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "description": "NEW reservation time in HH:MM format.",
                            },
                            "guests": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Total guests including the reserving person.",
                            },
                            "booking_reason": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Occasion or reason (e.g. 'Birthday', 'Family', 'Business').",
                            },
                            "special_notes": {
                                "type": "string",
                                "description": "Optional notes like seating preferences, allergies, etc.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_menu_pdf",
                    "description": "Send restaurant menu as a PDF via WhatsApp",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_menu_to_reservation",
                    "description": "Add pre-selected menu items to a confirmed reservation using its UID.",
                    "parameters": {
                        "type": "object",
                        "required": ["reservation_uid", "menu_items"],
                        "properties": {
                            "reservation_uid": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Unique ID from booking confirmation.",
                            },
                            "menu_items": {
                                "type": "array",
                                "minItems": 1,
                                "description": "List of selected menu items.",
                                "items": {
                                    "type": "object",
                                    "required": ["menu_name"],
                                    "properties": {
                                        "menu_name": {
                                            "type": "string",
                                            "minLength": 1,
                                            "description": "Exact name of the dish.",
                                        }
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
                    "description": "Cancel a reservation using reservation date (and optionally reservation time). Accept natural expressions like 'today', 'tomorrow', or 'next Saturday'.",
                    "parameters": {
                        "type": "object",
                        "required": ["reservation_date"],
                        "properties": {
                            "reservation_date": {
                                "type": "string",
                                "description": "Reservation date. Accepts natural phrases like 'today', 'tomorrow', 'next Saturday', or exact YYYY-MM-DD.",
                            },
                            "reservation_time": {
                                "type": "string",
                                "pattern": "^\\d{2}:\\d{2}$",
                                "description": "Time of reservation (only needed if multiple bookings on same date).",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
        ]
    else:
        tools = []  # Future expansion for other sales levels

    return tools
