import anvil.server
import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from .globals import current_teen_driving_schedule, COURSE_STRUCTURE

# Import from globals
# comment for github tracking
LESSON_SLOTS = current_teen_driving_schedule


class OptimalScheduler:
    def __init__(self, start_date=None, end_date=None, instructors=None):
        if start_date:
            self.start_date = start_date
        else:
            self.start_date = datetime.now()
        if end_date:
            self.end_date = end_date
        else:
            self.end_date = self.start_date + timedelta(days=45)
        if instructors:
            self.instructors = instructors
        else:
            self.instructors = app_tables.users.search(is_instructor=True)

        # Initialize instructor schedules first
        self.instructor_schedules = self._load_instructor_schedules()

        # Then initialize other attributes that depend on instructor schedules
        self.schedule = {}
        self.available_slots = self._initialize_available_slots()
        self.class_groups = []
        self.student_capacity = 0

    def _load_instructor_schedules(self):
        """Load instructor schedules from the database"""
        schedules = {}
        for instructor in self.instructors:
            try:
                schedule = app_tables.instructor_schedules.get(instructor=instructor)
                if schedule and schedule["weekly_availability"]:
                    schedules[instructor] = schedule["weekly_availability"]
            except Exception as e:
                print(f"Error loading schedule for {instructor['firstName']}: {e}")
        return schedules

    def _initialize_available_slots(self):
        """Initialize available time slots based on instructor availability"""
        slots = {}
        current_date = self.start_date

        while current_date <= self.end_date:
            day_slots = {}
            for slot_name, slot_info in LESSON_SLOTS.items():
                if self._is_slot_available(current_date, slot_name):
                    day_slots[slot_name] = {
                        "type": slot_info["type"],
                        "start_time": slot_info["start_time"],
                        "end_time": slot_info["end_time"],
                        "available_instructors": self._get_available_instructors(
                            current_date, slot_name
                        ),
                    }
            slots[current_date] = day_slots
            current_date += timedelta(days=1)
        return slots

    def _is_slot_available(self, date, slot_name):
        """Check if a slot is available on a given date"""
        day_name = date.strftime("%A").lower()

        for instructor, schedule in self.instructor_schedules.items():
            try:
                if not schedule:
                    continue
                day_schedule = schedule.get(day_name, {})
                if day_schedule.get(slot_name) == "Yes":
                    return True
            except Exception as e:
                print(
                    f"Error checking availability for {instructor['firstName']} on {day_name}: {e}"
                )

        return False

    def _get_available_instructors(self, date, slot_name):
        """Get list of instructors available for a slot"""
        day_name = date.strftime("%A").lower()
        available_instructors = []

        for instructor in self.instructors:
            try:
                schedule = self.instructor_schedules.get(instructor, {})
                if not schedule:
                    continue
                day_schedule = schedule.get(day_name, {})
                if day_schedule.get(slot_name) == "Yes":
                    available_instructors.append(instructor)
            except Exception as e:
                print(f"Error getting availability for {instructor['firstName']}: {e}")

        return available_instructors

    def create_optimal_schedule(self):
        """Create an optimal schedule that maximizes student capacity"""
        # Schedule orientation sessions
        self._schedule_orientations()

        # Schedule driving sessions
        self._schedule_driving_sessions()

        # Calculate total student capacity
        self._calculate_student_capacity()

        return {
            "schedule": self.schedule,
            "student_capacity": self.student_capacity,
            "class_groups": self.class_groups,
        }

    def _schedule_orientations(self):
        """Schedule orientation sessions"""
        current_date = self.start_date
        max_capacity = COURSE_STRUCTURE["orientation"]["max_students"]

        while current_date <= self.end_date:
            for slot_name, slot_info in self.available_slots[current_date].items():
                if (
                    slot_info["type"] == "class"
                    and len(slot_info["available_instructors"]) > 0
                ):
                    self.schedule[current_date] = self.schedule.get(current_date, {})
                    self.schedule[current_date][slot_name] = {
                        "type": "orientation",
                        "instructor": slot_info["available_instructors"][0],
                        "capacity": max_capacity,
                        "enrolled": 0,
                    }

                    self.class_groups.append(
                        {
                            "start_date": current_date,
                            "orientation_slot": slot_name,
                            "drive_sessions": [],
                            "student_capacity": max_capacity,
                        }
                    )

                    del self.available_slots[current_date][slot_name]
                    break

            current_date += timedelta(days=1)

    def _schedule_driving_sessions(self):
        """Schedule driving sessions - 5 pairs of 2-hour sessions with 2 students each"""
        for group in self.class_groups:
            current_date = group["start_date"] + timedelta(days=1)

            # Schedule each pair of drives
            for drive1, drive2 in COURSE_STRUCTURE["driving_sessions"]["pairs"]:
                # Schedule first drive
                drive1_scheduled = False
                while current_date <= self.end_date and not drive1_scheduled:
                    for slot_name, slot_info in self.available_slots[
                        current_date
                    ].items():
                        if (
                            slot_info["type"] == "drive"
                            and len(slot_info["available_instructors"]) > 0
                        ):
                            self.schedule[current_date] = self.schedule.get(
                                current_date, {}
                            )
                            self.schedule[current_date][slot_name] = {
                                "type": "drive",
                                "drive_number": drive1,
                                "instructor": slot_info["available_instructors"][0],
                                "capacity": 2,  # Two students per drive
                                "enrolled": 0,
                            }

                            group["drive_sessions"].append(
                                {
                                    "date": current_date,
                                    "slot": slot_name,
                                    "drive_number": drive1,
                                }
                            )

                            del self.available_slots[current_date][slot_name]
                            drive1_scheduled = True
                            break

                    current_date += timedelta(days=1)

                if not drive1_scheduled:
                    raise ValueError(
                        f"Could not schedule drive {drive1} for group starting {group['start_date']}"
                    )

                # Schedule second drive of the pair
                drive2_scheduled = False
                while current_date <= self.end_date and not drive2_scheduled:
                    for slot_name, slot_info in self.available_slots[
                        current_date
                    ].items():
                        if (
                            slot_info["type"] == "drive"
                            and len(slot_info["available_instructors"]) > 0
                        ):
                            self.schedule[current_date] = self.schedule.get(
                                current_date, {}
                            )
                            self.schedule[current_date][slot_name] = {
                                "type": "drive",
                                "drive_number": drive2,
                                "instructor": slot_info["available_instructors"][0],
                                "capacity": 2,  # Two students per drive
                                "enrolled": 0,
                            }

                            group["drive_sessions"].append(
                                {
                                    "date": current_date,
                                    "slot": slot_name,
                                    "drive_number": drive2,
                                }
                            )

                            del self.available_slots[current_date][slot_name]
                            drive2_scheduled = True
                            break

                    current_date += timedelta(days=1)

                if not drive2_scheduled:
                    raise ValueError(
                        f"Could not schedule drive {drive2} for group starting {group['start_date']}"
                    )

    def _calculate_student_capacity(self):
        """Calculate the total student capacity based on the schedule"""
        total_capacity = 0

        for group in self.class_groups:
            # Initial capacity is based on orientation session
            group_capacity = group["student_capacity"]

            # Each student needs 5 pairs of drives (10 total)
            # Each drive slot can accommodate 2 students
            available_drive_slots = len(group["drive_sessions"])
            max_drives_per_student = 10
            drive_based_capacity = (available_drive_slots * 2) // max_drives_per_student

            # The group's capacity is the minimum of orientation capacity and drive-based capacity
            group["student_capacity"] = min(group_capacity, drive_based_capacity)
            total_capacity += group["student_capacity"]

        self.student_capacity = total_capacity


@anvil.server.callable
def create_optimal_schedule(start_date=None, end_date=None, instructors=None):
    """Create an optimal schedule for the given date range"""
    scheduler = OptimalScheduler(start_date, end_date, instructors)
    return scheduler.create_optimal_schedule()
