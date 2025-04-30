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

# Schools are referenced by their abbreviation found in app_tables / schools / abbreviation

# Constants
STUDENTS_PER_DRIVE = 2
MAX_COHORT_SIZE = 30
BUFFER_PERCENTAGE = 0.9

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
    """
    available_days = []
    current_date = start_date

    # Get holidays from the database
    holidays = [
        {"date": datetime.strptime(date_str, "%Y-%m-%d").date(), "name": name}
        for date_str, name in no_class_days.items()
    ]

    holiday_dates = {h["date"] for h in holidays}

    # Check 6 weeks of dates
    for _ in range(6 * 7):  # 6 weeks * 7 days
        if current_date not in holiday_dates:
            available_days.append(current_date)
        current_date += timedelta(days=1)

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
    """
    total_slots = 0
    instructors = app_tables.users.search(is_instructor=True)

    for instructor in instructors:
        instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_row:
            continue

        # Check school preferences
        school_prefs = instructor_row["school_preferences"]
        print(school_prefs)
        #print(f"Checking preferences for {instructor['firstName']}: {school_prefs}")
        if school in school_prefs.get("school_preferences", {}).get("no", []):
            #
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
    """
    year = start_date.year
    # Get next sequence number for this year
    existing_cohorts = app_tables.cohorts.search(year=year, school=school)
    sequence = len(existing_cohorts) + 1
    return f"{year}-{sequence:02d}-{school}"


@anvil.server.callable
def create_ghost_students(cohort_name, num_students):
    """
    Create ghost student records for the cohort
    Example IDs: 2025-11-HSS-student01
    """
    students = []
    for i in range(1, num_students + 1):
        student_id = f"{cohort_name}-student{i:02d}"
        students.append(student_id)
    return students


@anvil.server.callable
def schedule_classes(cohort_name, start_date, num_students):
    """
    Schedule 15 classes (3 per week for 5 weeks)
    Returns list of class schedules with instructor assignments
    """
    classes = []
    current_date = start_date
    class_number = 1

    for week in range(5):
        for _ in range(3):  # 3 classes per week
            if class_number <= 15:
                classes.append(
                    {
                        "cohort": cohort_name,
                        "class_number": class_number,
                        "date": current_date,
                        "instructor": None,  # To be assigned
                    }
                )
                class_number += 1
        current_date += timedelta(days=7)
    return classes


@anvil.server.callable
def schedule_drives(cohort_name, start_date, num_students):
    """
    Schedule drives (1 per week for weeks 2-6)
    Returns list of drive schedules with instructor assignments
    """
    drives = []
    current_date = start_date + timedelta(days=7)  # Start week 2
    num_pairs = num_students // 2

    for week in range(5):
        for pair in range(num_pairs):
            drive_letter = chr(65 + pair)  # A, B, C, etc.
            drives.append(
                {
                    "cohort": cohort_name,
                    "drive_letter": drive_letter,
                    "date": current_date,
                    "instructor": None,  # To be assigned
                }
            )
        current_date += timedelta(days=7)
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

    print("\n=== Testing Capacity Calculation Functions ===")
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

    return {
        "start_date": start_date,
        "first_day_slots": first_day_slots,
        "last_day_slots": last_day_slots,
        "capacity": capacity,
    }
