import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files

"""
classroom Builder Module

Handles creation and scheduling of driving school classrooms.
"""

import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, timedelta, date
from .globals import (
    AVAILABILITY_MAPPING,
    COURSE_STRUCTURE_COMPRESSED,
    COURSE_STRUCTURE_STANDARD,
    LESSON_SLOTS,
)

# Schools are referenced by their abbreviation found in app_tables / schools / abbreviation

# Constants
STUDENTS_PER_DRIVE = 2
MAX_classroom_SIZE = 30
BUFFER_PERCENTAGE = 0.9
# Other constants are based on the course structure

# Test data for no_class_days if table is empty
no_class_days_test = {
    "2025-01-01": "New Year's Day",
    "2025-05-01": "May Day Test",
    "2025-05-26": "Memorial Day",
    "2025-07-04": "Independence Day",
    "2025-09-02": "Labor Day",
    "2025-11-28": "Thanksgiving",
    "2025-12-25": "Christmas Day",
}


# no_class_days_listed = app_tables.no_class_days.search(applies_all_or_school='all')
no_class_days_listed = None
if no_class_days_listed is None:
    no_class_days = no_class_days_test
else:
    no_class_days = no_class_days_listed


@anvil.server.callable
def get_available_days(start_date, course_structure):
    """
    Get available days for the program, excluding holidays.
    Note: Instructor vacations are handled separately in get_daily_drive_slots.

    Args:
        start_date (date): Start date of the program

    Returns:
        list: List of available dates
    ⚠️ Needs testing with regular availability and a large holiday block
    """
    available_days = []
    current_date = start_date
    # course_structure is now always a dict
    # Get holidays from the database
    holidays = [
        {"date": datetime.strptime(date_str, "%Y-%m-%d").date(), "name": name}
        for date_str, name in no_class_days.items()
    ]
    holiday_dates = {h["date"] for h in holidays}
    days_checked = 0
    max_days_to_check = 90
    while (
        len(available_days) < course_structure["sequence"]["MIN_COURSE_LENGTH"]
        and days_checked < max_days_to_check
    ):
        if current_date not in holiday_dates:
            available_days.append(current_date)
        current_date += timedelta(days=1)
        days_checked += 1
    if len(available_days) < course_structure["sequence"]["MIN_COURSE_LENGTH"]:
        days_short = course_structure["sequence"]["MIN_COURSE_LENGTH"] - len(
            available_days
        )
        raise ValueError(
            f"Could not find enough available days. Need {days_short} more days to meet minimum course length of {course_structure['sequence']['MIN_COURSE_LENGTH']} days"
        )
    return available_days


def get_daily_drive_slots(day, school):
    """
    Calculate total available drive slots for a specific day across all instructors.
    Only includes instructors who can teach at the specified school.

    Args:
        day (date): The day to check
        school (str): School abbreviation (e.g., 'HSS', 'NHS') from app_tables/schools/abbreviation

    Returns:
        int: Total number of available drive slots for the day
    ✅ This has been tested and function works as expected
    BUT!
    ⚠️ Need to do manual comparison to check exact results.
    """
    total_slots = 0
    instructors = app_tables.users.search(is_instructor=True)

    for instructor in instructors:
        instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_row:
            continue

        # Check school preferences
        school_prefs = instructor_row["school_preferences"]
        # print(school_prefs)
        # print(f"Checking preferences for {instructor['firstName']}: {school_prefs}")
        if school in school_prefs.get("school_preferences", {}).get("no", []):
            # ✅ This is working as expected
            continue

        # Check vacations
        instructor_vacations = instructor_row["vacation_days"]
        if day in instructor_vacations:
            continue

        # Get availability for the specific day
        instructor_availability = instructor_row["weekly_availability_term"][
            "weekly_availability"
        ]
        day_name = day.strftime("%A").lower()
        day_availability = instructor_availability.get(day_name, {})
        if not day_availability:
            continue

        # Count available drive slots
        for slot, status in day_availability.items():
            if status == "Yes" or status == "Drive Only":
                total_slots += 1

    return total_slots


