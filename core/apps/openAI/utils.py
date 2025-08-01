from typing import Dict

from datetime import datetime, date, time as time_obj, timedelta


from django.utils import timezone

import os
from openai import OpenAI

from apps.restaurant.models import RestaurantTable, Client, Reservation
from apps.restaurant.choices import TableStatus, ReservationStatus


client = OpenAI(api_key=os.environ.get("OPENAI_API"))


def check_table_availability(
    date: str, time: str, guests: int, organization: object
) -> Dict[str, any]:
    """
    Check table availability for given date, time, and guest count
    Returns available tables or suggestions for next available slots
    """
    # try:
    reservation_date = datetime.strptime(date, "%Y-%m-%d").date()
    reservation_time = datetime.strptime(time, "%H:%M").time()

    # Find tables that can accommodate the guests
    suitable_tables = RestaurantTable.objects.filter(
        organization=organization,
        capacity__gte=guests,
        status=TableStatus.AVAILABLE,
    )

    if not suitable_tables.exists():
        return {
            "available": False,
            "message": f"No tables available for {guests} guests",
            "suggestions": [],
        }

    # Check if any suitable table is free at the requested time
    available_tables = []
    for table in suitable_tables:
        # Check if table has conflicting reservations
        conflicting_reservations = Reservation.objects.filter(
            table=table,
            reservation_date=reservation_date,
            reservation_time__range=(
                (
                    datetime.combine(reservation_date, reservation_time)
                    - timedelta(hours=2)
                ).time(),
                (
                    datetime.combine(reservation_date, reservation_time)
                    + timedelta(hours=2)
                ).time(),
            ),
        ).exclude(reservation_status=ReservationStatus.COMPLETED)

        if not conflicting_reservations.exists():
            available_tables.append(
                {
                    "uid": table.uid,
                    "name": table.name,
                    "capacity": table.capacity,
                    "category": table.category,
                    "position": table.position,
                    "status": table.status,
                }
            )

    if available_tables:
        return {
            "available": True,
            "tables": available_tables,
            "message": f"Found {len(available_tables)} available table(s)",
        }

    # If no tables available at requested time, suggest alternatives
    suggestions = get_alternative_time_slots(reservation_date, guests, organization)

    return {
        "available": False,
        "message": f"No tables available at {time} on {date}",
        "suggestions": suggestions,
    }

    # except Exception as e:
    #     return {
    #         "available": False,
    #         "message": "Error checking availability",
    #         "suggestions": [],
    #     }


def get_alternative_time_slots(
    date: date, guests: int, organization: object, limit: int = 3
) -> list:
    """Get alternative available time slots for the same date"""
    # try:
    time_slots = [
        "11:00",
        "11:30",
        "12:00",
        "12:30",
        "13:00",
        "13:30",
        "14:00",
        "18:00",
        "18:30",
        "19:00",
        "19:30",
        "20:00",
        "20:30",
        "21:00",
    ]

    alternatives = []
    for time_str in time_slots:
        availability = check_table_availability(
            date.strftime("%Y-%m-%d"), time_str, guests, organization
        )
        if availability["available"] and len(alternatives) < limit:
            alternatives.append(
                {"time": time_str, "tables_count": len(availability["tables"])}
            )

    return alternatives
    # except Exception as e:
    #     return []
