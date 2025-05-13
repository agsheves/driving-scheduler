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


# Update this to parse classroom schedules
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


# Keep these files for transfers to / fron GLOBALS
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
# Export functions
# For testing sheet access
@anvil.server.callable
def sanity_check_write():
    sheet = app_files.drive_schedule_test
    ws = sheet["Sheet1"]

    ws.rows[:] = []


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

    # Get the spreadsheet from app_files
    try:
        spreadsheet = app_files.availability_new
    except Exception as e:
        print(f"Error accessing spreadsheet: {str(e)}")
        return False

    # Process each instructor
    for instructor in instructors:
        # Get instructor schedule
        instructor_row = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_row:
            print(f"No schedule found for {instructor['firstName']}")
            continue

        # Get availability data
        availability = instructor_row["weekly_availability"]["weekly_availability"]
        school_prefs = instructor_row["school_preferences"]
        vacation_days = instructor_row["vacation_days"]

        # Create sheet name (using underscore to avoid spaces)
        sheet_name = f"{instructor['firstName']}_{instructor['surname']}"

        # Get worksheet
        try:
            worksheet = spreadsheet[sheet_name]
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
            try:
                rows = list(worksheet.rows)
                if rows:
                    for row in rows:
                        row.delete()
            except TypeError:
                pass

            # Prepare all rows at once
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
            for row in rows:
                worksheet.add_row(**row)

            # Add school preferences
            worksheet.add_row(**{"Slot": "School Preferences:"})
            worksheet.add_row(**{"Slot": str(school_prefs)})

            # Add vacation days
            worksheet.add_row(**{"Slot": "Vacation Days:"})
            if vacation_days and "vacation_days" in vacation_days:
                for vac_day in vacation_days["vacation_days"]:
                    # Format: "Reason: Personal Day (2025-05-06 to 2025-05-07)"
                    vac_text = f"{vac_day['reason']} ({vac_day['start_date']} to {vac_day['end_date']})"
                    worksheet.add_row(**{"Slot": vac_text})
            else:
                worksheet.add_row(**{"Slot": "No vacation days scheduled"})

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
                    # Get the time range for this slot
                    slot_info = LESSON_SLOTS[slot]
                    time_range = f"{slot_info['start_time']}-{slot_info['end_time']}"
                    data.append(
                        {"Day": day.capitalize(), "Slot": time_range, "Status": status}
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
                start = format_time_12hr(LESSON_SLOTS[slot]['start_time'])
                end = format_time_12hr(LESSON_SLOTS[slot]['end_time'])
                row_data = {"Lesson": f"{slot} ({start}–{end})"}
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

            # Write to Excel
            sheet_name = f"{instructor['firstName']} {instructor['surname']}"
            df.to_excel(writer, sheet_name=sheet_name)

    # Create media object and save to database
    today = datetime.today().strftime('%B_%d_%Y')
    filename = f"instructor_availability_240Days_{today}.xlsx"
    excel_media = anvil.BlobMedia(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.getvalue(),
        name=filename,
    )

    app_tables.files.add_row(
        filename=filename,
        file=excel_media,
        file_type="Excel",
    )

    if excel_media:
      result = True
      return result, filename
    else:
      result = "error"
      filename = "n/a"
      return result, filename


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
    filename=f"{classroom_name}_schedule.xlsx"
    app_tables.files.add_row(
        filename=filename,
        file=excel_media,
        file_type="Excel"
    )
    results_message = "Download created successfully"

    return filename, results_message


def format_time_12hr(t):
  return datetime.strptime(t, "%H:%M").strftime("%-I:%M %p")

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

        cell_format = workbook.add_format(
            {"align": "center", "valign": "vcenter", "text_wrap": True, "border": 1}
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

        # Format the time column (first column of data)
        worksheet.set_column(0, 0, 8, time_format)  # Time column

        # Set column widths for date columns
        for i in range(1, len(df.columns) + 1):
            worksheet.set_column(i, i, 12)  # Date columns

        for row_num, (index, row) in enumerate(
            df.iterrows(), start=2
        ):  # Start from row 2 (after headers)
            worksheet.write(row_num, 0, index, time_format)  # First column: time slot
            for col_num, value in enumerate(row, start=1):  # Data cells
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


@anvil.server.callable
def import_instructor_availability_fromCSV(csv_file):
    """
    Import instructor availability from CSV and save to instructor record.
    CSV format: One row per instructor with 35 columns (7 days × 5 slots)
    Row header format: instructor_name_type (e.g., 'john_term' or 'john_vacation')
    """
    # Read CSV data
    if isinstance(csv_file, str):
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            data = list(reader)
    else:
        reader = csv.reader(csv_file.get_bytes().decode("utf-8").splitlines())
        data = list(reader)

    # Get headers and remove first column (instructor name)
    headers = data[0][1:]

    # Process each instructor row
    for row in data[1:]:
        # Get instructor name and type from first column
        instructor_id = row[0]
        if "_" not in instructor_id:
            print(f"Skipping invalid instructor ID format: {instructor_id}")
            continue

        instructor_name, schedule_type = instructor_id.split("_")
        if schedule_type not in ["term", "vacation"]:
            print(f"Skipping invalid schedule type: {schedule_type}")
            continue

        # Find instructor in database
        instructor = app_tables.users.get(firstName=instructor_name)
        if not instructor:
            print(f"Instructor not found: {instructor_name}")
            continue

        # Get or create instructor schedule record
        instructor_schedule = app_tables.instructor_schedules.get(instructor=instructor)
        if not instructor_schedule:
            instructor_schedule = app_tables.instructor_schedules.add_row(
                instructor=instructor
            )

        # Parse availability data into JSON structure
        availability_data = {"weekly_availability": {}}
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

        for i, day in enumerate(days):
            day_slots = {}
            for slot in range(5):
                col_idx = (i * 5) + slot
                if col_idx < len(row[1:]):  # Ensure we don't go out of bounds
                    value = row[
                        col_idx + 1
                    ]  # +1 because first column is instructor name
                    day_slots[f"lesson_slot_{slot + 1}"] = value
            availability_data["weekly_availability"][day] = day_slots

        # Save to appropriate field based on schedule type
        if schedule_type == "term":
            instructor_schedule.update(weekly_availability=availability_data)
        else:  # vacation
            instructor_schedule.update(vacation_availability=availability_data)

        print(f"Updated {schedule_type} availability for {instructor_name}")

    return True


@anvil.server.callable
def add_new_instructor():
    instructors = app_tables.users.search(is_instructor=True)
    for instructor in instructors:
        is_listed = app_tables.instructor_schedules.get(instructor=instructor)
        if is_listed is True:
            print("already listed")
        else:
            app_tables.instructor_schedules.add_row(instructor=instructor)


def fix_slot_names(data):
    """
    Recursively replace 'time_slot' with 'lesson_slot' in the availability data structure.
    """
    if isinstance(data, dict):
        return {
            k.replace("time_slot", "lesson_slot"): fix_slot_names(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [fix_slot_names(item) for item in data]
    else:
        return data


@anvil.server.callable
def fix_instructor_slot_names():
    """
    Fix slot names in all instructor schedules.
    """
    instructors = app_tables.users.search(is_instructor=True)
    for instructor in instructors:
        instructor_schedule = app_tables.instructor_schedules.get(instructor=instructor)
        if instructor_schedule:
            # Fix term availability
            if instructor_schedule["weekly_availability_term"]:
                fixed_term = fix_slot_names(
                    instructor_schedule["weekly_availability_term"]
                )
                instructor_schedule.update(weekly_availability_term=fixed_term)

            print(f"Fixed slot names for {instructor['firstName']}")

    return True