@anvil.server.callable
def calculate_weekly_capacity(start_date, school, course_structure):
    """
    Calculate the weekly capacity based on available drive slots,
    taking into account instructor availability, vacations, and school preferences.

    Args:
        start_date (date): Start date of the program
        school (str): School abbreviation (e.g., 'HSS', 'NHS') from app_tables/schools/abbreviation
        course_structure (dict): Course structure

    Returns:
        dict: Contains weekly capacity information
    ✅ This has been tested and function works as expected
    BUT!
    ⚠️ Need to do manual comparison to check exact results.
    """
    available_days = get_available_days(start_date, course_structure)
    weekly_days = {}
    for day in available_days:
        week_num = (day - start_date).days // 7 + 1
        if week_num not in weekly_days:
            weekly_days[week_num] = []
        weekly_days[week_num].append(day)
    weekly_slots = {}
    for week_num in range(1, 7):
        total_slots = 0
        week_days = [
            day
            for day in available_days
            if (day - start_date).days // 7 + 1 == week_num
        ]
        for day in week_days:
            total_slots += get_daily_drive_slots(day, school)
        available_slots = int(total_slots)
        weekly_slots[week_num] = available_slots
    max_weekly_slots = max(weekly_slots.values())
    avg_weekly_slots = sum(weekly_slots.values()) / len(weekly_slots)
    max_students = min(
        max_weekly_slots * STUDENTS_PER_DRIVE,
        course_structure["class_sessions"]["max_students"],
    )
    weekly_slots_serialized = {str(k): v for k, v in weekly_slots.items()}
    return {
        "weekly_slots": weekly_slots_serialized,
        "max_weekly_slots": max_weekly_slots,
        "avg_weekly_slots": avg_weekly_slots,
        "max_students": max_students,
    }


@anvil.server.callable
def generate_classroom_name(school, start_date):
    """
    Generate classroom name in format YEAR-SEQUENCENUMBER-SCHOOL_ABBREVIATION
    Example: 2025-11-HSS
    Also creates the classroom record in the database
    ✅ This has been tested and works as designed
    """
    year = start_date.year
    # Get next sequence number for this year
    existing_classrooms = app_tables.classrooms.search(school=school)
    sequence = len(existing_classrooms) + 1
    full_name = f"{year}-{sequence:02d}-{school}"

    # Calculate end date (6 weeks from start)
    end_date = start_date + timedelta(weeks=6)

    # Determine status
    today = datetime.now().date()
    status = "planned" if start_date > today else "active"

    # Create classroom record
    app_tables.classrooms.add_row(
        classroom_name=full_name,
        start_date=start_date,
        end_date=end_date,
        status=status,
        school=school,
        sequence=sequence,
    )

    return full_name


@anvil.server.callable
def create_ghost_students(classroom_name, num_students):
    """
    Create ghost student records for the classroom
    Example IDs: 2025-11-HSS-student01
    ⚠️ Needs testing
    """
    students = []
    for i in range(1, num_students + 1):
        student_id = f"{classroom_name}-student{i:02d}"
        students.append(student_id)
    classroom_record = app_tables.classrooms.get(classroom_name=classroom_name)
    classroom_record.update(student_list=students)
    return students


@anvil.server.callable
def schedule_classes(classroom_name, start_date, num_students, course_structure):
    """
    Schedule classes for the classroom.
    Classes must be on specific days of the week as defined in class_days.
    Returns a simplified object format suitable for table storage.
    """
    available_days = get_available_days(start_date, course_structure)
    class_schedule = []
    current_week = 1
    current_class = 1
    class_days = course_structure["class_sessions"]["class_days"]
    classes_per_week = course_structure["class_sessions"]["classes_per_week"]

    # Create a dynamic class_day_map
    class_day_map = {}
    class_number = 1

    # For each week
    for week in range(1, 6):  # Assuming 5 weeks of classes
        # For each class in the week
        for i in range(classes_per_week):
            # Get the day index (0-6) for this class
            day_index = class_days[
                i
            ]  # This assumes class_days is a list of day indices
            class_day_map[class_number] = day_index
            class_number += 1

    while current_class <= 15:
        required_day = class_day_map[current_class]
        week_offset = (current_week - 1) * 7
        target_date = start_date + timedelta(days=week_offset + required_day)
        class_date = None
        for day in available_days:
            if day >= target_date and day.weekday() == required_day:
                class_date = day
                break
        if class_date is None:
            print(f"Warning: Could not find available date for Class {current_class}")
            break
        class_slot = {
            "class_number": current_class,
            "date": class_date.isoformat(),
            "week": current_week,
            "day": class_date.strftime("%A"),
            "status": "scheduled",
        }
        class_schedule.append(class_slot)
        current_class += 1

        if current_class % classes_per_week == 1:
            current_week += 1

    # Print orientation details
    print(f"\nOrientation: {start_date.strftime('%A, %Y-%m-%d')}")

    # Print first few classes to verify scheduling
    print("\nFirst 3 classes:")
    for slot in class_schedule[1:4]:  # Skip orientation (index 0)
        print(f"Class {slot['class_number']}: {slot['date']} ({slot['day']})")

    # Print week transitions
    print("\nWeek transitions:")
    current_week = 1
    for slot in class_schedule:
        if slot["week"] != current_week:
            print(f"Week {current_week} -> {slot['week']}")
            current_week = slot["week"]

    return class_schedule


