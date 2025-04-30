"""
Cohort Builder Module

Handles creation and scheduling of driving school cohorts.
"""

import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, timedelta, date
from .globals import LESSON_SLOTS

# Schools are referenced by their abbreviation found in app_tables / schools / abbreviation

# Constants
STUDENTS_PER_DRIVE = 2
MAX_COHORT_SIZE = 30
BUFFER_PERCENTAGE = 0.9
MIN_COURSE_LENGTH = 42  # cohorts must run for over 42 calendar days to allow sufficient time to sequence all activities.
CLASS_DAYS = ["Monday", "Wednedsay", "Friday"]

# Test data for no_class_days if table is empty
no_class_days_test = {
    "2025-01-01": "New Year's Day",
    "2025-05-01": "May Day Test",
    "2025-05-27": "Memorial Day",
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
def get_available_days(start_date):
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

    # Get holidays from the database
    holidays = [
        {"date": datetime.strptime(date_str, "%Y-%m-%d").date(), "name": name}
        for date_str, name in no_class_days.items()
    ]

    holiday_dates = {h["date"] for h in holidays}

    # Check dates until we have enough available calendar days or hit max search window
    days_checked = 0
    max_days_to_check = 90  # Look up to ~3 months ahead

    while len(available_days) < MIN_COURSE_LENGTH and days_checked < max_days_to_check:
        if current_date not in holiday_dates:
            available_days.append(current_date)
        current_date += timedelta(days=1)
        days_checked += 1

    # Check if we found enough available days
    if len(available_days) < MIN_COURSE_LENGTH:
        days_short = MIN_COURSE_LENGTH - len(available_days)
        raise ValueError(
            f"Could not find enough available days. Need {days_short} more days to meet minimum course length of {MIN_COURSE_LENGTH} days"
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
        instructor_availability = instructor_row["weekly_availability"][
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
def calculate_weekly_capacity(start_date, school):
    """
    Calculate the weekly capacity based on available drive slots,
    taking into account instructor availability, vacations, and school preferences.

    Args:
        start_date (date): Start date of the program
        school (str): School abbreviation (e.g., 'HSS', 'NHS') from app_tables/schools/abbreviation

    Returns:
        dict: Contains weekly capacity information
    ✅ This has been tested and function works as expected
    BUT!
    ⚠️ Need to do manual comparison to check exact results.
    """
    available_days = get_available_days(start_date)

    # Group days by week
    weekly_days = {}
    for day in available_days:
        week_num = (day - start_date).days // 7 + 1
        if week_num not in weekly_days:
            weekly_days[week_num] = []
        weekly_days[week_num].append(day)

    # Calculate drive slots per week
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
    max_students = min(max_weekly_slots * STUDENTS_PER_DRIVE, MAX_COHORT_SIZE)

    weekly_slots_serialized = {str(k): v for k, v in weekly_slots.items()}

    return {
        "weekly_slots": weekly_slots_serialized,
        "max_weekly_slots": max_weekly_slots,
        "avg_weekly_slots": avg_weekly_slots,
        "max_students": max_students,
    }


@anvil.server.callable
def generate_cohort_name(school, start_date):
    """
    Generate cohort name in format YEAR-SEQUENCENUMBER-SCHOOL_ABBREVIATION
    Example: 2025-11-HSS
    Also creates the cohort record in the database
    ✅ This has been tested and works as designed
    """
    year = start_date.year
    # Get next sequence number for this year
    existing_cohorts = app_tables.cohorts.search(school=school)
    sequence = len(existing_cohorts) + 1
    full_name = f"{year}-{sequence:02d}-{school}"

    # Calculate end date (6 weeks from start)
    end_date = start_date + timedelta(weeks=6)

    # Determine status
    today = datetime.now().date()
    status = "planned" if start_date > today else "active"

    # Create cohort record
    app_tables.cohorts.add_row(
        cohort_name=full_name,
        start_date=start_date,
        end_date=end_date,
        status=status,
        school=school,
        sequence=sequence,
    )

    return full_name


@anvil.server.callable
def create_ghost_students(cohort_name, num_students):
    """
    Create ghost student records for the cohort
    Example IDs: 2025-11-HSS-student01
    ⚠️ Needs testing
    """
    students = []
    for i in range(1, num_students + 1):
        student_id = f"{cohort_name}-student{i:02d}"
        students.append(student_id)
    cohort_record = app_tables.cohorts.search(cohort_name=cohort_name)
    cohort_record(student_list=students)
    return students


@anvil.server.callable
def schedule_classes(cohort_name, start_date, num_students):
    """
    Schedule classes for the cohort.
    Classes must be on specific days of the week as defined in CLASS_DAYS.
    Returns a simplified object format suitable for table storage.
    """
    # Verify start_date is Monday
    if start_date.weekday() != 0:  # 0 is Monday
        print(
            f"Warning: Start date {start_date} is not a Monday. This may cause scheduling issues."
        )

    # Get available days
    available_days = get_available_days(start_date)

    # Create class schedule
    class_schedule = []
    current_week = 1
    current_class = 1

    # Map of class numbers to their required day of week (0=Monday, 6=Sunday)
    class_day_map = {
        1: 0,  # Monday
        2: 2,  # Wednesday
        3: 4,  # Friday
        4: 1,  # Tuesday
        5: 3,  # Thursday
        6: 0,  # Monday
        7: 2,  # Wednesday
        8: 4,  # Friday
        9: 1,  # Tuesday
        10: 3,  # Thursday
        11: 0,  # Monday
        12: 2,  # Wednesday
        13: 4,  # Friday
        14: 1,  # Tuesday
        15: 3,  # Thursday
    }

    # Schedule each class
    while current_class <= 15:
        # Calculate the target date based on week and required day
        required_day = class_day_map[current_class]
        week_offset = (current_week - 1) * 7
        target_date = start_date + timedelta(days=week_offset + required_day)

        # Find the next available date that matches the required day of week
        class_date = None
        for day in available_days:
            if day >= target_date and day.weekday() == required_day:
                class_date = day
                break

        if class_date is None:
            print(f"Warning: Could not find available date for Class {current_class}")
            break

        # Create simplified class slot object
        class_slot = {
            "class_number": current_class,
            "date": class_date.isoformat(),  # Convert date to string for storage
            "week": current_week,
            "day": class_date.strftime("%A"),
            "status": "scheduled",
        }
        class_schedule.append(class_slot)

        # Move to next class
        current_class += 1
        if current_class % 3 == 1:  # Start new week after every 3 classes
            current_week += 1

    # Store the schedule in the cohort table
    cohort_data_row = app_tables.cohorts.get(cohort_name=cohort_name)
    if cohort_data_row:
        cohort_data_row.update(class_schedule=class_schedule)

    return class_schedule


@anvil.server.callable
def schedule_drives(cohort_name, start_date, num_students):
    """
    Schedule drives (1 per week for weeks 2-6)
    Implements conflict resolution logic:
    1. Try same day, different time
    2. Use backup slots (Tuesday/Thursday evening, Sunday)
    3. Move to next week as last resort
    Uses predefined backup slots and checks for vacation days
    """
    # Get available days and instructor availability
    available_days = get_available_days(start_date)
    num_pairs = num_students // 2

    # Initialize drive schedule
    drives = []

    # Get lesson slots and define backup slots
    lesson_slots = LESSON_SLOTS
    backup_slots = {
        "Tuesday": "lesson_slot_5",
        "Thursday": "lesson_slot_5",
        "Sunday": "lesson_slot_1",
    }

    # Define primary slots (all slots except backup slots)
    primary_slots = {}
    for slot in lesson_slots:
        # Changed to get the first item in list - make sure this is correct
        day = slot[0]
        if slot not in backup_slots.values():
            if day not in primary_slots:
                primary_slots[day] = []
            primary_slots[day].append(slot)

    # Track used backup slots
    used_backup_slots = {day: [] for day in backup_slots.keys()}

    # Get company vacation days
    vacation_days = [
        datetime.strptime(date_str, "%Y-%m-%d").date()
        for date_str in no_class_days.keys()
    ]

    # Schedule drives for weeks 2-6
    for week in range(5):
        week_start = start_date + timedelta(days=7 * (week + 1))  # Start from week 2

        # Get available days for this week, excluding vacation days
        week_days = [
            day
            for day in available_days
            if week_start <= day < week_start + timedelta(days=7)
            and day not in vacation_days
        ]

        for pair in range(num_pairs):
            drive_letter = chr(65 + pair)  # A, B, C, etc.

            # Try to schedule on primary day first
            primary_date = None
            primary_slot = None

            # First try primary slots
            for day in week_days:
                day_name = day.strftime("%A")
                if day_name in primary_slots:
                    # Try each time slot for this day
                    for slot in primary_slots[day_name]:
                        if slot not in used_backup_slots.get(day_name, []):
                            primary_date = day
                            primary_slot = slot
                            break
                    if primary_date:
                        break

            # If primary slot not available, try backup slots
            if primary_date is None:
                for day in week_days:
                    day_name = day.strftime("%A")
                    if day_name in backup_slots:
                        backup_slot = backup_slots[day_name]
                        if backup_slot not in used_backup_slots.get(day_name, []):
                            primary_date = day
                            primary_slot = backup_slot
                            used_backup_slots[day_name].append(backup_slot)
                            break

            # If still no slot found, move to next week
            if primary_date is None:
                next_week_start = week_start + timedelta(days=7)
                next_week_days = [
                    day
                    for day in available_days
                    if next_week_start <= day < next_week_start + timedelta(days=7)
                    and day not in vacation_days
                ]
                if next_week_days:
                    primary_date = next_week_days[0]
                    # Try to find a slot for this day
                    day_name = primary_date.strftime("%A")
                    if day_name in primary_slots:
                        primary_slot = primary_slots[day_name][0]
                    elif day_name in backup_slots:
                        primary_slot = backup_slots[day_name]
                        used_backup_slots[day_name].append(primary_slot)

            if primary_date and primary_slot:
                drive_slot = {
                    "cohort": cohort_name,
                    "drive_letter": drive_letter,
                    "date": primary_date.isoformat(),
                    "slot": primary_slot,
                    "week": week + 2,  # Weeks 2-6
                    "is_backup_slot": primary_date.strftime("%A") in backup_slots,
                    "is_weekend": primary_date.weekday() in [5, 6],
                    "instructor": None,  # To be assigned
                    "status": "scheduled",
                }
                drives.append(drive_slot)

    # Store the schedule in the cohort table
    cohort_data_row = app_tables.cohorts.get(cohort_name=cohort_name)
    if cohort_data_row:
        cohort_data_row.update(drive_schedule=drives)

    return drives


@anvil.server.callable
def create_cohort(school, start_date):
    """
    Main function to create a new cohort

    Args:
        school (str): School abbreviation (e.g., 'HSS', 'NHS') from app_tables/schools/abbreviation
        start_date (date): Start date of the program

    Returns:
        dict: Cohort information including name, students, classes, and drives
    """
    print(f"\nCreating new cohort for {school} starting {start_date}")

    # 1. Generate cohort name
    cohort_name = generate_cohort_name(school, start_date)
    print(f"Cohort name: {cohort_name}")

    # 2. Calculate max students based on instructor availability
    capacity = calculate_weekly_capacity(start_date, school)
    num_students = min(capacity["max_students"], MAX_COHORT_SIZE)
    print(f"Max students: {num_students}")

    # 3. Create ghost students
    students = create_ghost_students(cohort_name, num_students)
    print(f"Created {len(students)} student records")

    # 4. Schedule classes
    classes = schedule_classes(cohort_name, start_date, num_students)
    print(f"Scheduled {len(classes)} classes")

    # 5. Schedule drives
    drives = schedule_drives(cohort_name, start_date, num_students)
    print(f"Scheduled {len(drives)} drives")

    return {
        "cohort_name": cohort_name,
        "num_students": num_students,
        "students": students,
        "classes": classes,
        "drives": drives,
    }


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

    print("\n=== Testing Cohort Builder Functions ===")
    print(f"Start Date: {start_date}")
    print(f"School: {school}")

    # Test get_available_days
    print("\n1. Testing get_available_days...")
    available_days = get_available_days(start_date)
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
    capacity = calculate_weekly_capacity(start_date, school)
    print(f"Weekly slots: {capacity['weekly_slots']}")
    print(f"Max weekly slots: {capacity['max_weekly_slots']}")
    print(f"Maximum students: {capacity['max_students']}")

    # Test cohort creation
    print("\n4. Testing cohort creation...")
    cohort_name = generate_cohort_name(school, start_date)
    print(f"Generated cohort name: {cohort_name}")

    # Test class scheduling
    print("\n5. Testing class scheduling...")
    classes = schedule_classes(cohort_name, start_date, capacity["max_students"])
    print(f"Scheduled {len(classes)} classes")
    print("First week classes:")
    for class_slot in classes[:3]:
        print(f"  • Class {class_slot['class_number']} on {class_slot['date']}")

    # Test drive scheduling
    print("\n6. Testing drive scheduling...")
    drives = schedule_drives(cohort_name, start_date, capacity["max_students"])
    print(f"Scheduled {len(drives)} drives")
    print("First week drives:")
    first_week_drives = [d for d in drives if datetime.fromisoformat(d["date"]).date() - start_date < timedelta(days=7)]
    for drive in first_week_drives:
        print(f"  • Drive {drive['drive_letter']} on {drive['date']}")

    return {
        "start_date": start_date,
        "school": school,
        "first_day_slots": first_day_slots,
        "last_day_slots": last_day_slots,
        "capacity": capacity,
        "cohort_name": cohort_name,
        "num_classes": len(classes),
        "num_drives": len(drives),
    }
