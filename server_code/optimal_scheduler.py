import anvil.server
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .course_rules_server import COURSE_STRUCTURE, CONCURRENCY_RULES, TIME_LIMITS
from .instructor_availability_server import LESSON_SLOTS


class OptimalScheduler:
    def __init__(self, start_date, end_date, instructors):
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
        self.schedule = {}
        self.available_slots = self._initialize_available_slots()
        self.class_groups = []  # Track groups of students taking classes together
        self.instructor_schedules = self._load_instructor_schedules()
        self.student_capacity = 0  # Track total student capacity

    def _load_instructor_schedules(self):
        """Load instructor schedules from the database"""
        schedules = {}
        for instructor in self.instructors:
            try:
                schedule = app_tables.instructor_schedules.get(instructor=instructor)
                if schedule and schedule["weekly_availability"]:
                    schedules[instructor["firstName"]] = schedule["weekly_availability"]
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
                # Check if any instructor is available for this slot
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

        # Check if any instructor is available for this slot
        for instructor_name, schedule in self.instructor_schedules.items():
            try:
                day_schedule = schedule.get(day_name, {})
                if day_schedule.get(slot_name) == "Yes":
                    return True
            except Exception as e:
                print(
                    f"Error checking availability for {instructor_name} on {day_name}: {e}"
                )

        return False

    def _get_available_instructors(self, date, slot_name):
        """Get list of instructors available for a slot"""
        day_name = date.strftime("%A").lower()
        available_instructors = []

        for instructor in self.instructors:
            try:
                schedule = self.instructor_schedules.get(instructor["firstName"], {})
                day_schedule = schedule.get(day_name, {})
                if day_schedule.get(slot_name) == "Yes":
                    available_instructors.append(instructor)
            except Exception as e:
                print(f"Error getting availability for {instructor['firstName']}: {e}")

        return available_instructors

    def create_optimal_schedule(self):
        """Create an optimal schedule that maximizes student capacity"""
        # 1. Schedule orientation sessions first (max capacity)
        self._schedule_orientations()

        # 2. Schedule classroom sessions
        self._schedule_classroom_sessions()

        # 3. Schedule driving sessions
        self._schedule_driving_sessions()

        # Calculate total student capacity
        self._calculate_student_capacity()

        return {
            "schedule": self.schedule,
            "student_capacity": self.student_capacity,
            "class_groups": self.class_groups,
        }

    def _schedule_orientations(self):
        """Schedule orientation sessions to maximize capacity"""
        current_date = self.start_date
        max_capacity = COURSE_STRUCTURE["orientation"]["max_students"]

        while current_date <= self.end_date:
            # Find available class slots for orientation
            for slot_name, slot_info in self.available_slots[current_date].items():
                if (
                    slot_info["type"] == "class"
                    and len(slot_info["available_instructors"]) > 0
                ):
                    # Schedule orientation session
                    self.schedule[current_date] = self.schedule.get(current_date, {})
                    self.schedule[current_date][slot_name] = {
                        "type": "orientation",
                        "instructor": slot_info["available_instructors"][0],
                        "capacity": max_capacity,
                        "enrolled": 0,
                    }

                    # Create a new student group
                    self.class_groups.append(
                        {
                            "start_date": current_date,
                            "orientation_slot": slot_name,
                            "class_sessions": [],
                            "drive_sessions": [],
                            "student_capacity": max_capacity,  # Initial capacity based on orientation
                        }
                    )

                    # Remove this slot from available slots
                    del self.available_slots[current_date][slot_name]
                    break

            current_date += timedelta(days=1)

    def _schedule_classroom_sessions(self):
        """Schedule classroom sessions following course rules"""
        for group in self.class_groups:
            current_date = group["start_date"] + timedelta(
                days=1
            )  # Start after orientation
            class_number = 1

            while class_number <= COURSE_STRUCTURE["classroom_sessions"]["count"]:
                # Find next available class slot
                slot_found = False
                while current_date <= self.end_date and not slot_found:
                    for slot_name, slot_info in self.available_slots[
                        current_date
                    ].items():
                        if (
                            slot_info["type"] == "class"
                            and len(slot_info["available_instructors"]) > 0
                            and self._is_valid_class_date(current_date, class_number)
                        ):

                            # Schedule class session
                            self.schedule[current_date] = self.schedule.get(
                                current_date, {}
                            )
                            self.schedule[current_date][slot_name] = {
                                "type": "class",
                                "class_number": class_number,
                                "instructor": slot_info["available_instructors"][0],
                                "capacity": COURSE_STRUCTURE["classroom_sessions"][
                                    "max_students"
                                ],
                                "enrolled": 0,
                            }

                            # Add to group's class sessions
                            group["class_sessions"].append(
                                {
                                    "date": current_date,
                                    "slot": slot_name,
                                    "class_number": class_number,
                                }
                            )

                            # Remove slot from available slots
                            del self.available_slots[current_date][slot_name]
                            slot_found = True
                            break

                    current_date += timedelta(days=1)

                if not slot_found:
                    raise ValueError(
                        f"Could not schedule class {class_number} for group starting {group['start_date']}"
                    )

                class_number += 1

    def _is_valid_class_date(self, date, class_number):
        """Check if a date is valid for scheduling a class based on rules"""
        # Check minimum interval between classes
        if class_number > 1:
            prev_class = next(
                (
                    c
                    for c in self.class_groups[0]["class_sessions"]
                    if c["class_number"] == class_number - 1
                ),
                None,
            )
            if prev_class:
                min_interval = COURSE_STRUCTURE["classroom_sessions"][
                    "scheduling_rules"
                ]["min_interval"]
                if (date - prev_class["date"]).days < min_interval:
                    return False

        # Check weekly and daily limits
        weekly_hours = self._get_weekly_hours(date)
        daily_hours = self._get_daily_hours(date)

        max_weekly = COURSE_STRUCTURE["classroom_sessions"]["scheduling_rules"][
            "max_per_week"
        ]
        max_daily = COURSE_STRUCTURE["classroom_sessions"]["scheduling_rules"][
            "max_per_day"
        ]

        return weekly_hours < max_weekly and daily_hours < max_daily

    def _get_weekly_hours(self, date):
        """Calculate total class hours for the week containing the date"""
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        total_hours = 0

        current_date = week_start
        while current_date <= week_end:
            if current_date in self.schedule:
                for slot in self.schedule[current_date].values():
                    if slot["type"] == "class":
                        total_hours += 1
            current_date += timedelta(days=1)

        return total_hours

    def _get_daily_hours(self, date):
        """Calculate total class hours for the given date"""
        if date not in self.schedule:
            return 0

        return sum(
            1 for slot in self.schedule[date].values() if slot["type"] == "class"
        )

    def _schedule_driving_sessions(self):
        """Schedule driving sessions following concurrency rules"""
        for group in self.class_groups:
            # Get the group's class completion dates
            class_completion_dates = {}
            for session in group["class_sessions"]:
                class_completion_dates[session["class_number"]] = session["date"]

            # Schedule each pair of drives
            for drive_pair in COURSE_STRUCTURE["driving_sessions"]["pairing"]:
                drive1, drive2 = drive_pair

                # Get required classes for this drive pair
                required_classes = CONCURRENCY_RULES[f"drive_{drive1}_{drive2}"][
                    "required_classes"
                ]

                # Find the latest completion date of required classes
                latest_class_date = max(
                    class_completion_dates[class_num] for class_num in required_classes
                )

                # Start scheduling drives after the latest required class
                current_date = latest_class_date + timedelta(days=1)

                # Schedule first drive of the pair
                drive1_scheduled = False
                while current_date <= self.end_date and not drive1_scheduled:
                    for slot_name, slot_info in self.available_slots[
                        current_date
                    ].items():
                        if (
                            slot_info["type"] == "drive"
                            and len(slot_info["available_instructors"]) > 0
                            and self._is_valid_drive_date(current_date, drive1)
                        ):

                            # Schedule drive session
                            self.schedule[current_date] = self.schedule.get(
                                current_date, {}
                            )
                            self.schedule[current_date][slot_name] = {
                                "type": "drive",
                                "drive_number": drive1,
                                "instructor": slot_info["available_instructors"][0],
                                "capacity": 2,  # Two students per drive (one driving, one observing)
                                "enrolled": 0,
                            }

                            # Add to group's drive sessions
                            group["drive_sessions"].append(
                                {
                                    "date": current_date,
                                    "slot": slot_name,
                                    "drive_number": drive1,
                                }
                            )

                            # Remove slot from available slots
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
                            and self._is_valid_drive_date(current_date, drive2)
                        ):

                            # Schedule drive session
                            self.schedule[current_date] = self.schedule.get(
                                current_date, {}
                            )
                            self.schedule[current_date][slot_name] = {
                                "type": "drive",
                                "drive_number": drive2,
                                "instructor": slot_info["available_instructors"][0],
                                "capacity": 2,  # Two students per drive (one driving, one observing)
                                "enrolled": 0,
                            }

                            # Add to group's drive sessions
                            group["drive_sessions"].append(
                                {
                                    "date": current_date,
                                    "slot": slot_name,
                                    "drive_number": drive2,
                                }
                            )

                            # Remove slot from available slots
                            del self.available_slots[current_date][slot_name]
                            drive2_scheduled = True
                            break

                    current_date += timedelta(days=1)

                if not drive2_scheduled:
                    raise ValueError(
                        f"Could not schedule drive {drive2} for group starting {group['start_date']}"
                    )

    def _is_valid_drive_date(self, date, drive_number):
        """Check if a date is valid for scheduling a drive based on rules"""
        # Check if this would exceed daily drive hours
        daily_drive_hours = self._get_daily_drive_hours(date)
        if (
            daily_drive_hours >= TIME_LIMITS["btw"]["daily_max"] / 60
        ):  # Convert minutes to hours
            return False

        # Check if this would exceed weekly drive hours
        weekly_drive_hours = self._get_weekly_drive_hours(date)
        if (
            weekly_drive_hours >= TIME_LIMITS["btw"]["weekly_max"] / 60
        ):  # Convert minutes to hours
            return False

        return True

    def _get_daily_drive_hours(self, date):
        """Calculate total drive hours for the given date"""
        if date not in self.schedule:
            return 0

        return sum(
            2 for slot in self.schedule[date].values() if slot["type"] == "drive"
        )  # Each drive is 2 hours

    def _get_weekly_drive_hours(self, date):
        """Calculate total drive hours for the week containing the date"""
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        total_hours = 0

        current_date = week_start
        while current_date <= week_end:
            if current_date in self.schedule:
                for slot in self.schedule[current_date].values():
                    if slot["type"] == "drive":
                        total_hours += 2  # Each drive is 2 hours
            current_date += timedelta(days=1)

        return total_hours

    def _calculate_student_capacity(self):
        """Calculate the total student capacity based on the schedule"""
        total_capacity = 0

        for group in self.class_groups:
            # Initial capacity is based on orientation session
            group_capacity = group["student_capacity"]

            # Adjust capacity based on available drive slots
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
def create_optimal_schedule(start_date, end_date):
    """Create an optimal schedule for the given date range"""
    instructors = app_tables.users.search(is_instructor=True)
    scheduler = OptimalScheduler(start_date, end_date, instructors)
    return scheduler.create_optimal_schedule()