def get_weekly_lesson_slots(week_number, course_structure):
    weekly_slots = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }
    class_days = course_structure["class_sessions"]["class_days"]
    class_slot = "lesson_slot_5"
    for slot_name, slot_info in LESSON_SLOTS.items():
        if not slot_name.startswith("break_"):
            term_days = [day.strip() for day in slot_info["term"].split(",")]
            if term_days == ["all"]:
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
                    if (
                        week_number < 6
                        and day in class_days
                        and slot_name == class_slot
                    ):
                        continue
                    weekly_slots[day].append(slot_name)
                if slot_name in ["lesson_slot_4", "lesson_slot_5"]:
                    weekly_slots["Saturday"].append(slot_name)
                    weekly_slots["Sunday"].append(slot_name)
            elif term_days == ["Sat", "Sun"]:
                weekly_slots["Saturday"].append(slot_name)
                weekly_slots["Sunday"].append(slot_name)
    return weekly_slots


@anvil.server.callable
def schedule_drives(classroom_name, start_date, num_students, course_structure):
    """
    Schedule drives (1 per week for weeks 2-6)
    First creates a master schedule that repeats each week, then adjusts for vacation days
    """
    available_days = get_available_days(start_date, course_structure)
    num_pairs = num_students // 2
    drives = []
    vacation_days = [
        datetime.strptime(date_str, "%Y-%m-%d").date()
        for date_str in no_class_days.keys()
    ]
    spare_slots = {
        "Tuesday": "lesson_slot_5",
        "Thursday": "lesson_slot_5",
        "Sunday": "lesson_slot_5",
    }
    master_schedule = []
    used_slots = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }
    weekly_slots = get_weekly_lesson_slots(2, course_structure)
    for pair in range(num_pairs):
        pair_letter = chr(65 + pair)
        scheduled = False
        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]:
            if scheduled:
                break
            for slot in weekly_slots[day]:
                if slot not in used_slots[day]:
                    master_schedule.append(
                        {"pair_letter": pair_letter, "day": day, "slot": slot}
                    )
                    used_slots[day].append(slot)
                    scheduled = True
                    break
    for week in range(5):
        week_num = week + 2
        week_start = start_date + timedelta(days=7 * (week + 1))
        week_days = [
            day
            for day in available_days
            if week_start <= day < week_start + timedelta(days=7)
        ]
        drives_to_reschedule = []
        drive_numbers = course_structure["driving_sessions"]["pairs"][week_num - 2]
        for master_drive in master_schedule:
            pair_letter = master_drive["pair_letter"]
            master_day = master_drive["day"]
            master_slot = master_drive["slot"]
            target_date = None
            for day in week_days:
                if day.strftime("%A") == master_day:
                    target_date = day
                    break
            if target_date and target_date not in vacation_days:
                drive_slot = {
                    "classroom": classroom_name,
                    "pair_letter": pair_letter,
                    "drive_numbers": drive_numbers,
                    "date": target_date.isoformat(),
                    "slot": master_slot,
                    "week": week_num,
                    "is_backup_slot": master_day in ["Tuesday", "Thursday", "Sunday"],
                    "is_weekend": target_date.weekday() in [5, 6],
                    "instructor": None,
                    "status": "scheduled",
                }
                drives.append(drive_slot)
            else:
                drives_to_reschedule.append(
                    {
                        "pair_letter": pair_letter,
                        "week": week_num,
                        "original_day": master_day,
                        "original_slot": master_slot,
                    }
                )
        if drives_to_reschedule:
            for drive in drives_to_reschedule:
                rescheduled = False
                for day, slot in spare_slots.items():
                    if not rescheduled:
                        for week_day in week_days:
                            if (
                                week_day.strftime("%A") == day
                                and week_day not in vacation_days
                            ):
                                slot_used = any(
                                    d["date"] == week_day.isoformat()
                                    and d["slot"] == slot
                                    for d in drives
                                )
                                if not slot_used:
                                    drive_slot = {
                                        "classroom": classroom_name,
                                        "pair_letter": drive["pair_letter"],
                                        "drive_numbers": drive_numbers,
                                        "date": week_day.isoformat(),
                                        "slot": slot,
                                        "week": drive["week"],
                                        "is_backup_slot": True,
                                        "is_weekend": week_day.weekday() in [5, 6],
                                        "instructor": None,
                                        "status": "scheduled",
                                        "rescheduled_from": f"{drive['original_day']} {drive['original_slot']}",
                                    }
                                    drives.append(drive_slot)
                                    rescheduled = True
                                    break
                if not rescheduled:
                    for week_day in week_days:
                        if week_day not in vacation_days and not rescheduled:
                            available_slots = get_weekly_lesson_slots(
                                week_num, course_structure
                            )[week_day.strftime("%A")]
                            for slot in available_slots:
                                slot_used = any(
                                    d["date"] == week_day.isoformat()
                                    and d["slot"] == slot
                                    for d in drives
                                )
                                if not slot_used:
                                    drive_slot = {
                                        "classroom": classroom_name,
                                        "pair_letter": drive["pair_letter"],
                                        "drive_numbers": drive_numbers,
                                        "date": week_day.isoformat(),
                                        "slot": slot,
                                        "week": drive["week"],
                                        "is_backup_slot": True,
                                        "is_weekend": week_day.weekday() in [5, 6],
                                        "instructor": None,
                                        "status": "scheduled",
                                        "rescheduled_from": f"{drive['original_day']} {drive['original_slot']}",
                                    }
                                    drives.append(drive_slot)
                                    rescheduled = True
                                    break
                if not rescheduled:
                    print(
                        f"WARNING: Could not reschedule Pair {drive['pair_letter']} in week {drive['week']}"
                    )
                    print(
                        f"Original schedule: {drive['original_day']} at {drive['original_slot']}"
                    )
    classroom_data_row = app_tables.classrooms.get(classroom_name=classroom_name)
    if classroom_data_row:
        classroom_data_row.update(drive_schedule=drives)
    return drives


