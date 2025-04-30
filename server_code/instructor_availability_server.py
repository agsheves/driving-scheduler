"""
Instructor Availability Server Module

This module handles instructor availability processing and scheduling.
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
from .globals import LESSON_SLOTS


@anvil.server.callable
def process_instructor_availability(instructors, start_date=None):
    """Process instructor availability data and return formatted schedule.

    Args:
        instructors (list): List of instructor objects
        start_date (date): Start date for calculation (default: today)

    Returns:
        dict: Dictionary containing availability data for heatmap display
    """
    if start_date is None:
        start_date = datetime.now().date()

    all_records = []

    for instructor in instructors:
        try:
            instructor_schedule = app_tables.instructor_schedules.get(
                instructor=instructor
            )
            weekly_data = instructor_schedule["weekly_availability"]
            print("==Debug== Weekly data:", weekly_data)  # Debug print
            if weekly_data is None or weekly_data == "":
                continue
            print(f"Found data for {instructor['firstName']}: {weekly_data.keys()}")
        except (KeyError, TypeError) as e:
            weekly_data = {}
            print(f"Error getting data for {instructor['firstName']}: {e}")
            continue

        availability_mapping = {"No": 0, "Yes": 1, "Drive Only": 2, "Class Only": 3}

        days_of_week = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

        for day_index, day_name in enumerate(days_of_week):
            try:
                print("==Debug== Trying to access:", day_name)  # Debug print
                print("==Debug== Weekly data structure:", weekly_data)  # Debug print
                day_availability = weekly_data["weekly_availability"][
                    day_name
                ]  # Fixed access
                print(
                    f"Processing {day_name} for {instructor['firstName']}: {len(day_availability)} time slots"
                )
            except (KeyError, TypeError) as e:
                print(f"No data for {day_name}: {e}")
                continue

            for slot_name, status in day_availability.items():
                if slot_name in LESSON_SLOTS:
                    try:
                        value = availability_mapping.get(status, -1)

                        all_records.append(
                            {
                                "instructor": instructor["firstName"],
                                "day_index": day_index,
                                "day_name": day_name,
                                "slot": slot_name,
                                "start_time": LESSON_SLOTS[slot_name]["start_time"],
                                "end_time": LESSON_SLOTS[slot_name]["end_time"],
                                "status": status,
                                "value": value,
                            }
                        )
                    except (KeyError, TypeError) as e:
                        print(f"Error with slot {slot_name}: {e}")
                        continue

        # print(f"Added {instructor['firstName']}")

    # Process the data with pandas
    df = pd.DataFrame(all_records)

    # Debug print to see sample of the dataframe in terminal
    print(f"Total records: {len(df)}")
    print("Sample of DataFrame (first 20 records):")
    print(df.head(20))

    if df.empty:
        return None

    # Create a pivot table for the heatmap: slots vs days
    pivot_df = df.pivot_table(
        values="value",
        index=["slot", "start_time", "end_time"],
        columns=["day_name", "instructor"],
        aggfunc="first",
    )

    # Sort by start time
    pivot_df = pivot_df.sort_values(by=["start_time"], ascending=False)

    # Create flattened day-instructor labels
    flat_columns = []
    for col in pivot_df.columns:
        day, instructor = col
        flat_columns.append((day, instructor, f"{day.capitalize()} - {instructor}"))

    # Define day order
    day_order = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Sort flat columns by day first, then by instructor
    flat_columns.sort(key=lambda x: (day_order[x[0]], x[1]))

    # Extract just the formatted labels
    flat_labels = [item[2] for item in flat_columns]

    # Reorder the z-values to match the new column order
    z_values_ordered = []
    for row in pivot_df.values.tolist():
        # Create a new row with values in the correct order
        new_row = []
        for day, instructor, _ in flat_columns:
            col_idx = list(pivot_df.columns).index((day, instructor))
            new_row.append(row[col_idx])
        z_values_ordered.append(new_row)

    # Return the properly ordered data
    return {
        "z_values": z_values_ordered,
        "x_labels": flat_labels,
        "y_labels": [
            f"{slot} ({start_time}-{end_time})"
            for slot, start_time, end_time in pivot_df.index
        ],
        "instructors": [i["firstName"] for i in instructors],
    }


@anvil.server.callable
def get_max_drive_slots(date):
    """
    Calculate maximum available drive slots for a given date.
    Uses the existing process_instructor_availability function to get availability data.
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Get availability data for the week containing the date
    availability_data = process_instructor_availability(instructors, date)

    if not availability_data:
        return 0

    # Count available drive slots
    drive_slots = 0
    for slot_info in availability_data["y_labels"]:
        # Check if any instructor is available for this slot
        slot_index = availability_data["y_labels"].index(slot_info)
        for instructor_availability in availability_data["z_values"][slot_index]:
            if instructor_availability in [1, 2]:  # 1 means "Yes", 2 means "Drive Only"
                drive_slots += 1
                break  # Count each slot only once if at least one instructor is available

    return drive_slots


@anvil.server.callable
def get_max_class_slots(date):
    """
    Calculate maximum available class slots for a given date.
    Uses the existing process_instructor_availability function to get availability data.
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Get availability data for the week containing the date
    availability_data = process_instructor_availability(instructors, date)

    if not availability_data:
        return 0

    # Count available class slots
    class_slots = 0
    for slot_info in availability_data["y_labels"]:
        # Check if any instructor is available for this slot
        slot_index = availability_data["y_labels"].index(slot_info)
        for instructor_availability in availability_data["z_values"][slot_index]:
            if instructor_availability in [1, 3]:  # 1 means "Yes", 3 means "Class Only"
                class_slots += 1
                break  # Count each slot only once if at least one instructor is available

    return class_slots
