"""
Tool and shared services
"""
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import json
import io
import anvil.media
from collections import OrderedDict
import pandas as pd
from datetime import datetime, timedelta
from .globals import LESSON_SLOTS, AVAILABILITY_MAPPING



###########################################################
# Google Sheet functions
# Keep for testing sheets
# ⚠️ REMEMBER Sheet headers must be pre-defined and remain static to allow coirrect writing
# Otherwise the save to sheets fails silently with no error message
@anvil.server.callable
def sanity_check_write():
    sheet = app_files.drive_schedule_test
    ws = sheet["Sheet1"]

    ws.rows[:] = []


# ➡️ Not active but keep for adaptation later if sheets is an option
@anvil.server.background_task
def sync_instructor_availability_to_sheets():
    """
    Sync instructor availability to Google Sheets.
    Creates one sheet per instructor with their weekly availability.
    Structure:
    - First row (row 1): Days of the week
    - First column (column 1): Lesson slots
    - Data grid: Availability for each slot/day combination
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)
    print(f"Found {len(instructors)} instructors")
    for inst in instructors:
        print(f"Instructor found: {inst['firstName']} {inst['surname']}")

    # Get the spreadsheet from app_files
    try:
        spreadsheet = app_files.availability_new
        print("Successfully accessed spreadsheet")
        print(f"Available worksheets: {list(spreadsheet.worksheets)}")
    except Exception as e:
        print(f"Error accessing spreadsheet: {str(e)}")
        return False

    # Process each instructor
    for instructor in instructors:
        print(
            f"\nProcessing instructor: {instructor['firstName']} {instructor['surname']}"
        )

        # Get instructor schedule
        instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_row:
            print(f"No schedule found for {instructor['firstName']}")
            print(f"Checking instructor data: {instructor}")
            continue

        # Get availability data
        availability = instructor_row["weekly_availability"]["weekly_availability"]
        school_prefs = instructor_row["school_preferences"]
        vacation_days = instructor_row["vacation_days"]
        print(f"Retrieved availability data for {instructor['firstName']}")
        print(f"Vacation days data: {vacation_days}")

        # Create sheet name (using underscore to avoid spaces)
        sheet_name = f"{instructor['firstName']}_{instructor['surname']}"
        print(f"Attempting to access worksheet: {sheet_name}")

        # Get worksheet
        try:
            worksheet = spreadsheet[sheet_name]
            print(f"Successfully accessed worksheet: {sheet_name}")
        except Exception as e:
            print(f"Error accessing worksheet {sheet_name}: {str(e)}")
            continue

        try:
            # Prepare data
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

            # Clear existing data by deleting rows
            print("Clearing existing data...")
            try:
                rows = list(worksheet.rows)
                if rows:
                    print(f"Found {len(rows)} rows to delete")
                    for row in rows:
                        row.delete()
                    print("Existing data cleared")
                else:
                    print("No existing rows to delete")
            except TypeError:
                print("No existing rows to delete (empty sheet)")

            # Prepare all rows at once
            print("Preparing data rows...")
            rows = []

            # Header row
            header_row = {"Slot": "Slot"}
            for day in days:
                header_row[day.capitalize()] = day.capitalize()
            rows.append(header_row)

            # Availability rows
            for slot in slots:
                row_data = {"Slot": slot}
                for day in days:
                    day_data = availability.get(day, {})
                    status = day_data.get(slot, "No")
                    row_data[day.capitalize()] = status
                rows.append(row_data)

            # Add all rows one by one
            print("Writing all rows...")
            for row in rows:
                worksheet.add_row(**row)
            print("Main data written")

            # Add school preferences
            print("Writing school preferences...")
            worksheet.add_row(**{"Slot": "School Preferences:"})
            worksheet.add_row(**{"Slot": str(school_prefs)})
            print("School preferences written")

            # Add vacation days
            print("Writing vacation days...")
            worksheet.add_row(**{"Slot": "Vacation Days:"})
            if vacation_days and "vacation_days" in vacation_days:
                print(vacation_days["vacation_days"])
                for vac_day in vacation_days["vacation_days"]:
                    # Format: "Reason: Personal Day (2025-05-06 to 2025-05-07)"
                    vac_text = f"{vac_day['reason']} ({vac_day['start_date']} to {vac_day['end_date']})"
                    worksheet.add_row(**{"Slot": vac_text})
            else:
                worksheet.add_row(**{"Slot": "No vacation days scheduled"})
            print("Vacation days written")

            print(
                f"Successfully updated availability for {instructor['firstName']} {instructor['surname']}"
            )
        except Exception as e:
            print(f"Error writing data to worksheet: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
            continue

    return True

###########################################################
# Excel functions
# ✅ Core function - keep
@anvil.server.callable
def export_instructor_availability():
    """
    Export instructor availability to Excel.
    Creates one sheet per instructor with their weekly availability.
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Create Excel writer
    output = io.BytesIO()
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
            sheet_name = f"{instructor['firstName']} {instructor['surname']}"
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

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name="instructor_availability.xlsx",
    )

    app_tables.files.add_row(
        filename="instructor_availability.xlsx", file=excel_media, file_type="Excel"
    )

    return excel_media

