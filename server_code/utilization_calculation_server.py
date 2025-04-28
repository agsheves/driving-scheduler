import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

# Get no_class_days from database or use test data
no_class_days_db = list(app_tables.no_class_dates.search())
print("No class days from DB:", no_class_days_db)
no_class_days = {}
if no_class_days_db:
    print("Processing DB no_class_days")
    for day in no_class_days_db:
        try:
            date_str = day["date"].strftime("%Y-%m-%d")
            no_class_days[date_str] = day["description"]
        except (KeyError, AttributeError) as e:
            print(f"Error processing no_class_day: {e}")
            continue
else:
    print("Using test no_class_days")
    no_class_days = no_class_days_test

print("No class days loaded:", no_class_days)


def is_holiday(date):
    """Check if a date is a company holiday"""
    date_str = date.strftime("%Y-%m-%d")
    return date_str in no_class_days


def is_vacation_day(date, vacation_days):
    """Check if a date falls within any vacation period"""
    if not vacation_days or "vacation_days" not in vacation_days:
        return False

    for vacation in vacation_days["vacation_days"]:
        try:
            start_date = datetime.strptime(vacation["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(vacation["end_date"], "%Y-%m-%d").date()
            if start_date <= date <= end_date:
                return True
        except (KeyError, ValueError) as e:
            print(f"Error processing vacation date: {e}")
            continue
    return False


@anvil.server.callable
def calculate_instructor_availability_hours(
    instructors, start_date=None, end_date=None
):
    """
    Calculate availability metrics for multiple instructors over a date range.

    Args:
        instructors (list): List of instructor objects
        start_date (date): Start date for calculation (default: today)
        end_date (date): End date for calculation (default: 30 days from start)

    Returns:
        dict: Dictionary containing availability metrics for each instructor
    """
    if start_date is None:
        start_date = datetime.now().date()
    if end_date is None:
        end_date = start_date + timedelta(days=30)

    results = {}

    for instructor in instructors:
        try:
            print(f"\nProcessing instructor: {instructor['firstName']}")

            # Get instructor's schedule data
            instructor_schedule = app_tables.instructor_schedules.get(
                instructor=instructor
            )
            if not instructor_schedule:
                print(f"No schedule found for {instructor['firstName']}")
                continue

            weekly_data = instructor_schedule["weekly_availability"]
            vacation_data = instructor_schedule["vacation_days"]

            print(f"Weekly data type: {type(weekly_data)}")
            print(f"Vacation data: {vacation_data}")

            if not weekly_data:
                print(f"No weekly data for {instructor['firstName']}")
                continue

            # Initialize counters
            total_available = 0
            driving_slots = 0
            class_slots = 0

            # Process each day in the date range
            current_date = start_date
            while current_date <= end_date:
                # Skip if it's a company holiday
                if is_holiday(current_date):
                    print(f"Skipping holiday: {current_date}")
                    current_date += timedelta(days=1)
                    continue

                # Skip if it's a vacation day
                if is_vacation_day(current_date, vacation_data):
                    print(f"Skipping vacation day: {current_date}")
                    current_date += timedelta(days=1)
                    continue

                # Get day of week (lowercase for matching with availability data)
                day_of_week = current_date.strftime("%A").lower()

                # Process slots for this day
                if day_of_week in weekly_data.get("weekly_availability", {}):
                    for slot_name, status in weekly_data["weekly_availability"][
                        day_of_week
                    ].items():
                        if status == "Yes":
                            total_available += 1
                            if "Drive" in slot_name:
                                driving_slots += 1
                            elif "Class" in slot_name:
                                class_slots += 1

                current_date += timedelta(days=1)

            results[instructor["firstName"]] = {
                "total_available_slots": total_available,
                "driving_slots_available": driving_slots,
                "class_slots_available": class_slots,
            }

            print(
                f"Results for {instructor['firstName']}: {results[instructor['firstName']]}"
            )

        except Exception as e:
            print(f"Error processing {instructor['firstName']}: {str(e)}")
            results[instructor["firstName"]] = {
                "error": str(e),
                "total_available_slots": 0,
                "driving_slots_available": 0,
                "class_slots_available": 0,
            }

    return results


@anvil.server.callable
def test_availability_calculation():
    """
    Test function to verify availability calculation with existing data.
    Returns a dictionary with test results and debug information.
    """
    try:
        # Get all instructors
        instructors = app_tables.users.search(is_instructor=True)
        print(f"Found {len(instructors)} instructors")

        # Set test date range (next 30 days)
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)

        print(f"Testing date range: {start_date} to {end_date}")

        # Calculate availability
        results = calculate_instructor_availability_hours(
            instructors, start_date, end_date
        )

        # Prepare debug information
        debug_info = {
            "test_date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_days": (end_date - start_date).days + 1,
            },
            "no_class_days_in_range": [
                {"date": date, "description": desc}
                for date, desc in no_class_days.items()
                if start_date <= datetime.strptime(date, "%Y-%m-%d").date() <= end_date
            ],
            "results": results,
        }

        return debug_info

    except Exception as e:
        return {"error": str(e), "traceback": str(e.__traceback__)}
