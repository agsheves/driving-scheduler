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
            # print("==Debug== Weekly data:", weekly_data)  # Debug print
            if weekly_data is None or weekly_data == "":
                continue
            # print(f"Found data for {instructor['firstName']}: {weekly_data.keys()}")
        except (KeyError, TypeError) as e:
            weekly_data = {}
            # print(f"Error getting data for {instructor['firstName']}: {e}")
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
                # print("==Debug== Trying to access:", day_name)  # Debug print
                # print("==Debug== Weekly data structure:", weekly_data)  # Debug print
                day_availability = weekly_data["weekly_availability"][
                    day_name
                ]  # Fixed access
                # print(
                # f"Processing {day_name} for {instructor['firstName']}: {len(day_availability)} time slots"
                # )
            except (KeyError, TypeError) as e:
                # print(f"No data for {day_name}: {e}")
                continue

            for slot_name, status in day_availability.items():
                # print(f"{slot_name}: {status}")
                if slot_name in LESSON_SLOTS:
                    try:
                        # print(
                        # "==Debug== Processing slot:",
                        # slot_name,
                        # "with status:",
                        # status,
                        # )  # Debug print
                        value = availability_mapping.get(status, -1)
                        # print("==Debug== Mapped value:", value)  # Debug print
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
    # print(f"Total records: {len(df)}")
    # print("Sample of DataFrame (first 20 records):")
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


@anvil.server.callable
def generate_capacity_report(days=180):
    """
    Generate a capacity report showing instructor availability for the next X days.

    Args:
        days (int): Number of days to report on (default: 180)

    Returns:
        str: Path to the generated Excel file
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Get vacation days
    vacation_days = app_tables.no_class_days.search()
    vacation_dict = {str(day["date"]): day["name"] for day in vacation_days}

    # Create date range
    start_date = datetime.now().date()
    date_range = [start_date + timedelta(days=x) for x in range(days)]

    # Initialize DataFrame
    df = pd.DataFrame(
        index=[i["firstName"] for i in instructors]
        + ["Total Available", "Total Booked"],
        columns=date_range,
    )

    # Get instructor schedules
    for instructor in instructors:
        try:
            instructor_schedule = app_tables.instructor_schedules.get(
                instructor=instructor
            )
            weekly_data = instructor_schedule["weekly_availability"]
            if weekly_data is None or weekly_data == "":
                continue
        except (KeyError, TypeError):
            continue

        # Process each day
        for date in date_range:
            date_str = str(date)

            # Check if it's a vacation day
            if date_str in vacation_dict:
                df.loc[instructor["firstName"], date] = f"0 - {vacation_dict[date_str]}"
                continue

            # Get day of week
            day_name = date.strftime("%A").lower()

            try:
                day_availability = weekly_data["weekly_availability"][day_name]
                available_slots = sum(
                    1
                    for status in day_availability.values()
                    if status in ["Yes", "Drive Only", "Class Only"]
                )
                df.loc[instructor["firstName"], date] = available_slots
            except (KeyError, TypeError):
                df.loc[instructor["firstName"], date] = 0

    # Calculate totals (excluding vacation days)
    for date in date_range:
        date_str = str(date)
        if date_str in vacation_dict:
            df.loc["Total Available", date] = f"0 - {vacation_dict[date_str]}"
            df.loc["Total Booked", date] = f"0 - {vacation_dict[date_str]}"
        else:
            # Sum available slots for this day
            available = df.loc[df.index[:-2], date].sum()
            df.loc["Total Available", date] = available
            df.loc["Total Booked", date] = 0  # Reserved for future use

    # Format the Excel file
    filename = f"total_availability_as_at_{start_date.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Capacity Report")

        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets["Capacity Report"]

        # Add formatting
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9E1F2", "border": 1, "align": "center"}
        )

        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num + 1, value, header_format)

        # Format row headers
        for row_num, value in enumerate(df.index.values):
            worksheet.write(row_num + 1, 0, value, header_format)

        # Set column widths
        worksheet.set_column(0, 0, 15)  # Instructor names
        for i in range(1, len(df.columns) + 1):
            worksheet.set_column(i, i, 12)  # Date columns

    return filename