# ✅ Core function - keep
@anvil.server.callable
def export_instructor_eight_monthavailability():
    """
    Export instructor availability to Excel.
    Creates one sheet per instructor with their weekly availability.
    Dates as columns, lessons as rows.
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)

    # Create Excel writer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for instructor in instructors:
            # Get instructor schedule
            instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
            if not instructor_row:
                continue

            # Get availability data
            availability = instructor_row["current_seven_month_availability"]

            # Create DataFrame for this instructor
            slots = [
                "lesson_slot_1",
                "lesson_slot_2",
                "lesson_slot_3",
                "lesson_slot_4",
                "lesson_slot_5",
            ]

            # Get all dates (they are the top-level keys)
            all_dates = sorted(list(availability.keys()))

            # Create data structure
            data = []
            for slot in slots:
                row_data = {"Lesson": slot}
                for date in all_dates:
                    # Get the value directly from the availability data
                    value = availability[date].get(slot, 0)
                    # Convert numeric value to text using reverse mapping
                    text_value = next(
                        (k for k, v in AVAILABILITY_MAPPING.items() if v == value),
                        "Unknown",
                    )
                    row_data[date] = text_value
                data.append(row_data)

            df = pd.DataFrame(data)
            df.set_index("Lesson", inplace=True)

            # Print a sample of the DataFrame for logging
            print(f"\nDataFrame sample for {instructor['firstName']}:")
            print(df.head(2))  # Show first 2 rows
            print("\nColumns (dates):")
            print(df.columns[:5])  # Show first 5 dates

            # Write to Excel
            sheet_name = f"{instructor['firstName']} {instructor['surname']}"
            df.to_excel(writer, sheet_name=sheet_name)

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name="instructor_availability.xlsx",
    )

    app_tables.files.add_row(
        filename="instructor_availability_240Days.xlsx", file=excel_media, file_type="Excel"
    )

    return excel_media

# ✅ Core function - keep
@anvil.server.callable
def export_classroom_schedule(classroom_name):
    print(classroom_name)
    """
    Export classroom schedule to Excel.
    Creates sheets for classes and drives.
    """
    # Get classroom data
    classroom = app_tables.classrooms.get(classroom_name=classroom_name)
    if not classroom:
        raise ValueError(f"classroom {classroom_name} not found")

    # Create Excel writer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Classes sheet
        if classroom["class_schedule"]:
            classes_df = pd.DataFrame(classroom["class_schedule"])
            classes_df.to_excel(writer, sheet_name="Classes", index=False)

        # Drives sheet
        if classroom["drive_schedule"]:
            drives_df = pd.DataFrame(classroom["drive_schedule"])
            drives_df.to_excel(writer, sheet_name="Drives", index=False)

        # Get workbook
        workbook = writer.book

        # Format classes sheet
        if classroom["class_schedule"]:
            worksheet = writer.sheets["Classes"]
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D9E1F2", "border": 1}
            )

            # Format headers
            for col_num, value in enumerate(classes_df.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Format drives sheet
        if classroom["drive_schedule"]:
            worksheet = writer.sheets["Drives"]
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#D9E1F2", "border": 1}
            )

            # Format headers
            for col_num, value in enumerate(drives_df.columns.values):
                worksheet.write(0, col_num, value, header_format)

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name=f"{classroom_name}_schedule.xlsx",
    )

    app_tables.files.add_row(
        filename=f"{classroom_name}_schedule.xlsx", file=excel_media, file_type="Excel"
    )

    return excel_media

# ✅ Core function - keep
@anvil.server.callable
def export_merged_classroom_schedule(classroom_name):
    """
    Export merged classroom schedule to Excel.
    Creates a single sheet with days as columns and slots as rows.
    Row headers show lesson start times instead of slot names.

    Args:
        classroom_name (str): Name of the classroom to export
    """

    # Get merged schedule
    has_instructor = False
    daily_schedules = app_tables.classrooms.get(classroom_name=classroom_name)[
        "complete_schedule"
    ]

    # Create Excel writer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Create DataFrame with slots as index and days as columns
        data = {}
        slot_order = [
            slot for slot in LESSON_SLOTS.keys() if not slot.startswith("break_")
        ]

        # Create slot to time mapping
        slot_to_time = {slot: LESSON_SLOTS[slot]["start_time"] for slot in slot_order}

        # Initialize data structure
        for slot in slot_order:
            data[slot_to_time[slot]] = {}  # Use time as key instead of slot name

        # Fill in the data
        for day in daily_schedules:
            date_str = day["date"]
            for slot, slot_data in day["slots"].items():
                if slot_data["type"] == "vacation":
                    # Use the holiday name from details
                    data[slot_to_time[slot]][date_str] = slot_data["details"][
                        "holiday_name"
                    ]
                elif slot_data["type"]:
                    # Add instructor name to title if it exists
                    title = slot_data["title"]

                    if "instructor" in slot_data:
                        title = f"{title} | Inst: {slot_data['instructor']}"
                        has_instructor = True
                    data[slot_to_time[slot]][date_str] = title
                else:
                    data[slot_to_time[slot]][date_str] = ""
                  
        if has_instructor:
          filename = f"{classroom_name}_merged_schedule_lessons_instructors.xlsx"
        else:
          filename = f"{classroom_name}_merged_schedule_lessons.xlsx"
        # Create DataFrame
        df = pd.DataFrame(data).T

        # Sort columns by date
        df = df.sort_index(axis=1)

        # Format the index (times) to be more readable
        df.index = [
            datetime.strptime(t, "%H:%M").strftime("%I:%M %p").lstrip("0")
            for t in df.index
        ]

        # Write to Excel without headers since we write them manually
        df.to_excel(
            writer, sheet_name="Schedule", startrow=2, header=False
        )  # Start data at row 2

        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets["Schedule"]

        # Add formatting
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9E1F2", "border": 1, "align": "center"}
        )

        date_format = workbook.add_format(
            {"num_format": "yyyy-mm-dd", "align": "center"}
        )

        cell_format = workbook.add_format({"align": "center", "valign": "vcenter","text_wrap": True, "border": 1})


        time_format = workbook.add_format(
            {"bold": True, "bg_color": "#F2F2F2", "border": 1, "align": "center"}
        )

        # Write headers
        worksheet.write(0, 0, "DATE", header_format)
        worksheet.write(1, 0, "DAY", header_format)

        # Format headers (dates)
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num + 1, value, header_format)
            # Add day of week below date
            date_obj = datetime.strptime(value, "%Y-%m-%d")
            worksheet.write(1, col_num + 1, date_obj.strftime("%A"), header_format)

        # Format the time column (first column of data)
        worksheet.set_column(0, 0, 8, time_format)  # Time column

        # Set column widths for date columns
        for i in range(1, len(df.columns) + 1):
            worksheet.set_column(i, i, 12)  # Date columns
          
        for row_num, (index, row) in enumerate(df.iterrows(), start=2):  # Start from row 2 (after headers)
          worksheet.write(row_num, 0, index, time_format)  # First column: time slot
          for col_num, value in enumerate(row, start=1):   # Data cells
            worksheet.write(row_num, col_num, value, cell_format)

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name=f"{classroom_name}_merged_schedule.xlsx",
    )

    app_tables.files.add_row(
        filename=filename,
        file=excel_media,
        file_type="Excel",
    )

    return excel_media
