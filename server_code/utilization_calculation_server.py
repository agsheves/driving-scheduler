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

# Company holidays for testing - format: "YYYY-MM-DD"
COMPANY_HOLIDAYS = {
    "2024-01-01": "New Year's Day",
    "2024-05-01": "May Day Test",
    "2024-05-27": "Memorial Day",
    "2024-07-04": "Independence Day",
    "2024-09-02": "Labor Day",
    "2024-11-28": "Thanksgiving",
    "2024-12-25": "Christmas Day",
}


def is_holiday(date):
    """Check if a date is a company holiday"""
    date_str = date.strftime("%Y-%m-%d")
    return date_str in COMPANY_HOLIDAYS


def is_vacation_day(date, vacation_days):
    """Check if a date falls within any vacation period"""
    if not vacation_days:
        return False

    for vacation in vacation_days:
        start_date = datetime.strptime(vacation["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(vacation["end_date"], "%Y-%m-%d").date()
        if start_date <= date <= end_date:
            return True
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
            # Get instructor's schedule data
            instructor_schedule = app_tables.instructor_schedules.get(
                instructor=instructor
            )
            weekly_data = instructor_schedule["weekly_availability"]
            vacation_data = instructor_schedule["vacation_days"]

            if not weekly_data:
                continue

            # Initialize counters
            total_available = 0
            driving_hours = 0
            class_hours = 0
            booked_hours = 0

            # Process each day in the date range
            current_date = start_date
            while current_date <= end_date:
                # Skip if it's a company holiday
                if is_holiday(current_date):
                    current_date += timedelta(days=1)
                    continue

                # Skip if it's a vacation day
                if is_vacation_day(current_date, vacation_data):
                    current_date += timedelta(days=1)
                    continue

                # Get day of week (lowercase for matching with availability data)
                day_of_week = current_date.strftime("%A").lower()

                # Process hours for this day
                if day_of_week in weekly_data.get("weekly_availability", {}):
                    for hour, status in weekly_data["weekly_availability"][
                        day_of_week
                    ].items():
                        if status == "Yes - Any":
                            total_available += 1
                        elif status == "Yes - Drive":
                            total_available += 1
                            driving_hours += 1
                        elif status == "Yes - Class":
                            total_available += 1
                            class_hours += 1
                        elif status == "Booked":
                            booked_hours += 1

                current_date += timedelta(days=1)

            results[instructor["firstName"]] = {
                "total_available_hours": total_available,
                "driving_hours_available": driving_hours,
                "class_hours_available": class_hours,
                "booked_hours": booked_hours,
            }

        except Exception as e:
            print(f"Error processing instructor {instructor['firstName']}: {e}")
            continue

    return results


@anvil.server.callable
def test_availability_calculation():
    """
    Test function to verify availability calculation with existing data.
    Returns a dictionary with test results and debug information.
    """
    try:
        # Get all instructors
        instructors = app_tables.instructors.search()

        # Set test date range (next 30 days)
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)

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
            "company_holidays_in_range": [
                holiday
                for date, holiday in COMPANY_HOLIDAYS.items()
                if start_date <= datetime.strptime(date, "%Y-%m-%d").date() <= end_date
            ],
            "results": results,
        }

        return debug_info

    except Exception as e:
        return {"error": str(e), "traceback": str(e.__traceback__)}
