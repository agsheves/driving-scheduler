import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# This contains the global variables for the app
# Changing these will change all referneces to time slots, lessons, etc.
#

# These are the time slots when a lesson could be booked. This is used to show availability
# and for schedule building. Start / end times will be converted to time objects for calendars, etc
availability_time_slots = {
    "time_slot_1": {
        "start_time": "08:00",
        "end_time": "10:00",
        "seasonal": "no",
        "term_days": ["Saturday", "Sunday"],
        "vacation": "all",
        "is_break": False
    },
    "time_slot_2": {
        "start_time": "10:15",
        "end_time": "12:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_3": {
        "start_time": "13:15",
        "end_time": "15:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_4": {
        "start_time": "15:45",
        "end_time": "17:45",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_5": {
        "start_time": "18:00",
        "end_time": "20:00",
        "seasonal": ["spring", "summer"],
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_6": {
        "start_time": "18:30",
        "end_time": "20:30",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": False
    },
    "time_slot_break_am": {
        "start_time": "10:00",
        "end_time": "10:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
    },
    "time_slot_break_lunch": {
        "start_time": "12:15",
        "end_time": "13:15",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
    },
    "time_slot_break_pm": {
        "start_time": "15:15",
        "end_time": "15:45",
        "seasonal": "no",
        "term_days": "all",
        "vacation": "all",
        "is_break": True
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

current_teen_driving_schedule = {
    "Drive 1": {
        "start_time": "08:00",
        "end_time": "10:00",
        "seasonal": "no",
        "term": "Sat, Sun",
        "vacation": "all",
    },
    "Drive 2": {
        "start_time": "10:15",
        "end_time": "12:15",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Drive 3": {
        "start_time": "13:15",
        "end_time": "15:15",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Drive 4": {
        "start_time": "15:45",
        "end_time": "17:45",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Drive 5": {
        "start_time": "18:00",
        "end_time": "20:00",
        "seasonal": "spring, summer",
        "term": "all",
        "vacation": "all",
    },
    "Class 1": {
        "start_time": "10:00",
        "end_time": "12:00",
        "seasonal": "no",
        "term": "Sat, Sun",
        "vacation": "all",
    },
    "Class 2": {
        "start_time": "16:00",
        "end_time": "18:00",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Class 3": {
        "start_time": "18:30",
        "end_time": "20:30",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Break - am": {
        "start_time": "10:00",
        "end_time": "10:15",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Break - Lunch": {
        "start_time": "12:15",
        "end_time": "13:15",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
    "Break - pm": {
        "start_time": "15:15",
        "end_time": "15:45",
        "seasonal": "no",
        "term": "all",
        "vacation": "all",
    },
}

old_teen_driving_schedule = ""

# Course structure defining lesson pairs and sequence
COURSE_STRUCTURE = {
    "orientation": {
        "max_students": 30,  # Maximum students per orientation session
        "duration": 2,  # Hours
        "type": "class",
    },
    "driving_sessions": {
        "pairs": [
            (1, 2),  # First pair of drives
            (3, 4),  # Second pair of drives
            (5, 6),  # Third pair of drives
            (7, 8),  # Fourth pair of drives
            (9, 10),  # Fifth pair of drives
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
    },
}
