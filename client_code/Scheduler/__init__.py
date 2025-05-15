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
from datetime import date, time, datetime, timedelta
from time import sleep
import plotly.graph_objects as go
import uuid


class Scheduler(SchedulerTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        self.merged_schedule = ""
        self.classroom_name = ""
        self.start_date = None

        school_list = app_tables.schools.search()
        self.school_selector.items = [
            (s['abbreviation'], s["abbreviation"]) for s in school_list
        ] # f"{s['abbreviation']} - {s['school_name']}"
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

        self.populate_instructor_filter_drop_down()
        self.refresh_schedule_display()


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
        self.instructor_filter_drop_down.items = [
            (i["firstName"] + " " + i["surname"], i) for i in instructors
        ]

        if self.instructor_filter_drop_down.items:
            self.instructor_filter_drop_down.selected_value = (
                self.instructor_filter_drop_down.items[0][1]
            )
        self.instructor_filter_drop_down.visible = False

# ###########################################
# Gets all current parameters and rebuilds the display including the availability heatmap
# This is triggered after every function call so availability remains up to date
  
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

        data = anvil.server.call(
            "process_instructor_availability", selected_instructors, self.start_date
        )

        if not data:
            self.schedule_plot_complete.visible = False
            print("no data to show")
            return
 
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

# Availability display navigation
  
    def forward_day_button_click(self, **event_args):
      new_start_date = self.start_date + timedelta(days=1)
      self.start_date = new_start_date
      self.refresh_schedule_display(self.start_date)

    def back_day_button_click(self, **event_args):
      new_start_date = self.start_date + timedelta(days=-1)
      self.start_date = new_start_date
      self.refresh_schedule_display(self.start_date)

    def today_reset_link_click(self, **event_args):
      self.start_date = datetime.now().date()
      self.refresh_schedule_display(self.start_date)

# ###########################################
# UI change handling
  
    def filter_schedule_switch_change(self, **event_args):
        self.filter_instructors = self.filter_schedule_switch.checked
        self.instructor_filter_drop_down.visible = self.filter_instructors
        self.refresh_schedule_display()

    def instructor_filter_drop_down_change(self, **event_args):
        self.filter_instructors = True
        self.refresh_schedule_display()

    def school_selector_change(self, **event_args):
      self.selected_school = self.school_selector.selected_value

    def classroom_start_date_change(self, **event_args):
      start_date = self.classroom_start_date.date
      self.start_date = start_date.strftime("%m-%d-%Y")

    def classroom_type_selector_change(self, **event_args):
      if self.classroom_type_selector.checked is True:
        self.COURSE_STRUCTURE = "COURSE_STRUCTURE_COMPRESSED"
      else:
        self.COURSE_STRUCTURE = "COURSE_STRUCTURE_STANDARD"

    def availability_display_date_picker_change(self, **event_args):
      self.start_date = self.availability_display_date_picker.date
      self.refresh_schedule_display(self.start_date)

# ######################################
# Classroom builder and report generation

    def classroom_builder_button_click(self, **event_args):
    # Creates an ideal classroom of scheduled classes and drives
    # Accounts for holidays and no-drive days
    # Checks that there is overall instructor capacity available over this period to run a classroom
        if not self.school_selector.selected_value:
            self.schedule_print_box.content = "Please select a school"
            return
        school = self.school_selector.selected_value

        if not self.start_date:
            self.schedule_print_box.content = "Please select a start date"
            return
        start_date = datetime.strptime(self.start_date, "%m-%d-%Y").date()

        task_id = str(uuid.uuid4())
        anvil.server.call("create_full_classroom_schedule", school, start_date, task_id, num_students=None, classroom_type=None)
        self.set_and_monitor_background_task(task_id)
        print("Running background classroom builder")
  
    def create_availability_report_button_click(self, **event_args):
        result, filename = anvil.server.call("generate_capacity_report")
        if result is True:
          alert(content = f"Your report was downloaded to the files list as:\n{filename}", large=True, dismissible=True)
        else:
          alert(content = "There was an error downloading your report. Please try again", large=True, dismissible=True)

    def download_availability_button_click(self, **event_args):
        result, filename = anvil.server.call("export_instructor_eight_month_availability")
        if result is True:
          alert(content = f"Your report was downloaded to the files list as:\n{filename}", large=True, dismissible=True)
        else:
          alert(content = "There was an error downloading your report. Please try again", large=True, dismissible=True)

    def check_for_background_task(self,task_id):
      while True:
        row = app_tables.background_tasks_table.get(task_id=task_id)
        if row is None:
          alert("Task was not initiated properly. Please try again.", large=True, dismissible=True)
          return
    
        status = row['status']
    
        if status in ('complete', 'error'):
          results_message = row['results_text']
          alert(content=results_message, large=True, dismissible=True)
          return
    
        sleep(30)

    def set_and_monitor_background_task(self,task_id):
        now = datetime.now()
        app_tables.background_tasks_table.add_row(
          start_time=now,
          status='running',
          task_id=task_id
        )
  
        n =Notification("Your task is running and you will receive an alert when it is complete")
        n.show()
        sleep(5)
        self.check_for_background_task(task_id)

    
            
# ##############################################
# Schedule upload which overwrites the availability schedule which are used for all FUTURE planning

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

# #################################
# Adding instructors to a classroom schedule

    def classroom_selector_change(self, **event_args):
      classroom = app_tables.classrooms.get(
        classroom_name=self.classroom_selector.selected_value
      )
      self.classroom_name_label.text = f"Classroom selected: School - {classroom['school']}, Start date - {classroom['start_date']}"
      self.classroom = classroom
    
      self.available_instructors = app_tables.users.search(is_instructor=True)
      self.available_instructors_school = []
    
      for instructor in self.available_instructors:
        # instructor here is a user row (users table)
        schedule = app_tables.instructor_schedules.get(instructor=instructor)
        if schedule and self.classroom['school'] not in schedule['school_preferences'].get('no', []):
          self.available_instructors_school.append(instructor)

      
      # Now build the dropdown list using names from the users table
      instructor_items_school = [
        {
          'value': instructor,                  # actual row object for internal use
          'label': instructor['firstName'],     # not used for display in this component
          'key': instructor['firstName']        # Use firstName as the display text
        }
        for instructor in self.available_instructors_school
      ]
      
      self.instructor_schedule_multi_select.items = instructor_items_school
      self.instructor_schedule_multi_select.enabled = True

    
    def instructor_schedule_multi_select_change(self, **event_args):
      selected_keys = self.instructor_schedule_multi_select.selected_keys
    
      # Need to map from firstName back to the instructor objects
      self.selected_instructors = []
      for key in selected_keys:  # keys are now firstNames
        for instructor in self.available_instructors_school:
          if instructor['firstName'] == key:
            self.selected_instructors.append(instructor)
            break
    
      if len(self.selected_instructors) >= 3:
        self.instructor_1 = self.selected_instructors[0]
        self.instructor_2 = self.selected_instructors[1]
        self.instructor_3 = self.selected_instructors[2]
    
        self.task_summary_label.text = (
          f"You are scheduling {self.instructor_1['firstName']}, "
          f"{self.instructor_2['firstName']}, and {self.instructor_3['firstName']} "
          f"for {self.classroom['classroom_name']}."
        )
        self.schedule_instructors_button.enabled = True
      else:
        self.task_summary_label.text = "Please select at least 3 instructors."



    def schedule_instructors_button_click(self, **event_args):
      # Adds instructors to the chosen classroom
      # User selects instructors to prioritize and scheduler works around availability and school preference
      if not self.classroom_selector.selected_value:
        self.instructor_alert_box.visible = True
        self.instructor_alert_box.text = "Please select a classroom"
        return
      if len(self.instructor_schedule_multi_select.selected_keys) != 3:
        self.instructor_alert_box.visible = True
        self.instructor_alert_box.text = "Please select three instructors"
        return
      print("Scheduling instructors")
      task_id = str(uuid.uuid4())
      anvil.server.call(
        "schedule_instructors_for_classroom",
        self.classroom['classroom_name'],
        self.instructor_1,
        self.instructor_2,
        self.instructor_3, 
        task_id
      )
      self.set_and_monitor_background_task(task_id)

      self.instructor_1 = ""
      self.instructor_2 = ""
      self.instructor_3 = ""
      self.classroom = ""
    
