from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server


class AvailabilityType(Enum):
    YES = "Yes"
    NO = "No"
    DRIVE_ONLY = "Drive Only"
    CLASS_ONLY = "Class Only"


class SchoolPreference(Enum):
    PREFERRED = "Preferred"
    POSSIBLE = "Possible"
    NO = "No"


@dataclass
class School:
    id: str
    name: str
    total_slots: int = 0
    preferred_slots: int = 0
    possible_slots: int = 0


@dataclass
class Instructor:
    id: str
    name: str
    availability: Dict[
        datetime, Dict[str, AvailabilityType]
    ]  # date -> time_slot -> availability
    school_preferences: Dict[str, SchoolPreference]  # school_id -> preference
    max_daily_sessions: int = 4
    min_weekly_sessions: int = 10
    max_weekly_sessions: int = 20


@dataclass
class TimeSlot:
    start_time: datetime
    end_time: datetime
    type: str  # "Class" or "Drive"


class SchedulerOptimizer:
    def __init__(self):
        self.instructors: List[Instructor] = []
        self.time_slots: List[TimeSlot] = []
        self.schools: Dict[str, School] = {}
        self.assignments = {}  # Will store the assignments

    def add_instructor(self, instructor: Instructor):
        """Add an instructor to the optimization problem."""
        self.instructors.append(instructor)

    def add_time_slot(self, time_slot: TimeSlot):
        """Add a time slot to the optimization problem."""
        self.time_slots.append(time_slot)

    def optimize(self) -> Dict:
        """
        Optimize the schedule using rule-based approach.
        Returns the optimized schedule.
        """
        try:
            # Initialize assignments
            self.assignments = {}

            # Sort time slots by start time
            sorted_slots = sorted(self.time_slots, key=lambda x: x.start_time)

            # Process each time slot
            for slot in sorted_slots:
                # Get available instructors for this slot
                available_instructors = [
                    instr
                    for instr in self.instructors
                    if self._is_instructor_available(instr, slot)
                ]

                if not available_instructors:
                    continue

                # Sort instructors by their current load (least loaded first)
                available_instructors.sort(
                    key=lambda x: len(
                        [
                            a
                            for a in self.assignments.values()
                            if a["instructor_id"] == x.id
                        ]
                    )
                )

                # Get the least loaded instructor
                instructor = available_instructors[0]

                # Check if instructor has reached daily limit
                if self._has_reached_daily_limit(instructor, slot.start_time):
                    continue

                # Assign the slot
                self.assignments[slot.start_time.isoformat()] = {
                    "instructor_id": instructor.id,
                    "instructor_name": instructor.name,
                    "slot_type": slot.type,
                    "start_time": slot.start_time,
                    "end_time": slot.end_time,
                }

            return self._format_schedule()

        except Exception as e:
            anvil.server.error(f"Error in optimize: {str(e)}")
            raise

    def _is_instructor_available(self, instructor: Instructor, slot: TimeSlot) -> bool:
        """Check if an instructor is available for a given time slot."""
        try:
            date = slot.start_time.date()
            time_key = slot.start_time.strftime("%H:%M")

            if date not in instructor.availability:
                return False

            availability = instructor.availability[date].get(
                time_key, AvailabilityType.NO
            )

            if availability == AvailabilityType.NO:
                return False
            if availability == AvailabilityType.DRIVE_ONLY and slot.type != "Drive":
                return False
            if availability == AvailabilityType.CLASS_ONLY and slot.type != "Class":
                return False

            return True

        except Exception as e:
            anvil.server.error(f"Error checking availability: {str(e)}")
            return False

    def _has_reached_daily_limit(self, instructor: Instructor, date: datetime) -> bool:
        """Check if an instructor has reached their daily session limit."""
        try:
            # Count assignments for this instructor on this date
            daily_assignments = len(
                [
                    a
                    for a in self.assignments.values()
                    if a["instructor_id"] == instructor.id
                    and a["start_time"].date() == date.date()
                ]
            )

            return daily_assignments >= instructor.max_daily_sessions

        except Exception as e:
            anvil.server.error(f"Error checking daily limit: {str(e)}")
            return True

    def _format_schedule(self) -> Dict:
        """Format the schedule for output."""
        try:
            schedule = {
                "assignments": self.assignments,
                "summary": {
                    "total_slots": len(self.assignments),
                    "instructors": {},
                    "schools": {},
                },
            }

            # Calculate instructor summaries
            for instructor in self.instructors:
                instructor_assignments = [
                    a
                    for a in self.assignments.values()
                    if a["instructor_id"] == instructor.id
                ]

                schedule["summary"]["instructors"][instructor.id] = {
                    "name": instructor.name,
                    "total_slots": len(instructor_assignments),
                    "daily_average": len(instructor_assignments) / 7,  # Assuming 7 days
                }

            return schedule

        except Exception as e:
            anvil.server.error(f"Error formatting schedule: {str(e)}")
            raise

    def calculate_gross_availability(
        self,
        start_date: datetime,
        duration_weeks: int = 6,
        school_list: List[str] = None,
    ) -> Dict[str, Dict]:
        """
        Calculate gross availability of time slots across all schools.

        Args:
            start_date: Start date of the program
            duration_weeks: Duration of the program in weeks
            school_list: List of school IDs (default: ['A', 'B', 'C', 'D'])

        Returns:
            Dict containing total available slots per school, broken down by preference level
        """
        try:
            # Initialize schools if not provided
            if school_list is None:
                school_list = ["A", "B", "C", "D"]

            # Initialize school objects
            self.schools = {
                school_id: School(id=school_id, name=f"School {school_id}")
                for school_id in school_list
            }

            # Get all instructors
            instructors = app_tables.users.search(is_instructor=True)

            # Process each week
            for week in range(duration_weeks):
                current_date = start_date + timedelta(weeks=week)

                # Skip if it's a holiday
                if self._is_holiday(current_date):
                    continue

                # Process each instructor
                for instructor in instructors:
                    # Skip if instructor is on vacation
                    if self._is_instructor_on_vacation(instructor, current_date):
                        continue

                    # Get instructor's availability for the day
                    availability = self._get_instructor_availability(
                        instructor, current_date
                    )

                    # Process each time slot
                    for slot in availability:
                        # Skip if instructor is not available
                        if availability[slot] == AvailabilityType.NO:
                            continue

                        # Count schools by preference level for this slot
                        preferred_schools = []
                        possible_schools = []

                        for school_id, school in self.schools.items():
                            preference = instructor.school_preferences.get(
                                school_id, SchoolPreference.NO
                            )
                            if preference == SchoolPreference.PREFERRED:
                                preferred_schools.append(school_id)
                            elif preference == SchoolPreference.POSSIBLE:
                                possible_schools.append(school_id)

                        # Calculate slot distribution
                        total_schools = len(preferred_schools) + len(possible_schools)
                        if total_schools == 0:
                            continue

                        # Distribute slots to preferred schools first
                        slots_per_preferred = 1
                        if len(preferred_schools) > 0:
                            slots_per_preferred = max(1, len(preferred_schools))

                        # Distribute remaining slots to possible schools
                        remaining_slots = len(availability) - (
                            slots_per_preferred * len(preferred_schools)
                        )
                        slots_per_possible = 0
                        if len(possible_schools) > 0 and remaining_slots > 0:
                            slots_per_possible = max(
                                1, remaining_slots // len(possible_schools)
                            )

                        # Assign slots to schools
                        for school_id in preferred_schools:
                            self.schools[
                                school_id
                            ].preferred_slots += slots_per_preferred
                            self.schools[school_id].total_slots += slots_per_preferred

                        for school_id in possible_schools:
                            self.schools[school_id].possible_slots += slots_per_possible
                            self.schools[school_id].total_slots += slots_per_possible

            # Format results
            results = {}
            for school_id, school in self.schools.items():
                results[school_id] = {
                    "name": school.name,
                    "total_slots": school.total_slots,
                    "preferred_slots": school.preferred_slots,
                    "possible_slots": school.possible_slots,
                }

            return results

        except Exception as e:
            anvil.server.error(f"Error in calculate_gross_availability: {str(e)}")
            raise

    def _is_holiday(self, date: datetime) -> bool:
        """Check if a date is a holiday."""
        try:
            holiday = app_tables.no_class_dates.get(date=date)
            return holiday is not None
        except Exception as e:
            anvil.server.error(f"Error checking holiday: {str(e)}")
            return False

    def _is_instructor_on_vacation(self, instructor, date: datetime) -> bool:
        """Check if an instructor is on vacation on a given date."""
        try:
            schedule = app_tables.instructor_schedules.get(instructor=instructor)
            if schedule and schedule["vacation_days"]:
                return date in schedule["vacation_days"]
            return False
        except Exception as e:
            anvil.server.error(f"Error checking vacation: {str(e)}")
            return False

    def _get_instructor_availability(
        self, instructor, date: datetime
    ) -> Dict[str, AvailabilityType]:
        """Get an instructor's availability for a given date."""
        try:
            schedule = app_tables.instructor_schedules.get(instructor=instructor)
            if schedule and schedule["weekly_availability"]:
                day_name = date.strftime("%A").lower()
                return schedule["weekly_availability"].get(day_name, {})
            return {}
        except Exception as e:
            anvil.server.error(f"Error getting availability: {str(e)}")
            return {}

    def test_allocation(
        self,
        start_date: datetime,
        duration_weeks: int = 6,
        school_list: List[str] = None,
    ) -> Dict:
        """
        Test function to show detailed breakdown of time slot allocation.
        """
        try:
            if school_list is None:
                school_list = ["A", "B", "C", "D"]

            self.schools = {
                school_id: School(id=school_id, name=f"School {school_id}")
                for school_id in school_list
            }

            instructors = app_tables.users.search(is_instructor=True)

            results = {
                "total_slots": 0,
                "instructors": {},
                "schools": {
                    school_id: {
                        "name": f"School {school_id}",
                        "total_slots": 0,
                        "preferred_slots": 0,
                        "possible_slots": 0,
                        "instructors": {},
                    }
                    for school_id in school_list
                },
            }

            for week in range(duration_weeks):
                current_date = start_date + timedelta(weeks=week)

                if self._is_holiday(current_date):
                    continue

                for instructor in instructors:
                    if self._is_instructor_on_vacation(instructor, current_date):
                        continue

                    availability = self._get_instructor_availability(
                        instructor, current_date
                    )
                    if not availability:
                        continue

                    instructor_name = (
                        f"{instructor['firstName']} {instructor['surname']}"
                    )
                    if instructor_name not in results["instructors"]:
                        results["instructors"][instructor_name] = {
                            "name": instructor_name,
                            "total_slots": 0,
                            "max_daily_sessions": instructor.get(
                                "max_daily_sessions", 4
                            ),
                            "schools": {
                                school_id: {
                                    "preferred_slots": 0,
                                    "possible_slots": 0,
                                    "total_slots": 0,
                                }
                                for school_id in school_list
                            },
                        }

                    results["total_slots"] += len(availability)
                    results["instructors"][instructor_name]["total_slots"] += len(
                        availability
                    )

                    for slot in availability:
                        if availability[slot] == AvailabilityType.NO:
                            continue

                        preferred_schools = []
                        possible_schools = []

                        for school_id in school_list:
                            preference = instructor.get("school_preferences", {}).get(
                                school_id, SchoolPreference.NO
                            )
                            if preference == SchoolPreference.PREFERRED:
                                preferred_schools.append(school_id)
                            elif preference == SchoolPreference.POSSIBLE:
                                possible_schools.append(school_id)

                        total_schools = len(preferred_schools) + len(possible_schools)
                        if total_schools == 0:
                            continue

                        slots_per_preferred = 1
                        if len(preferred_schools) > 0:
                            slots_per_preferred = max(1, len(preferred_schools))

                        remaining_slots = len(availability) - (
                            slots_per_preferred * len(preferred_schools)
                        )
                        slots_per_possible = 0
                        if len(possible_schools) > 0 and remaining_slots > 0:
                            slots_per_possible = max(
                                1, remaining_slots // len(possible_schools)
                            )

                        for school_id in preferred_schools:
                            self.schools[
                                school_id
                            ].preferred_slots += slots_per_preferred
                            self.schools[school_id].total_slots += slots_per_preferred
                            results["schools"][school_id][
                                "preferred_slots"
                            ] += slots_per_preferred
                            results["schools"][school_id][
                                "total_slots"
                            ] += slots_per_preferred
                            results["instructors"][instructor_name]["schools"][
                                school_id
                            ]["preferred_slots"] += slots_per_preferred
                            results["instructors"][instructor_name]["schools"][
                                school_id
                            ]["total_slots"] += slots_per_preferred

                        for school_id in possible_schools:
                            self.schools[school_id].possible_slots += slots_per_possible
                            self.schools[school_id].total_slots += slots_per_possible
                            results["schools"][school_id][
                                "possible_slots"
                            ] += slots_per_possible
                            results["schools"][school_id][
                                "total_slots"
                            ] += slots_per_possible
                            results["instructors"][instructor_name]["schools"][
                                school_id
                            ]["possible_slots"] += slots_per_possible
                            results["instructors"][instructor_name]["schools"][
                                school_id
                            ]["total_slots"] += slots_per_possible

            return results

        except Exception as e:
            anvil.server.error(f"Error in test_allocation: {str(e)}")
            raise


