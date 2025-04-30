"""
Program Builder Consolidated Module

This module handles the calculation of program capacity based on available drive slots,
taking into account vacations and holidays.
"""

import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, timedelta, date

# Constants
STUDENTS_PER_SLOT = 2  # 2 students per drive slot
BUFFER_PERCENTAGE = 0.9  # 10% buffer for classes and slack

# Test data for no_class_days if table is empty
no_class_days_test = {
    "2025-01-01": "New Year's Day",
    "2025-05-01": "May Day Test",
    "2025-05-27": "Memorial Day",
    "2025-07-04": "Independence Day",
    "2025-09-02": "Labor Day",
    "2025-11-28": "Thanksgiving",
    "2025-12-25": "Christmas Day",
}


@anvil.server.callable
def get_available_days(start_date):
    """
    Get available days for the program, excluding holidays.
    Note: Instructor vacations are handled separately in get_daily_drive_slots.

    Args:
        start_date (date): Start date of the program

    Returns:
        list: List of available dates
    """
    available_days = []
    current_date = start_date

    # Get holidays from the database
    # Convert the test dictionary to the required format
    holidays = [
        {"date": datetime.strptime(date_str, "%Y-%m-%d").date(), "name": name}
        for date_str, name in no_class_days_test.items()
    ]

    # Now this will work correctly
    holiday_dates = {h["date"] for h in holidays}

    # Check 6 weeks of dates
    for _ in range(6 * 7):  # 6 weeks * 7 days
        # Skip if it's a holiday
        if current_date not in holiday_dates:
            available_days.append(current_date)
        current_date += timedelta(days=1)

    return available_days


def get_daily_drive_slots(day):
    """
    Calculate total available drive slots for a specific day across all instructors.

    Args:
        day (date): The day to check

    Returns:
        int: Total number of available drive slots for the day
    """
    total_slots = 0
    instructors = app_tables.users.search(is_instructor=True)

    for instructor in instructors:
        # Get instructor's schedule
        print(f"==Function log== Checking {instructor['firstName']}")
        instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_row:
            continue

        # Check vacations
        instructor_vacations = instructor_row["vacation_days"]
        if day in instructor_vacations:
            continue

        # Get availability for the specific day
        instructor_availability = instructor_row["weekly_availability"]
        day_availability = instructor_availability.get(str(day), {})
        if not day_availability:
            continue

        # Count available drive slots
        for slot, status in day_availability.items():
            if status == "Yes" or "Drive" in slot:
                total_slots += 1
        print(f"==Function log== {instructor['firstName']} has {total_slots} slots available")

    return total_slots


@anvil.server.callable
def calculate_weekly_capacity(start_date):
    """
    Calculate the weekly capacity based on available drive slots,
    taking into account instructor availability and vacations.

    Args:
        start_date (date): Start date of the program

    Returns:
        dict: Contains weekly capacity information
    """
    available_days = get_available_days(start_date)

    # Group days by week
    weekly_days = {}
    for day in available_days:
        week_num = (day - start_date).days // 7 + 1
        if week_num not in weekly_days:
            weekly_days[week_num] = []
        weekly_days[week_num].append(day)

    # Calculate drive slots per week
    # Internal storage with int keys and int values
    weekly_slots = {}
    
    for week_num in range(1, 7):
        total_slots = ...  # some calculation
        available_slots = int(total_slots * (BUFFER_PERCENTAGE))
        weekly_slots[week_num] = available_slots  # week_num = int, available_slots = int
    
    # Do math using int values
    max_weekly_slots = max(weekly_slots.values())
    avg_weekly_slots = sum(weekly_slots.values()) / len(weekly_slots)
    
    # Just before returning to Anvil
    weekly_slots_serialized = {str(k): v for k, v in weekly_slots.items()}
    
    return {
        "weekly_slots": weekly_slots_serialized,
        "max_weekly_slots": max_weekly_slots,
        "avg_weekly_slots": avg_weekly_slots
    }




@anvil.server.callable
def test_capacity_calculation(start_date=None):
    """
    Test function to verify the capacity calculation functions.
    Tests each function individually and shows their results.

    Args:
        start_date (date): Optional start date (defaults to next Monday)

    Returns:
        dict: Test results with function outputs
    """
    if start_date is None:
        today = datetime.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_monday)

    print("\n=== Testing Capacity Calculation Functions ===")
    print(f"Start Date: {start_date}")

    # Test get_available_days
    print("\n1. Testing get_available_days...")
    available_days = get_available_days(start_date)
    print(f"Found {len(available_days)} available days")
    print(f"First day: {available_days[0]}")
    print(f"Last day: {available_days[-1]}")

    # Test get_daily_drive_slots for first and last day
    print("\n2. Testing get_daily_drive_slots...")
    first_day_slots = get_daily_drive_slots(available_days[0])
    last_day_slots = get_daily_drive_slots(available_days[-1])
    print(f"First day slots: {first_day_slots}")
    print(f"Last day slots: {last_day_slots}")

    # Test calculate_weekly_capacity
    print("\n3. Testing calculate_weekly_capacity...")
    capacity = calculate_weekly_capacity(start_date)
    print(f"Weekly slots: {capacity['weekly_slots']}")
    print(f"Max weekly slots: {capacity['max_weekly_slots']}")
    print(f"Maximum students: {capacity['max_students']}")

    # Verify the calculations
    print("\n4. Verifying calculations...")
    max_slots = max(capacity["weekly_slots"].values())
    expected_students = max_slots * STUDENTS_PER_SLOT
    print(f"Expected students ({max_slots} * {STUDENTS_PER_SLOT}): {expected_students}")
    print(f"Calculated students: {capacity['max_students']}")

    return {
        "start_date": start_date,
        "available_days": available_days,
        "first_day_slots": first_day_slots,
        "last_day_slots": last_day_slots,
        "capacity": capacity,
    }
