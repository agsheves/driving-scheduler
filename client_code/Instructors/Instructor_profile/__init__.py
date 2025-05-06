from ._anvil_designer import Instructor_profileTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users


class Instructor_profile(Instructor_profileTemplate):
    def __init__(self, instructorID, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        self.instructorID = instructorID
        self.instructor = app_tables.users.get(instructorID=self.instructorID)
        self.instructor_availability_row = app_tables.instructor_schedules.get(
            instructor=self.instructor
        )

        # Get lesson slots from globals
        self.lesson_slots = app_tables.global_variables_edit_with_care.get(
            version="latest"
        )["current_teen_driving_schedule"]
        self.availability_codes = app_tables.global_variables_edit_with_care.get(
            version="latest"
        )["instructor_availability_codes"]
        self.days_formatted = app_tables.global_variables_edit_with_care.get(
            version="latest"
        )["days_full"]

        # Check instructor profile
        print(self.instructor["firstName"])
        existing_term_schedule = False  # Initialize to False
        existing_term_schedule_data = self.instructor_availability_row[
            "weekly_availability"
        ]
        if existing_term_schedule_data != "null":
            existing_term_schedule = True

        self.card_title.text = f"Instructor: {self.instructor['firstName']} {self.instructor['surname'][0]}."
        self.full_name_label.text = (
            f"Full Name: {self.instructor['firstName']} {self.instructor['surname']}"
        )
        self.phone_number_label.text = f"Cell Phone: {self.instructor['phoneNumber']}"
        self.email_label.text = f"Email: {self.instructor['email']}"
        self.term_dates_list.text = "**Example** This applies to Fall 2025 (dates 9/1-12/23), Winter 2026 (dates 1/3 - 4/1) and Spring 2026 (4/10 - 7/10)."

        # For testing - remove later
        existing_term_schedule = False
        if existing_term_schedule is True:
            print(existing_term_schedule_data)
            self.term_availability_drop_down_panel.items = existing_term_schedule_data
        else:
            # Create items for each lesson slot
            self.term_availability_drop_down_panel.items = [
                {
                    "slot": slot_name,
                    "time": f"{slot_info['start_time']} - {slot_info['end_time']}",
                    "type": "drive" if "Drive" in slot_name else "class",
                    "availability": self.availability_codes,
                }
                for slot_name, slot_info in self.lesson_slots.items()
                if slot_name
                not in ["Break - am", "Break - Lunch", "Break - pm"]  # Skip break times
            ]

    def download_term_availability_button_click(self, **event_args):
        json = self.instructor_availability_row["weekly_availability"]
        csv_file_name = f"{self.instructor['firstName']}_{self.instructor['surname']}_term_availability.csv"
        anvil.server.call("convert_JSON_to_csv_and_save", json, csv_file_name)
