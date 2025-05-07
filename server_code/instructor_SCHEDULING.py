import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime
from .globals import LESSON_SLOTS, AVAILABILITY_MAPPING


@anvil.server.callable
def schedule_instructors_for_cohort(cohort_name, instructor1, instructor2):
    """
    Schedule instructors for a cohort's lessons based on availability.
    Alternates primary instructor by week.

    Args:
        cohort_name (str): Name of the cohort to schedule
        instructor1_name (str): First instructor's name
        instructor2_name (str): Second instructor's name

    Returns:
        dict: Updated cohort schedule with instructor assignments
    """
    # Get cohort data
    print("Checking for cohort")
    cohort = app_tables.cohorts.get(cohort_name=cohort_name["cohort_name"])
    if not cohort:
        raise ValueError(f"Cohort {cohort_name} not found")

    # Get instructor data
    # UI will retutn a row for instructor
    print("Checking for instructors")
    print(instructor1["firstName"])
    print(instructor2["firstName"])

    if not instructor1 or not instructor2:
        raise ValueError("One or both instructors not found")

    # Get instructor schedules
    print("Checking for instructor schedules")
    instructor1_schedule = app_tables.instructor_schedules.get(instructor=instructor1)
    instructor2_schedule = app_tables.instructor_schedules.get(instructor=instructor2)

    if not instructor1_schedule or not instructor2_schedule:
        raise ValueError("One or both instructor schedules not found")

    # Get availability data
    instructor1_availability = instructor1_schedule["current_seven_month_availability"]
    instructor2_availability = instructor2_schedule["current_seven_month_availability"]

    # Get the complete schedule
    daily_schedules = cohort["complete_schedule"]
    print("Checked initial info collection")

    # First pass: Schedule classes
    daily_schedules = _schedule_classes(
        daily_schedules,
        instructor1,
        instructor2,
        instructor1_availability,
        instructor2_availability,
    )

    # Second pass: Schedule remaining lessons
    daily_schedules = _schedule_remaining_lessons(
        daily_schedules,
        instructor1,
        instructor2,
        instructor1_availability,
        instructor2_availability,
    )

    # Update cohort with new schedule
    cohort.update(complete_schedule=daily_schedules)

    # Log the final availability updates that would be persisted
    _persist_instructor_availability(instructor1, instructor1_availability)
    _persist_instructor_availability(instructor2, instructor2_availability)

    return daily_schedules


def _get_primary_instructor(date_str, instructor1, instructor2):
    """
    Determine which instructor is primary for the week containing the given date.
    Alternates by week, with instructor1 being primary for odd weeks.
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    week_number = date.isocalendar()[1]  # Get ISO week number
    return instructor1 if week_number % 2 == 1 else instructor2


def _schedule_classes(
    daily_schedules,
    instructor1,
    instructor2,
    instructor1_availability,
    instructor2_availability,
):
    """
    Schedule classes first, checking for 'Yes' or 'Class Only' availability.
    Primary instructor for the week gets first choice of slots.
    """
    for day in daily_schedules:
        date_str = day["date"]
        primary_instructor = _get_primary_instructor(date_str, instructor1, instructor2)
        secondary_instructor = (
            instructor2 if primary_instructor == instructor1 else instructor1
        )

        for slot, slot_data in day["slots"].items():
            if slot_data["type"] is None:
                pass
            elif slot_data["type"] == "class":
                # Check primary instructor first
                primary_available = _can_teach_class(
                    (
                        instructor1_availability
                        if primary_instructor == instructor1
                        else instructor2_availability
                    ),
                    date_str,
                    slot,
                )

                if primary_available:
                    slot_data["instructor"] = primary_instructor["firstName"]
                    _update_instructor_availability(
                        (
                            instructor1_availability
                            if primary_instructor == instructor1
                            else instructor2_availability
                        ),
                        date_str,
                        slot,
                        primary_instructor,
                    )
                else:
                    # Check secondary instructor
                    secondary_available = _can_teach_class(
                        (
                            instructor1_availability
                            if secondary_instructor == instructor1
                            else instructor2_availability
                        ),
                        date_str,
                        slot,
                    )

                    if secondary_available:
                        slot_data["instructor"] = secondary_instructor["firstName"]
                        _update_instructor_availability(
                            (
                                instructor1_availability
                                if secondary_instructor == instructor1
                                else instructor2_availability
                            ),
                            date_str,
                            slot,
                            secondary_instructor,
                        )

    return daily_schedules


def _schedule_remaining_lessons(
    daily_schedules,
    instructor1,
    instructor2,
    instructor1_availability,
    instructor2_availability,
):
    """
    Schedule remaining lessons (drives) based on availability.
    Primary instructor for the week gets first choice of slots.
    """
    for day in daily_schedules:
        date_str = day["date"]
        primary_instructor = _get_primary_instructor(date_str, instructor1, instructor2)
        secondary_instructor = (
            instructor2 if primary_instructor == instructor1 else instructor1
        )

        for slot, slot_data in day["slots"].items():
            if slot_data["type"] == "drive" and "instructor" not in slot_data:
                # Check primary instructor first
                primary_available = _can_teach_drive(
                    (
                        instructor1_availability
                        if primary_instructor == instructor1
                        else instructor2_availability
                    ),
                    date_str,
                    slot,
                )

                if primary_available:
                    slot_data["instructor"] = primary_instructor["firstName"]
                    _update_instructor_availability(
                        (
                            instructor1_availability
                            if primary_instructor == instructor1
                            else instructor2_availability
                        ),
                        date_str,
                        slot,
                        primary_instructor,
                    )
                else:
                    # Check secondary instructor
                    secondary_available = _can_teach_drive(
                        (
                            instructor1_availability
                            if secondary_instructor == instructor1
                            else instructor2_availability
                        ),
                        date_str,
                        slot,
                    )

                    if secondary_available:
                        slot_data["instructor"] = secondary_instructor["firstName"]
                        _update_instructor_availability(
                            (
                                instructor1_availability
                                if secondary_instructor == instructor1
                                else instructor2_availability
                            ),
                            date_str,
                            slot,
                            secondary_instructor,
                        )

    return daily_schedules


def _can_teach_class(availability, date_str, slot):
    """
    Check if instructor can teach a class based on availability.
    Returns True if availability is 'Yes' or 'Class Only'.
    """
    if date_str not in availability or slot not in availability[date_str]:
        return False

    slot_availability = availability[date_str][slot]
    return slot_availability in [
        AVAILABILITY_MAPPING["Yes"],
        AVAILABILITY_MAPPING["Class Only"],
    ]


def _can_teach_drive(availability, date_str, slot):
    """
    Check if instructor can teach a drive based on availability.
    Returns True if availability is 'Yes' or 'Drive Only'.
    """
    if date_str not in availability or slot not in availability[date_str]:
        return False

    slot_availability = availability[date_str][slot]
    return slot_availability in [
        AVAILABILITY_MAPPING["Yes"],
        AVAILABILITY_MAPPING["Drive Only"],
    ]


def _update_instructor_availability(availability, date_str, slot, instructor):
    """
    Update instructor's availability to 'Scheduled' for a slot.
    Logs the update instead of writing to database for testing.
    """
    if date_str in availability and slot in availability[date_str]:
        availability[date_str][slot] = AVAILABILITY_MAPPING["Scheduled"]


def _persist_instructor_availability(instructor, availability):
    """
    Persist instructor's availability to the database.
    Currently just logs the update for testing.
    """
    instructor_schedule = app_tables.instructor_schedules.get(instructor=instructor)
    if instructor_schedule:
        instructor_schedule.update(current_seven_month_availability=availability)
