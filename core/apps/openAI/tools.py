tools = [
    {
        "type": "function",
        "function": {
            "name": "check_customer_status",
            "description": "Check if the customer is new or returning based on their whatsapp number",
            "parameters": {
                "type": "object",
                "properties": {
                    "whatsapp number": {"type": "string"},
                },
                "required": ["whatsapp number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_table",
            "description": "Create a table reservation for the customer. Only call this after collecting all required information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer's full name"},
                    "whatsapp_number": {
                        "type": "string",
                        "description": "Customer's whatsapp number",
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Reservation date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "format": "time",
                        "description": "Reservation time in HH:MM format (24-hour)",
                    },
                    "guests": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of guests",
                    },
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Dietary preferences or special requests",
                    },
                    "birthday": {
                        "type": "string",
                        "format": "date",
                        "description": "Customer's birthday in YYYY-MM-DD format",
                    },
                },
                "required": ["name", "whatsapp_number", "date", "time", "guests"],
            },
        },
    },
]