@anvil.server.callable
def create_full_classroom_schedule(
    school, start_date, num_students=None, classroom_type=None
):
    """
    Create a complete schedule for a new classroom including:
    - classroom creation
    - Student assignment
    - Class scheduling
    - Drive scheduling

    Args:
        school (str): School abbreviation (e.g., 'HSS', 'NHS')
        start_date (date): Start date of the program
        num_students (int, optional): Number of students. If None, will calculate based on capacity
        classroom_type (str, optional): 'standard' or 'compressed'

    Returns:
        str: Task ID for tracking the background process
    """
    # Generate task ID
    task_id = f"classroom_{school}_{start_date.strftime('%Y%m%d')}"

    # Create task record
    task_record = app_tables.background_tasks.add_row(
        task_id=task_id, status="running", start_time=datetime.now()
    )

    # Launch background task
    anvil.server.launch_background_task(
        "create_full_classroom_schedule_background",
        school,
        start_date,
        num_students,
        classroom_type,
        task_id,
    )

    return task_id


@anvil.server.background_task
def create_full_classroom_schedule_background(
    school, start_date, num_students, classroom_type, task_id
):
    """
    Background task version of create_full_classroom_schedule
    """
    try:
        # Select course structure ONCE
        if classroom_type == "compressed":
            course_structure = COURSE_STRUCTURE_COMPRESSED
        else:
            course_structure = COURSE_STRUCTURE_STANDARD

        # 1. Generate classroom name
        classroom_name = generate_classroom_name(school, start_date)

        # 2. Calculate capacity if num_students not provided
        if num_students is None:
            capacity = calculate_weekly_capacity(start_date, school, course_structure)
            num_students = min(
                capacity["max_students"],
                course_structure["class_sessions"]["max_students"],
            )

        # 3. Create student records
        students = create_ghost_students(classroom_name, num_students)

        # 4. Schedule classes
        classes = schedule_classes(
            classroom_name, start_date, num_students, course_structure
        )

        # 5. Schedule drives
        drives = schedule_drives(
            classroom_name, start_date, num_students, course_structure
        )

        complete_schedule = anvil.server.call("create_merged_schedule", classroom_name)

        # 6. Store everything in the classroom record
        classroom_data_row = app_tables.classrooms.get(classroom_name=classroom_name)
        if classroom_data_row:
            classroom_data_row.update(
                student_list=students,
                class_schedule=classes,
                drive_schedule=drives,
                status="scheduled",
                complete_schedule=complete_schedule,
            )

        result = {
            "classroom_name": classroom_name,
            "num_students": num_students,
            "students": students,
            "classes": classes,
            "drives": drives,
            "complete_schedule": complete_schedule,
            "start_date": start_date,
            "end_date": start_date + timedelta(weeks=6),
        }

        # Update task record with success
        task_record = app_tables.background_tasks.get(task_id=task_id)
        if task_record:
            task_record.update(
                status="done", end_time=datetime.now(), result=str(result)
            )
        return result

    except Exception as e:
        # Update task record with error
        task_record = app_tables.background_tasks.get(task_id=task_id)
        if task_record:
            task_record.update(status="error", end_time=datetime.now(), error=str(e))
        return str(e)


