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
from .globals import LESSON_SLOTS

###########################################################
# General data import function to take CSV data and convert to JSON.


@anvil.server.callable
def csv_to_structured_json(csv_file):
    if isinstance(csv_file, str):
        print("CSV convert function has file")
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            data = list(reader)
    else:
        reader = csv.reader(csv_file.get_bytes().decode("utf-8").splitlines())
        data = list(reader)

    headers = data[0][1:]  # Column headers (excluding first column)
    row_headers = [row[0] for row in data[1:]]  # Row headers (first column)

    structured_data = {}
    for i, row in enumerate(data[1:], start=0):
        row_header = row_headers[i]
        row_data = {}

        for j, value in enumerate(row[1:], start=0):
            column_header = headers[j]
            row_data[column_header] = value

        structured_data[row_header] = row_data

    return structured_data


@anvil.server.callable
def convert_csv_to_json(file):
    json_payload = csv_to_structured_json(file)
    print(json_payload)
    return json_payload


# Optional: Pretty print the JSON
def print_json(json_data):
    print(json.dumps(json_data, indent=2))


# Drive schedule spoecifc import function


@anvil.server.callable
def convert_schedule_csv_to_json(csv_file):
    if isinstance(csv_file, str):
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            data = list(reader)
    else:
        content = csv_file.get_bytes().decode("utf-8")
        reader = csv.DictReader(content.splitlines())
        data = list(reader)

    structured_data = {}

    for row in data:
        # Use the "Title" field as the main key
        title = row.pop("Title", None)
        if title:
            # Add all other columns as properties
            structured_data[title] = {k: v for k, v in row.items() if k}

    return structured_data


@anvil.server.callable
def update_teen_drive_schedule(file):
    json_payload = convert_schedule_csv_to_json(file)
    current_variables = app_tables.global_variables_edit_with_care.get(version="latest")

    if current_variables:
        current_schedule = current_variables["current_teen_driving_schedule"]
        current_variables.update(
            previous_teen_driving_schedule=current_schedule,
            current_teen_driving_schedule=json_payload,
        )
        return True
    else:
        app_tables.global_variables_edit_with_care.add_row(
            version="latest", current_teen_driving_schedule=json_payload
        )
        return True


###########################################################
# Data export function to take JSON data and convert to CSV


def export_json_to_csv(json_data, filename="schedule.csv"):
    output = io.StringIO()
    writer = csv.writer(output)

    # Convert JSON to OrderedDict to preserve order
    json_data = OrderedDict(json_data)

    # Get all unique column headers
    all_headers = set()
    for _, event_data in json_data.items():
        all_headers.update(event_data.keys())
    all_headers = sorted(all_headers)
    # Write the header row
    writer.writerow(["Title"] + list(all_headers))

    # Write each item as a row
    for event_id, event_data in json_data.items():
        row = [event_id]  # Event ID (e.g., "Drive 1") as first column

        # Add data for each header
        for header in all_headers:
            row.append(event_data.get(header, ""))

        writer.writerow(row)

    # Create media object
    csv_media = anvil.BlobMedia(
        "text/csv", output.getvalue().encode("utf-8"), name=filename
    )

    app_tables.files.add_row(filename=filename, file=csv_media, file_type="CSV")


@anvil.server.callable
def convert_JSON_to_csv_and_save(json_data, filename):
    return export_json_to_csv(json_data, filename)


###########################################################
# Excel export functions


@anvil.server.callable
def sync_instructor_availability_to_sheets():
    """
    Sync instructor availability to Google Sheets.
    Creates one sheet per instructor with their weekly availability.
    Structure:
    - First row (row 0): Days of the week
    - First column (column 0): Lesson slots
    - Data grid: Availability for each slot/day combination
    """
    # Get all instructors
    instructors = app_tables.users.search(is_instructor=True)
    print(f"Found {len(instructors)} instructors")

    # Get the spreadsheet from app_files
    try:
        spreadsheet = app_files.current_availability
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
            continue

        # Get availability data
        availability = instructor_row["weekly_availability"]["weekly_availability"]
        school_prefs = instructor_row["school_preferences"]
        vacation_days = instructor_row["vacation_days"]
        print(f"Retrieved availability data for {instructor['firstName']}")

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

            # Write headers (row 0) - Days of the week
            print("Writing day headers...")
            worksheet[0, 0].value = "Slot"  # First cell is "Slot"
            for i, day in enumerate(days):
                worksheet[0, i + 1].value = day.capitalize()
            print("Day headers written")

            # Write slot names (column 0) - Lesson slots
            print("Writing slot names...")
            for i, slot in enumerate(slots):
                worksheet[i + 1, 0].value = slot
            print("Slot names written")

            # Write availability data in the grid
            print("Writing availability data...")
            for i, slot in enumerate(slots):
                for j, day in enumerate(days):
                    day_data = availability.get(day, {})
                    status = day_data.get(slot, "No")
                    worksheet[i + 1, j + 1].value = status
            print("Availability data written")

            # Add school preferences
            pref_row = len(slots) + 3
            print("Writing school preferences...")
            worksheet[pref_row, 0].value = "School Preferences:"
            worksheet[pref_row + 1, 0].value = str(school_prefs)
            print("School preferences written")

            # Add vacation days
            vac_row = len(slots) + 6
            print("Writing vacation days...")
            worksheet[vac_row, 0].value = "Vacation Days:"
            for i, vac_day in enumerate(vacation_days):
                worksheet[vac_row + 1 + i, 0].value = str(vac_day)
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


@anvil.server.callable
def export_cohort_schedule(cohort_name):
    print(cohort_name)
    """
    Export cohort schedule to Excel.
    Creates sheets for classes and drives.
    """
    # Get cohort data
    cohort = app_tables.cohorts.get(cohort_name=cohort_name)
    if not cohort:
        raise ValueError(f"Cohort {cohort_name} not found")

    # Create Excel writer
    output = io.BytesIO()
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

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name=f"{cohort_name}_schedule.xlsx",
    )

    app_tables.files.add_row(
        filename=f"{cohort_name}_schedule.xlsx", file=excel_media, file_type="Excel"
    )

    return excel_media


@anvil.server.callable
def export_merged_cohort_schedule(cohort_name):
    """
    Export merged cohort schedule to Excel.
    Creates a single sheet with days as columns and slots as rows.
    Row headers show lesson start times instead of slot names.

    Args:
        cohort_name (str): Name of the cohort to export
    """

    # Get merged schedule
    daily_schedules = app_tables.cohorts.get(cohort_name=cohort_name)[
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
                    data[slot_to_time[slot]][date_str] = slot_data["title"]
                else:
                    data[slot_to_time[slot]][date_str] = ""

        # Create DataFrame
        df = pd.DataFrame(data).T

        # Sort columns by date
        df = df.sort_index(axis=1)

        # Write to Excel
        df.to_excel(writer, sheet_name="Schedule", startrow=2)  # Start data at row 2

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

        # Format row headers (times)
        for row_num, value in enumerate(df.index.values):
            worksheet.write(row_num + 2, 0, value, time_format)

        # Set column widths
        worksheet.set_column(0, 0, 8)  # Time column
        for i in range(1, len(df.columns) + 1):
            worksheet.set_column(i, i, 12)  # Date columns

    # Create media object and save to database
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name=f"{cohort_name}_merged_schedule.xlsx",
    )

    app_tables.files.add_row(
        filename=f"{cohort_name}_merged_schedule.xlsx",
        file=excel_media,
        file_type="Excel",
    )

    return excel_media
