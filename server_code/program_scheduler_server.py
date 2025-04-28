"""
Program Scheduler Server Module

This module handles the creation and management of driving school program schedules.
It coordinates class scheduling, drive scheduling, and instructor availability.
"""

import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import string


@anvil.server.callable
def calculate_program_schedule(start_date):
    """
    Calculate the ideal program schedule based on instructor availability.
    Returns a schedule with class and drive slots, and max cohort size.
    """
    try:
        print(f"\nStarting schedule calculation for {start_date}")

        # Calculate available drive slots for each week
        weekly_drive_slots = []

        # Week 1 - orientation and classes
        week1_start = start_date
        weekly_drive_slots.append(0)  # No drives in week 1
        print(f"Week 1 start: {week1_start}")

        # Weeks 2-6 - classes and drives
        for week_num in range(1, 6):
            week_start = start_date + timedelta(weeks=week_num)
            print(f"Week {week_num + 1} start: {week_start}")
            drive_slots = anvil.server.call("get_max_drive_slots", week_start)
            weekly_drive_slots.append(drive_slots)

        print(f"Weekly drive slots: {weekly_drive_slots}")

        # Calculate max students based on drive capacity
        students_per_slot = 2
        if len(weekly_drive_slots) < 2:
            raise ValueError("Not enough weeks with drive slots available")

        max_students = min(weekly_drive_slots[1:]) * students_per_slot
        print(f"Max students: {max_students}")

        # Create drive pairs (A, B, C, etc.)
        drive_pairs = list(string.ascii_uppercase[: max_students // 2])
        print(f"Drive pairs: {drive_pairs}")

        # Generate schedule
        schedule = {
            "start_date": start_date,
            "end_date": start_date + timedelta(weeks=6),
            "max_students": max_students,
            "weekly_drive_slots": weekly_drive_slots,
            "weekly_schedule": [],
        }

        # Generate weekly schedule
        current_drive_number = 1
        current_class_number = 1

        for week_num in range(6):
            week_start = start_date + timedelta(weeks=week_num)
            print(
                f"\nGenerating schedule for week {week_num + 1} starting {week_start}"
            )

            week_schedule = {
                "week_number": week_num + 1,
                "start_date": week_start,
                "class_slots": [],
                "drive_slots": [],
            }

            # Add orientation on first day of week 1
            if week_num == 0:
                print("Adding orientation and first 3 classes")
                week_schedule["class_slots"].append("Orientation")
                for i in range(3):
                    week_schedule["class_slots"].append(f"Class {current_class_number}")
                    current_class_number += 1
            else:
                # Add 3 classes per week for weeks 2-6
                print(
                    f"Adding classes {current_class_number} to {current_class_number + 2}"
                )
                for i in range(3):
                    if current_class_number <= 15:
                        week_schedule["class_slots"].append(
                            f"Class {current_class_number}"
                        )
                        current_class_number += 1

            # Add drive slots (weeks 2-6 only)
            if week_num > 0:
                week_drive_slots = weekly_drive_slots[week_num]
                print(f"Adding {week_drive_slots} drive slots for week {week_num + 1}")

                for slot_num in range(week_drive_slots):
                    for pair in drive_pairs:
                        week_schedule["drive_slots"].append(
                            f"Drive {current_drive_number}-Pair{pair}"
                        )
                    current_drive_number += 1

            schedule["weekly_schedule"].append(week_schedule)
            print(f"Week {week_num + 1} schedule: {week_schedule}")

        print("\nFinal schedule:", schedule)
        return schedule

    except Exception as e:
        print(f"Error in calculate_program_schedule: {str(e)}")
        raise


@anvil.server.callable
def format_schedule_output(schedule):
    """
    Format the schedule as a text output for easy verification.
    Returns a formatted string suitable for a rich text box.
    """
    output = []

    # Header
    output.append("=== PROGRAM SCHEDULE ===")
    output.append(f"Start Date: {schedule['start_date']}")
    output.append(f"End Date: {schedule['end_date']}")
    output.append(f"Max Cohort Size: {schedule['max_students']} students")
    output.append(f"Total Drive Slots: {sum(schedule['weekly_drive_slots'])}")
    output.append("\n")

    # Weekly Schedule
    output.append("=== WEEKLY SCHEDULE ===")

    for week in schedule["weekly_schedule"]:
        output.append(f"\nWeek {week['week_number']} ({week['start_date']})")
        output.append("-" * 40)

        if week["class_slots"]:
            output.append("\nClasses:")
            for class_slot in week["class_slots"]:
                output.append(f"  • {class_slot}")

        if week["drive_slots"]:
            output.append("\nDrives:")
            # Group drives by number for better readability
            drive_groups = {}
            for drive_slot in week["drive_slots"]:
                drive_num = drive_slot.split("-")[0]
                if drive_num not in drive_groups:
                    drive_groups[drive_num] = []
                drive_groups[drive_num].append(drive_slot)

            for drive_num in sorted(drive_groups.keys()):
                output.append(f"  • {drive_num}:")
                for drive in sorted(drive_groups[drive_num]):
                    output.append(f"    - {drive}")

        output.append("\n")

    return "\n".join(output)


@anvil.server.callable
def test_program_schedule(start_date=None):
    """
    Test function to create and validate a program schedule.
    Args:
        start_date (date): Optional start date (defaults to next Monday)
    Returns:
        dict: Test results including schedule and validation
    """
    try:
        # If no start date provided, default to next Monday
        if start_date is None:
            today = datetime.now().date()
            days_until_monday = (7 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_monday)

        print(f"\nCreating schedule starting from {start_date}")

        # Calculate the schedule
        schedule = calculate_program_schedule(start_date)

        # Validate the schedule
        validation = validate_schedule(schedule)

        # Format the output
        schedule_text = format_schedule_output(schedule)

        return {
            "success": True,
            "start_date": start_date,
            "schedule": schedule,
            "validation": validation,
            "formatted_output": schedule_text,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "start_date": start_date}


def validate_schedule(schedule):
    """
    Validate that the schedule meets all requirements.
    Returns a dictionary of validation results.
    """
    validation = {
        "total_drives_per_student": 0,
        "total_classes_per_student": 0,
        "drive_pairs_complete": True,
        "class_sequence_valid": True,
        "errors": [],
    }

    try:
        # Count total drives per student
        drive_counts = {}
        for week in schedule["weekly_schedule"]:
            for drive_slot in week["drive_slots"]:
                pair = drive_slot.split("-Pair")[1]
                if pair not in drive_counts:
                    drive_counts[pair] = 0
                drive_counts[pair] += 1

        # Check if each pair has exactly 5 drive slots
        for pair, count in drive_counts.items():
            if count != 5:
                validation["errors"].append(
                    f"Pair {pair} has {count} drives instead of 5"
                )
                validation["drive_pairs_complete"] = False

        # Count total classes
        class_count = sum(
            len(week["class_slots"]) for week in schedule["weekly_schedule"]
        )
        validation["total_classes_per_student"] = class_count

        # Check class sequence
        expected_classes = set(range(1, 16))  # Classes 1-15
        scheduled_classes = set()
        for week in schedule["weekly_schedule"]:
            for class_slot in week["class_slots"]:
                if class_slot != "Orientation":  # Skip orientation
                    class_num = int(class_slot.split(" ")[1])
                    scheduled_classes.add(class_num)

        if scheduled_classes != expected_classes:
            validation["errors"].append(
                f"Missing classes: {expected_classes - scheduled_classes}"
            )
            validation["class_sequence_valid"] = False

        return validation

    except Exception as e:
        print(f"Error in validate_schedule: {str(e)}")
        validation["errors"].append(f"Validation error: {str(e)}")
        validation["drive_pairs_complete"] = False
        validation["class_sequence_valid"] = False
        return validation