@anvil.server.callable
def check_classroom_task_status(task_id):
    """
    Check the status of a classroom creation task
    """
    task = app_tables.background_tasks.get(task_id=task_id)
    if not task:
        return "not_found"
    return task["status"]


@anvil.server.callable
def test_capacity_calculation(start_date=None, school=None):
    """
    Test function to verify the capacity calculation functions.
    Tests each function individually and shows their results.

    Args:
        start_date (date): Optional start date (defaults to next Monday)
        school (str): School abbreviation (e.g., 'HSS', 'NHS') from app_tables/schools/abbreviation

    Returns:
        dict: Test results with function outputs
    """
    if start_date is None:
        today = datetime.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_monday)

    if school is None:
        school = "HSS"  # Default to HSS for testing

    print("\n=== Testing classroom Builder Functions ===")
    print(f"Start Date: {start_date}")
    print(f"School: {school}")

    # Test get_available_days
    print("\n1. Testing get_available_days...")
    available_days = get_available_days(start_date, course_structure)
    print(f"Found {len(available_days)} available days")
    print(f"First day: {available_days[0]}")
    print(f"Last day: {available_days[-1]}")

    # Test get_daily_drive_slots for first and last day
    print("\n2. Testing get_daily_drive_slots...")
    first_day_slots = get_daily_drive_slots(available_days[0], school)
    last_day_slots = get_daily_drive_slots(available_days[-1], school)
    print(f"First day slots: {first_day_slots}")
    print(f"Last day slots: {last_day_slots}")

    # Test calculate_weekly_capacity
    print("\n3. Testing calculate_weekly_capacity...")
    capacity = calculate_weekly_capacity(start_date, school, COURSE_STRUCTURE_STANDARD)
    print(f"Weekly slots: {capacity['weekly_slots']}")
    print(f"Max weekly slots: {capacity['max_weekly_slots']}")
    print(f"Maximum students: {capacity['max_students']}")

    # Test classroom creation
    print("\n4. Testing classroom creation...")
    classroom_name = generate_classroom_name(school, start_date)
    print(f"Generated classroom name: {classroom_name}")

    # Test class scheduling
    print("\n5. Testing class scheduling...")
    classes = schedule_classes(
        classroom_name, start_date, capacity["max_students"], COURSE_STRUCTURE_STANDARD
    )
    print(f"Scheduled {len(classes)} classes")
    print("First week classes:")
    for class_slot in classes[:3]:
        print(f"  • Class {class_slot['class_number']} on {class_slot['date']}")

    # Test drive scheduling
    print("\n6. Testing drive scheduling...")
    drives = schedule_drives(
        classroom_name, start_date, capacity["max_students"], COURSE_STRUCTURE_STANDARD
    )
    print(f"Scheduled {len(drives)} drives")

    # Debug printing for drives
    print("\nDebug - All drives:")
    for drive in drives:
        print(f"  • Pair {drive['pair_letter']} on {drive['date']}")

    print("\nDebug - First week calculation:")
    for drive in drives:
        drive_date = datetime.fromisoformat(drive["date"]).date()
        days_diff = (drive_date - start_date).days
        print(
            f"  • Pair {drive['pair_letter']} on {drive['date']} (days from start: {days_diff})"
        )

    print("\nFirst week drives:")
    # Filter for drives in week 2 (days 7-13 from start)
    first_week_drives = [
        d
        for d in drives
        if 7 <= (datetime.fromisoformat(d["date"]).date() - start_date).days < 14
    ]
    print(f"Found {len(first_week_drives)} drives in first week")
    for drive in first_week_drives:
        print(f"  • Pair {drive['pair_letter']} on {drive['date']}")

    return {
        "start_date": start_date,
        "school": school,
        "first_day_slots": first_day_slots,
        "last_day_slots": last_day_slots,
        "capacity": capacity,
        "classroom_name": classroom_name,
        "num_classes": len(classes),
        "num_drives": len(drives),
    }


