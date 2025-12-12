def function_tools():
    """
    Returns function tools for restaurant customer support based on sales level.

    Args:
        sales_level (int): Level determining available functions

    Returns:
        list: List of function tool definitions
    """
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
                "name": "client_profile_update",
                "description": "Update customer profile information such as preferences, allergens, date of birth, or anniversary date. Use this when: (1) Customer mentions birthday/anniversary as booking occasion and confirms it's theirs - use booking date. (2) Customer explicitly states their birthday/anniversary date. (3) Customer mentions dietary preferences or food allergies. Collect all necessary info from customer before calling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preferences": {
                            "type": "string",
                            "description": "Customer's dining preferences (e.g., vegetarian, vegan, gluten-free, prefers window seating, likes spicy food). Multiple preferences can be comma-separated.",
                        },
                        "allergens": {
                            "type": "string",
                            "description": "Known food allergies or dietary restrictions (e.g., peanuts, shellfish, dairy, gluten). Multiple allergens can be comma-separated.",
                        },
                        "date_of_birth": {
                            "type": "string",
                            "description": "Customer's date of birth in YYYY-MM-DD format. Use this when customer confirms the booking is for their birthday, or when they explicitly mention their birthday date.",
                        },
                        "anniversary_date": {
                            "type": "string",
                            "description": "Customer's anniversary date in YYYY-MM-DD format. Use this when customer confirms the booking is for their anniversary, or when they explicitly mention their anniversary date.",
                        },
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
                "description": "Check table availability for a given date (and optional time).",
                "parameters": {
                    "type": "object",
                    "required": ["date", "guests"],
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Reservation date.",
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
                "description": "Create a new reservation. Ensure all info is collected. Phone number is only needed if WhatsApp is not used. Profile data (date_of_birth, anniversary_date, allergens, preferences) should be included when mentioned by customer.",
                "parameters": {
                    "type": "object",
                    "required": [
                        "reservation_name",
                        "date",
                        "time",
                        "guests",
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
                            "description": "Reservation date.",
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
                            "description": "Occasion or reason (e.g. 'Birthday', 'Anniversary', 'Family', 'Business').",
                        },
                        "reason_for_visit_date": {
                            "type": "string",
                            "description": "Date of the occasion or reason for the visit.",
                        },
                        "special_notes": {
                            "type": "string",
                            "description": "Optional notes like seating preferences, allergies, etc.",
                        },
                        "promo_code": {
                            "type": "string",
                            "description": "Optional promotional code for discounts or special offers.",
                        },
                        "preferences": {
                            "type": "string",
                            "description": "Customer's dining preferences (e.g., vegetarian, vegan, gluten-free, prefers window seating, likes spicy food). Multiple preferences can be comma-separated.",
                        },
                        "allergens": {
                            "type": "string",
                            "description": "Known food allergies or dietary restrictions (e.g., peanuts, shellfish, dairy, gluten). Multiple allergens can be comma-separated.",
                        },
                        "date_of_birth": {
                            "type": "string",
                            "description": "Customer's date of birth in YYYY-MM-DD format. Include ONLY when: (1) Customer says 'my birthday' as occasion - use booking date, OR (2) Customer confirms 'yes' when asked 'Is this for your birthday?' - use booking date, OR (3) Customer explicitly states their birthday date - use that date. DO NOT include if customer just says 'birthday' without clarification.",
                        },
                        "anniversary_date": {
                            "type": "string",
                            "description": "Customer's anniversary date in YYYY-MM-DD format. Include ONLY when: (1) Customer says 'my anniversary' as occasion - use booking date, OR (2) Customer confirms 'yes' when asked 'Is this for your anniversary?' - use booking date, OR (3) Customer explicitly states their anniversary date - use that date. DO NOT include if customer just says 'anniversary' without clarification.",
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
                            "description": "Original reservation date to identify the reservation to reschedule.",
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
                            "description": "NEW reservation date.",
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
                "description": "Cancel a reservation using reservation date (and optionally reservation time).",
                "parameters": {
                    "type": "object",
                    "required": ["reservation_date"],
                    "properties": {
                        "reservation_date": {
                            "type": "string",
                            "description": "Reservation date.",
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
        {
            "type": "function",
            "function": {
                "name": "get_customer_reservations",
                "description": "Retrieve all based on reservation date (and optionally reservation time).",
                "parameters": {
                    "type": "object",
                    "required": ["reservation_date", "reservation_status"],
                    "properties": {
                        "reservation_date": {
                            "type": "string",
                            "description": "Reservation date.",
                        },
                        "reservation_status": {
                            "type": "string",
                            "enum": [
                                "PLACED",
                                "INPROGRESS",
                                "COMPLETED",
                                "RESCHEDULED",
                                "CANCELLED",
                                "ABSENT",
                            ],
                            "description": "Filter by reservation status.",
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_priority_menu_items",
                "description": "Retrieve menu items that are marked as priority or recommended by the restaurant.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_personalized_recommendations",
                "description": "Get personalized dish recommendations based on customer's past orders and preferences.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_available_promotions",
                "description": "Fetch current promotions, discounts, or special offers available at the restaurant.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]

    return tools
