from ._anvil_designer import SchedulerTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
from datetime import date, time, datetime, timedelta, sleep
import plotly.graph_objects as go


class Scheduler(SchedulerTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        self.merged_schedule = ""
        self.classroom_name = ""
        self.start_date = None

        school_list = app_tables.schools.search()
        self.school_selector.items = [
            (s["school_name"], s["abbreviation"]) for s in school_list
        ]
        self.filter_instructors = False

        self.COURSE_STRUCTURE = "None"

        classroom_placeholder = [("Select a classroom", None)]
        current_classrooms = app_tables.classrooms.search()
        classroom_items = [
            (c["classroom_name"], c["classroom_name"]) for c in current_classrooms
        ]
        self.classroom_selector.items = classroom_placeholder + classroom_items
        self.classroom_selector.selected_value = None

        instructor_placeholder = [("Select an instructor", None)]
        self.instructors = app_tables.users.search(is_instructor=True)
        instructor_items = [
            (i["firstName"] + " " + i["surname"], i) for i in self.instructors
        ]
        self.instructor_1_selector.items = instructor_placeholder + instructor_items
        self.instructor_2_selector.items = instructor_placeholder + instructor_items
        self.instructor_1_selector.selected_value = None
        self.instructor_2_selector.selected_value = None

        self.populate_instructor_filter_drop_down()
        self.refresh_schedule_display()

    # ##############################################
    # Export schedule placeholder - not in use right now
    def export_schedule_button_click(self, **event_args):
        filename = f"Teen Schedule - version {date.today()}.csv"
        csv_file = anvil.server.call(
            "convert_JSON_to_csv_and_save", self.teen_schedule, filename
        )

    def upload_new_schedule_button_change(self, file, **event_args):
        if file is not None:
            c = confirm(
                "⚠️ WARNING ⚠️ \nThis will overwrite the current lesson schedule. Only proceed if you are sure."
            )
            if c is True:
                result = anvil.server.call("update_teen_drive_schedule", file)
                if result is True:
                    n = Notification("The schedule has been updated successfully.")

                else:
                    n = Notification("There was an error updating the schedule.")
                n.show()
                self.refresh_data_bindings()
            else:
                pass
        from ..Frame import Frame

        open_form("Frame", Scheduler)

    # ##############################################
    # Schedule preparation and display

    def populate_instructor_filter_drop_down(self):
        """Populate the dropdown with available instructors"""
        # Get all instructors from the database
        instructors = app_tables.users.search(tables.order_by("display_order", ascending=True), is_instructor=True)
        instructor_names = [
            f"{instructor['firstName']} {instructor['surname']}"
            for instructor in instructors
        ]
        instructor_list_text = ", ".join(instructor_names)
        self.instructor_list.text = f"Instructors displayed: {instructor_list_text}"

        # Populate dropdown with instructor names
        self.instructor_filter_drop_down.items = [
            (i["firstName"] + " " + i["surname"], i) for i in instructors
        ]

        # Select first instructor as default if available
        if self.instructor_filter_drop_down.items:
            self.instructor_filter_drop_down.selected_value = (
                self.instructor_filter_drop_down.items[0][1]
            )

        # Initially hide the dropdown since filtering is off by default
        self.instructor_filter_drop_down.visible = False

    def refresh_schedule_display(self, start_date=None):
        if start_date is None:
            self.start_date = datetime.now().date()
        formatted_date = self.start_date.strftime("%A, %B %d")
        self.week_shown_label.text = f"Availability for {formatted_date}."

        # Get selected instructors based on filter status
        if self.filter_instructors:
            # When filter is on, use the selected instructor
            if self.instructor_filter_drop_down.selected_value:
                selected_instructors = [self.instructor_filter_drop_down.selected_value]
                self.instructor_list.visible = False

        else:
            # When filter is off, get all instructors
            selected_instructors = app_tables.users.search(tables.order_by("display_order", ascending=True), is_instructor=True)
            self.instructor_list.visible = True

        # Get data from server
        print("Getting data:\n")
        data = anvil.server.call(
            "process_instructor_availability", selected_instructors, self.start_date
        )
        print(data)

        if not data:
            self.schedule_plot_complete.visible = False
            print("no data to show")
            return
        # data format: 'z_values': availability code (0-1)
        # availability_mapping =
        #  "No": 0,
        # "Yes": 1,

        # 'x_labels': Days,'y_labels': hours, 'instructors': [i['firstName'] for i in instructors]
        # Create a simple heatmap
        text_matrix = []
        for row in data["z_values"]:
            text_row = []
            for val in row:
                if val == 0:
                    text_row.append("No")
                elif val == 1:
                    text_row.append("Any")
                elif val == 2:
                    text_row.append("Drive<br>Only")
                elif val == 3:
                    text_row.append("Class<br>Only")
                elif val == 4:
                    text_row.append("Scheduled")
                elif val == 5:
                    text_row.append("Booked")
                elif val == 6:
                    text_row.append("Vacation")
                else:
                    text_row.append("")
            text_matrix.append(text_row)

        fig = go.Figure(
            data=go.Heatmap(
                z=data["z_values"],
                x=data["x_labels"],
                y=data["y_labels"],
                colorscale=[
                    [0 / 6, "grey"],  # 0: Not available
                    [1 / 6, "purple"],  # 1: Available for both
                    [2 / 6, "purple"],  # 2: Available for drives only
                    [3 / 6, "purple"],  # 3: Available for classes only
                    [4 / 6, "blue"],  # 4: Allocated to classroom slot
                    [5 / 6, "blue"],  # 5: Booked
                    [6 / 6, "grey"],  # 6: Vacation
                ],
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=10),
                textwrap = True,
                showscale=False,
                bgcolor="white",
                zmin=0,
                zmax=6,
            )
        )
        # Update layout - keeping it very minimal
        title_text = "Weekly Availability"
        if data["instructors"]:
            title_text += f": {', '.join(data['instructors'])}"

        fig.update_layout(
            title=None,  # Remove title
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(side="top", tickangle=-45, tickfont=dict(color="black")),
            yaxis=dict(tickfont=dict(color="black")),
        )

        # Set the plot's figure
        self.schedule_plot_complete.figure = fig
        self.schedule_plot_complete.visible = True

    def filter_schedule_switch_change(self, **event_args):
        self.filter_instructors = self.filter_schedule_switch.checked
        self.instructor_filter_drop_down.visible = self.filter_instructors
        self.refresh_schedule_display()

    def instructor_filter_drop_down_change(self, **event_args):
        self.filter_instructors = True
        self.refresh_schedule_display()

    def classroom_builder_button_click(self, **event_args):

        if not self.school_selector.selected_value:
            self.schedule_print_box.content = "Please select a school"
            return

        if not self.start_date:
            self.schedule_print_box.content = "Please select a start date"
            return

        # Convert the string date back to a date object for the API call
        start_date = datetime.strptime(self.start_date, "%m-%d-%Y").date()

        self.classroom_schedule = anvil.server.call(
            "create_full_classroom_schedule",
            self.school_selector.selected_value,
            start_date,
            None,
            self.COURSE_STRUCTURE,
        )

        if self.classroom_schedule:
            self.classroom_name = self.classroom_schedule["classroom_name"]
            formatted_output = (
                f"classroom Schedule: {self.classroom_schedule['classroom_name']}\n\n"
            )

            # formatted_output += "Class Schedule:\n"
            # for class_slot in self.classroom_schedule['classes']:
            # formatted_output += f"Class {class_slot['class_number']}: {class_slot['date']} ({class_slot['day']})\n"

            # formatted_output += "\nDrive Schedule:\n"
            # for drive in self.classroom_schedule['drives']:
            # formatted_output += f"Pair {drive['pair_letter']}: {drive['date']} - Slot {drive['slot']} (Week {drive['week']})\n"

            formatted_output += f"\nSummary:\n"
            formatted_output += (
                f"Number of Students: {self.classroom_schedule['num_students']}\n"
            )
            formatted_output += f"Start Date: {self.classroom_schedule['start_date']}\n"
            formatted_output += f"End Date: {self.classroom_schedule['end_date']}"

            self.schedule_print_box.content = f"The classroom has been completed successfully:\n\n{formatted_output}\n\n You can export this file now"
        else:
            self.schedule_print_box.content = "Error creating schedule"

    def school_selector_change(self, **event_args):
        self.selected_school = self.school_selector.selected_value

    def classroom_start_date_change(self, **event_args):
        start_date = self.classroom_start_date.date
        self.start_date = start_date.strftime("%m-%d-%Y")

    def export_classroom_button_click(self, **event_args):
        name = self.classroom_name
        anvil.server.call("export_merged_classroom_schedule", name)
        self.classroom_name = ""
        self.schedule_export_notice_label.visible = True

    def create_availability_report_button_click(self, **event_args):
        anvil.server.call("generate_capacity_report")
        Notification("Your report is available in the file downloader")

    def classroom_selector_change(self, **event_args):
        classroom = app_tables.classrooms.get(
            classroom_name=self.classroom_selector.selected_value
        )
        self.classroom_name_label.text = f"classroom selected: School - {classroom['school']}, Start date - {classroom['start_date']}"
        self.classroom = classroom

    def instructor_1_selector_change(self, **event_args):
        self.instructor1 = self.instructor_1_selector.selected_value

    def instructor_2_selector_change(self, **event_args):
        self.instructor2 = self.instructor_2_selector.selected_value

    def schedule_instructors_button_click(self, **event_args):
        instructor_allocation = anvil.server.call(
            "schedule_instructors_for_classroom",
            self.classroom,
            self.instructor1,
            self.instructor2,
        )
        self.scheduling_text_box.text = f"The instructors ({self.instructor1['firstName']}, {self.instructor2['firstName']}) have been successfully added to {self.classroom['classroom_name']}. You can export this file now."  # instructor_allocation

    def export_classroom_and_schedule_button_click(self, **event_args):
        name = self.classroom["classroom_name"]
        anvil.server.call("export_merged_classroom_schedule", name)
        self.classroom = ""

    def download_availability_button_click(self, **event_args):
        anvil.server.call("export_instructor_eight_monthavailability")

    def forward_day_button_click(self, **event_args):
        new_start_date = self.start_date + timedelta(days=1)
        self.start_date = new_start_date
        self.refresh_schedule_display(self.start_date)

    def back_day_button_click(self, **event_args):
        new_start_date = self.start_date + timedelta(days=-1)
        self.start_date = new_start_date
        self.refresh_schedule_display(self.start_date)

    def classroom_type_selector_change(self, **event_args):
        if self.classroom_type_selector.checked is True:
            self.COURSE_STRUCTURE = "COURSE_STRUCTURE_COMPRESSED"
        else:
            self.COURSE_STRUCTURE = "COURSE_STRUCTURE_STANDARD"

    def availability_display_date_picker_change(self, **event_args):
      self.start_date = self.availability_display_date_picker.date
      self.refresh_schedule_display(self.start_date)

    def today_reset_link_click(self, **event_args):
      self.start_date = datetime.now().date()
      self.refresh_schedule_display(self.start_date)