@anvil.server.callable
def create_merged_schedule(classroom_name):
    """
    Create a merged view of the classroom schedule showing all slots and their assignments.
    Returns a list of daily schedules with all slots and their assignments (classes or drives).
    Vacation days are included with all slots marked as vacation.

    Args:
        classroom_name (str): Name of the classroom

    Returns:
        list: List of daily schedules with slot assignments
    """
    # Get classroom data
    classroom = app_tables.classrooms.get(classroom_name=classroom_name)
    if not classroom:
        raise ValueError(f"classroom {classroom_name} not found")

    # Get class and drive schedules
    class_schedule = classroom["class_schedule"] or []
    drive_schedule = classroom["drive_schedule"] or []

    # Create a dictionary of all dates in the classroom's date range
    start_date = classroom["start_date"]
    end_date = classroom["end_date"]
    current_date = start_date
    daily_schedules = []

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        # Create daily schedule
        day_schedule = {
            "date": date_str,
            "day": current_date.strftime("%A"),
            "week": (current_date - start_date).days // 7 + 1,
            "slots": {},
            "is_vacation": date_str in no_class_days,
        }

        # Initialize all slots
        for slot_name in LESSON_SLOTS:
            if not slot_name.startswith("break_"):
                if day_schedule["is_vacation"]:
                    # Mark all slots as vacation for vacation days
                    day_schedule["slots"][slot_name] = {
                        "type": "vacation",
                        "title": "Vacation",
                        "details": {
                            "holiday_name": no_class_days.get(date_str, "Vacation Day")
                        },
                    }
                else:
                    # Initialize as empty for non-vacation days
                    day_schedule["slots"][slot_name] = {
                        "type": None,
                        "title": None,
                        "details": None,
                    }

        # Add class assignments (only for non-vacation days)
        if not day_schedule["is_vacation"]:
            for class_slot in class_schedule:
                if class_slot["date"] == date_str:
                    day_schedule["slots"]["lesson_slot_5"] = {
                        "type": "class",
                        "title": f"Class {class_slot['class_number']}",
                        "details": {
                            "week": class_slot["week"],
                            "status": class_slot["status"],
                        },
                    }

        # Add drive assignments (only for non-vacation days)
        if not day_schedule["is_vacation"]:
            for drive_slot in drive_schedule:
                if drive_slot["date"] == date_str:
                    day_schedule["slots"][drive_slot["slot"]] = {
                        "type": "drive",
                        "title": f"Pair {drive_slot['pair_letter']}: Drives {drive_slot['drive_numbers']}",
                        "details": {
                            "week": drive_slot["week"],
                            "is_backup_slot": drive_slot["is_backup_slot"],
                            "is_weekend": drive_slot["is_weekend"],
                            "status": drive_slot["status"],
                        },
                    }

        daily_schedules.append(day_schedule)
        current_date += timedelta(days=1)

    return daily_schedules
