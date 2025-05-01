"""
Export Utilities Module

Handles Excel exports for:
1. Instructor availability
2. Cohort schedules
"""

import anvil.files
from anvil.files import data_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime, timedelta, date
import pandas as pd
from io import BytesIO


@anvil.server.callable
def export_instructor_availability():
    """
    Export instructor availability to Excel.
    Creates one sheet per instructor with their weekly availability.
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Create Excel writer
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for instructor in instructors:
            # Get instructor schedule
            instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
            if not instructor_row:
                continue

            # Get availability data
            availability = instructor_row["weekly_availability"]["weekly_availability"]
            school_prefs = instructor_row["school_preferences"]
            vacation_days = instructor_row["vacation_days"]

            # Create DataFrame for this instructor
            days = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
            slots = [
                "lesson_slot_1",
                "lesson_slot_2",
                "lesson_slot_3",
                "lesson_slot_4",
                "lesson_slot_5",
            ]

            data = []
            for day in days:
                day_data = availability.get(day, {})
                for slot in slots:
                    status = day_data.get(slot, "No")
                    data.append(
                        {"Day": day.capitalize(), "Slot": slot, "Status": status}
                    )

            df = pd.DataFrame(data)
            df_pivot = df.pivot(index="Slot", columns="Day", values="Status")

            # Write to Excel
            sheet_name = f"{instructor['firstName']} {instructor['lastName']}"
            df_pivot.to_excel(writer, sheet_name=sheet_name)

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # Add formatting
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D9E1F2", "border": 1}
            )

            # Format headers
            for col_num, value in enumerate(df_pivot.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
            for row_num, value in enumerate(df_pivot.index.values):
                worksheet.write(row_num + 1, 0, value, header_format)

            # Add school preferences
            worksheet.write(len(slots) + 3, 0, "School Preferences:", header_format)
            worksheet.write(len(slots) + 4, 0, str(school_prefs))

            # Add vacation days
            worksheet.write(len(slots) + 6, 0, "Vacation Days:", header_format)
            for i, vac_day in enumerate(vacation_days):
                worksheet.write(len(slots) + 7 + i, 0, str(vac_day))

    return output.getvalue()


@anvil.server.callable
def export_cohort_schedule(cohort_name):
    """
    Export cohort schedule to Excel.
    Creates sheets for classes and drives.
    """
    # Get cohort data
    cohort = app_tables.cohorts.get(cohort_name=cohort_name)
    if not cohort:
        raise ValueError(f"Cohort {cohort_name} not found")

    # Create Excel writer
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Classes sheet
        if cohort["class_schedule"]:
            classes_df = pd.DataFrame(cohort["class_schedule"])
            classes_df.to_excel(writer, sheet_name="Classes", index=False)

        # Drives sheet
        if cohort["drive_schedule"]:
            drives_df = pd.DataFrame(cohort["drive_schedule"])
            drives_df.to_excel(writer, sheet_name="Drives", index=False)

        # Get workbook
        workbook = writer.book

        # Format classes sheet
        if cohort["class_schedule"]:
            worksheet = writer.sheets["Classes"]
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D9E1F2", "border": 1}
            )

            # Format headers
            for col_num, value in enumerate(classes_df.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Format drives sheet
        if cohort["drive_schedule"]:
            worksheet = writer.sheets["Drives"]
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D9E1F2", "border": 1}
            )

            # Format headers
            for col_num, value in enumerate(drives_df.columns.values):
                worksheet.write(0, col_num, value, header_format)

    return output.getvalue()
