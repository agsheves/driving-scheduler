import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# GLOBALs imports date from the GLOBALS table but also maintains fall-back values here
# GLOBALS maitnains a current data set and previous sets as archives

def get_globals():
    latest_globals = app_tables.global_variables_edit_with_care.get(version='latest')
    if latest_globals:
        globals = {
            'days_full': latest_globals['days_full'] or days_full_fallback,
            'LESSON_SLOTS': latest_globals['lesson_slots'] or LESSON_SLOTS,
            'days_short': latest_globals['days_short'] or days_short_fallback,
            'availability_codes': latest_globals['availability_codes'] or availability_codes_fallback,
            'AVAILABILITY_MAPPING': latest_globals['availability_mapping'] or AVAILABILITY_MAPPING_FALLBACK,
            'COURSE_STRUCTURE_COMPRESSED': latest_globals['course_structure_compressed'] or COURSE_STRUCTURE_COMPRESSED_FALLBACK,
            'COURSE_STRUCTURE_STANDARD': latest_globals['course_structure_standard'] or COURSE_STRUCTURE_STANDARD_FALLBACK,
        }
        return latest_globals
    else:
        # Use local fallbacks
        globals = {
            'days_full': days_full_fallback,
            'days_short': days_short_fallback,
            'availability_codes': availability_codes_fallback,
            'AVAILABILITY_MAPPING': AVAILABILITY_MAPPING_FALLBACK,
            'COURSE_STRUCTURE_COMPRESSED': COURSE_STRUCTURE_COMPRESSED_FALLBACK,
            'COURSE_STRUCTURE_STANDARD': COURSE_STRUCTURE_STANDARD_FALLBACK,
        }

# time_slot_5 is extended as the evening drive and class start times differ
LESSON_SLOTS = app_tables.global_variables_edit_with_care.get(version='latest')['lesson_slots']

days_full_fallback = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
days_short_fallback = ["mon", "tues", "wed", "thurs", "fri", "sat", "sun"]
availability_codes_fallback = ["Unavailable", "Yes - Drive", "Yes - Class", "Yes - Any"]

AVAILABILITY_MAPPING_FALLBACK = {
  "No": 0,  # Not available
  "Yes": 1,  # Available for both
  "Drive Only": 2,  # Available for drives only
  "Class Only": 3,  # Available for classes only
  "Scheduled": 4,  # Allocated to classroom slot (could be booked)
  "Booked": 5,  # Scheduled slot has student booking
  "Vacation": 6,  # Personal vacation day
}

# Course structure defining lesson pairs and sequence
COURSE_STRUCTURE_COMPRESSED_FALLBACK = {
    "orientation": {
        "max_students": 30,  # Maximum students per orientation session
        "duration": 2,  # Hours
        "type": "class",
    },
    "driving_sessions": {
        "pairs": [ # rename to drive_lesson_pairs to differntiate from student pairs
            (1, 2),  # First pair of drives
            (3, 4),  # Second pair of drives
            (5, 6),  # Third pair of drives
            (7, 8),  # Fourth pair of drives
            (9, 10),  # Fifth pair of drives
            (11), # Final drive
        ],
        "students_per_drive": 2,  # Number of students per drive session
        "duration": 2,  # Hours per drive session
        "min_days_between_pairs": 1,  # Minimum days between drive pairs
        "max_days_between_pairs": 7,  # Maximum days between drive pairs
        "type": "drive",
    },
    "class_sessions": {
        "total_sessions": 15,  # Total number of class sessions
        "max_students": 30,  # Maximum students per class
        "duration": 2,  # Hours per class
        "classes_per_week": 3,  # Number of classes per week
        "class_days": ["Monday", "Wednesday", "Friday"],
        "type": "class",
    },
    "sequence": {
        "orientation_first": True,  # Orientation must be first
        "class_drive_order": [
            "class",
            "drive",
        ],  # Preferred order of class vs drive sessions
        "min_days_between_classes": 1,  # Minimum days between class sessions
        "max_days_between_classes": 7,  # Maximum days between class sessions
        "MIN_COURSE_LENGTH": 49,  # Minimum days classroom must run 7 weeks * 7 days
    },
}

COURSE_STRUCTURE_STANDARD_FALLBACK = {
    "orientation": {
        "max_students": 30,  # Maximum students per orientation session
        "duration": 2,  # Hours
        "type": "class",
    },
    "driving_sessions": {
        "pairs": [ # rename to drive_lesson_pairs to differntiate from student pairs
            (1, 2),  # First pair of drives
            (3, 4),  # Second pair of drives
            (5, 6),  # Third pair of drives
            (7, 8),  # Fourth pair of drives
            (9, 10),  # Fifth pair of drives
            (11), # Final drive
        ],
        "students_per_drive": 2,  # Number of students per drive session
        "duration": 2,  # Hours per drive session
        "min_days_between_pairs": 1,  # Minimum days between drive pairs
        "max_days_between_pairs": 7,  # Maximum days between drive pairs
        "type": "drive",
    },
    "class_sessions": {
        "total_sessions": 15,  # Total number of class sessions
        "max_students": 30,  # Maximum students per class
        "duration": 2,  # Hours per class
        "classes_per_week": 2,  # Number of classes per week
        "class_days": ["Tuesday", "Thursday"],
        "type": "class",

    },
    "sequence": {
        "orientation_first": True,  # Orientation must be first
        "class_drive_order": [
            "class",
            "drive",
        ],  # Preferred order of class vs drive sessions
        "min_days_between_classes": 1,  # Minimum days between class sessions
        "max_days_between_classes": 7,  # Maximum days between class sessions
        "MIN_COURSE_LENGTH": 56,  # Minimum days classroom must run 8 weeks * 7 days
    },
}