@anvil.server.callable
def test_allocation_breakdown(start_date, duration_weeks=6, school_list=None):
    """
    Server callable function to get a formatted breakdown of the allocation.
    """
    try:
        parsed_date = datetime.strptime(start_date, "%m-%d-%Y")
        optimizer = SchedulerOptimizer()
        results = optimizer.test_allocation(parsed_date, duration_weeks, school_list)

        output = []
        output.append("=== ALLOCATION BREAKDOWN ===")
        output.append(f"Total Available Slots: {results['total_slots']}")
        output.append("\n=== SCHOOLS ===")

        for school_id, school_data in results["schools"].items():
            output.append(f"\nSchool {school_id}:")
            output.append(f"  Total Slots: {school_data['total_slots']}")
            output.append(f"  Preferred Slots: {school_data['preferred_slots']}")
            output.append(f"  Possible Slots: {school_data['possible_slots']}")

        output.append("\n=== INSTRUCTORS ===")
        for instructor_data in results["instructors"].values():
            output.append(f"\n{instructor_data['name']}:")
            output.append(f"  Total Slots: {instructor_data['total_slots']}")
            output.append(
                f"  Max Daily Sessions: {instructor_data['max_daily_sessions']}"
            )
            output.append("  School Allocations:")
            for school_id, school_data in instructor_data["schools"].items():
                if school_data["total_slots"] > 0:
                    output.append(f"    School {school_id}:")
                    output.append(f"      Total Slots: {school_data['total_slots']}")
                    output.append(
                        f"      Preferred Slots: {school_data['preferred_slots']}"
                    )
                    output.append(
                        f"      Possible Slots: {school_data['possible_slots']}"
                    )

        return "\n".join(output)

    except Exception as e:
        anvil.server.error(f"Error in test_allocation_breakdown: {str(e)}")
        raise
