import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# This contains the global variables for the app
# Changing these will change all referneces to time slots, lessons, etc.
# 

availability_time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
days_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
days_short = ["mon", "tues", "wed", "thurs", "fri", "sat", "sun"]
availability_codes = ["Unavailable", "Yes - Drive", "Yes - Class", "Yes - Any"]

teen_driving_schedule = {
    "lesson_schedule": [
        {
            "title": "Drive 1",
            "start_time": "08:00",
            "end_time": "10:00",
            "seasonal": "no",
            "days_term": "Sat, Sun",
            "days_vacation": "all"
        },
        {
            "title": "Drive 2",
            "start_time": "10:15",
            "end_time": "12:15",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Drive 3",
            "start_time": "13:15",
            "end_time": "15:15",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Drive 4",
            "start_time": "15:45",
            "end_time": "17:45",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Drive 5",
            "start_time": "18:00",
            "end_time": "20:00",
            "seasonal": "spring, summer",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Class 1",
            "start_time": "10:00",
            "end_time": "12:00",
            "seasonal": "no",
            "days_term": "Sat, Sun",
            "days_vacation": "all"
        },
        {
            "title": "Class 2",
            "start_time": "16:00",
            "end_time": "18:00",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Class 3",
            "start_time": "18:30",
            "end_time": "20:30",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Break - am",
            "start_time": "10:00",
            "end_time": "10:15",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Break - Lunch",
            "start_time": "12:15",
            "end_time": "13:15",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        },
        {
            "title": "Break - pm",
            "start_time": "15:15",
            "end_time": "15:45",
            "seasonal": "no",
            "days_term": "all",
            "days_vacation": "all"
        }
    ]
}