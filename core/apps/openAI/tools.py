tools = [
    {
        "type": "function",
        "function": {
            "name": "check_customer_status",
            "description": "Check if the user is a new or returning customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "format": "international_phone_number"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_table",
            "description": "Create a reservation for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string", "format": "international_phone_number"},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "birthday": {"type": "string", "format": "date"},
                    "date": {"type": "string", "format": "date"},
                    "time": {"type": "string", "format": "time"},
                    "guests": {"type": "number"},
                },
                "required": ["name", "phone", "date", "time", "guests"],
            },
        },
    },
]
