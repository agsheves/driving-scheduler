import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, timedelta

# Course structure and rules
COURSE_STRUCTURE = {
    "orientation": {
        "type": "classroom",
        "duration": 1,  # hours
        "max_students": 30,
        "online": True,
    },
    "classroom_sessions": {
        "count": 15,
        "max_students": 30,
        "online": True,
        "duration": 1,  # hours per session
        "scheduling_rules": {
            "min_interval": 1,  # days between classes
            "max_per_week": 6,  # hours
            "max_per_day": 3,  # hours
        },
    },
    "driving_sessions": {
        "count": 10,
        "pairing": [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)],
        "duration": 2,  # hours per session
        "btw_per_student": 0.5,  # hours
        "observation_per_student": 0.5,  # hours
    },
    "final_test": {"type": "driving", "duration": 1, "max_students": 1},  # hours
}

# Concurrency rules - which classes must be completed before which drives
CONCURRENCY_RULES = {
    "drive_1_2": {
        "required_classes": [1, 2, 3],
        "additional_hours": 4,  # hours of classroom
    },
    "drive_3_4": {"required_classes": [4, 5, 6]},
    "drive_5_6": {"required_classes": [7, 8, 9]},
    "drive_7_8": {"required_classes": [10, 11, 12]},
    "drive_9_10": {"required_classes": [13, 14, 15]},
}

# Time limits and requirements
TIME_LIMITS = {
    "btw": {
        "weekly_max": 120,  # minutes
        "daily_max": 90,  # minutes
        "total_required": 360,  # minutes (6 hours)
    },
    "observation": {"total_required": 360},  # minutes (6 hours)
    "classroom": {
        "weekly_max": 360,  # minutes
        "daily_max": 180,  # minutes
    },
    "course": {"min_days": 35, "max_days": 180},
}

# Summer exception rules (June-August)
SUMMER_EXCEPTION = {
    "months": [6, 7, 8],  # June-August
    "min_weeks": 3,
    "weekly_max_hours": 10,
    "daily_max_hours": 3,
}


# Helper functions
@anvil.server.callable
def get_required_classes_for_drive(drive_number):
    """Get the required classes for a specific drive"""
    drive_key = f"drive_{drive_number}_{drive_number+1}"
    return CONCURRENCY_RULES.get(drive_key, {}).get("required_classes", [])


@anvil.server.callable
def is_summer_exception_applicable(date):
    """Check if summer exception rules apply to a date"""
    return date.month in SUMMER_EXCEPTION["months"]


@anvil.server.callable
def get_class_scheduling_rules(date):
    """Get the applicable scheduling rules for a date"""
    if is_summer_exception_applicable(date):
        return {
            "weekly_max": SUMMER_EXCEPTION["weekly_max_hours"],
            "daily_max": SUMMER_EXCEPTION["daily_max_hours"],
        }
    return COURSE_STRUCTURE["classroom_sessions"]["scheduling_rules"]


@anvil.server.callable
def get_drive_pair(drive_number):
    """Get the paired drive number for a given drive"""
    for pair in COURSE_STRUCTURE["driving_sessions"]["pairing"]:
        if drive_number in pair:
            return pair
    return None


@anvil.server.callable
def validate_class_schedule(class_numbers, dates):
    """
    Validate if a sequence of classes can be scheduled on the given dates
    Returns (is_valid, error_message)
    """
    # Check if all classes are within valid range
    if not all(1 <= num <= 15 for num in class_numbers):
        return False, "Invalid class numbers"

    # Check if dates are in order
    if dates != sorted(dates):
        return False, "Classes must be scheduled in order"

    # Check minimum interval between classes
    for i in range(len(dates) - 1):
        if (dates[i + 1] - dates[i]).days < COURSE_STRUCTURE["classroom_sessions"][
            "scheduling_rules"
        ]["min_interval"]:
            return (
                False,
                f"Classes {class_numbers[i]} and {class_numbers[i+1]} are too close together",
            )

    return True, None
