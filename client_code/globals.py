import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# time_slot_5 is extended as the evening drive and class start times differ
LESSON_SLOTS = {
  "break_am": {
    "term": "all",
    "end_time": "10:15",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "10:00"
  },
  "break_pm": {
    "term": "all",
    "end_time": "15:45",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "15:30"
  },
  "break_lunch": {
    "term": "all",
    "end_time": "13:30",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "12:30"
  },
  "lesson_slot_1": {
    "term": "Sat, Sun",
    "end_time": "10:00",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "08:00"
  },
  "lesson_slot_2": {
    "term": "Sat, Sun",
    "end_time": "12:15",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "10:15"
  },
  "lesson_slot_3": {
    "term": "Sat, Sun",
    "end_time": "15:15",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "13:15"
  },
  "lesson_slot_4": {
    "term": "all",
    "end_time": "17:45",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "15:45"
  },
  "lesson_slot_5": {
    "term": "all",
    "end_time": "20:30",
    "seasonal": "no",
    "vacation": "all",
    "start_time": "18:00"
  }
}

days_full = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
days_short = ["mon", "tues", "wed", "thurs", "fri", "sat", "sun"]
availability_codes = ["Unavailable", "Yes - Drive", "Yes - Class", "Yes - Any"]

AVAILABILITY_MAPPING = {
  "No": 0,  # Not available
  "Yes": 1,  # Available for both
  "Drive Only": 2,  # Available for drives only
  "Class Only": 3,  # Available for classes only
  "Scheduled": 4,  # Allocated to classroom slot (could be booked)
  "Booked": 5,  # Scheduled slot has student booking
  "Vacation": 6,  # Personal vacation day
}

# Course structure defining lesson pairs and sequence
COURSE_STRUCTURE_COMPRESSED = {
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

COURSE_STRUCTURE_STANDARD = {
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