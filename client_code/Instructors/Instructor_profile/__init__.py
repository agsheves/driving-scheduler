from ._anvil_designer import Instructor_profileTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users



class Instructor_profile(Instructor_profileTemplate):
  def __init__(self, instructorID,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.instructorID = instructorID
    self.instructor = app_tables.users.get(instructorID=self.instructorID)
    self.instructor_availability_row = app_tables.instructor_schedules.get(instructor=self.instructor)

    # Define these from globals so all actions are using the same variables.
    self.time_slots = app_tables.global_variables_edit_with_care.get(version='latest')['availability_time_slots']
    self.availability_codes = app_tables.global_variables_edit_with_care.get(version='latest')['instructor_availability_codes']
    self.days_formatted = app_tables.global_variables_edit_with_care.get(version='latest')['days_full']

    # Check instructor profile
    print(self.instructor['firstName'])
    existing_term_schedule = False # Initialize to False
    existing_term_schedule_data = self.instructor_availability_row['school_term_availability']
    if existing_term_schedule_data != 'null':
      existing_term_schedule = True
      #print(existing_term_schedule_data)
    existing_vacation_schedule = False # Initialize to False
    school_vacation_availability_data = self.instructor_availability_row['vacation_days']
    if school_vacation_availability_data != 'null':
      existing_vacation_schedule = True
      print(school_vacation_availability_data)
        
    self.card_title.text = f"Instructor: {self.instructor['firstName']} {self.instructor['surname'][0]}."
    self.full_name_label.text = f"Full Name: {self.instructor['firstName']} {self.instructor['surname']}"
    self.phone_number_label.text = f"Cell Phone: {self.instructor['phoneNumber']}"
    self.email_label.text = f"Email: {self.instructor['email']}"
    self.term_dates_list.text = "**Example** This applies to Fall 2025 (dates 9/1-12/23), Winter 2026 (dates 1/3 - 4/1) and Spring 2026 (4/10 - 7/10)."
    self.vacation_dates_list.text = "**Example** This applies to school vacation. Christmas Break 25-26 (dates 12/23 - 1/2), Spring 22026 (dates 4/1 - 4/9) and Summer vacation 2026 (7/10 - 08/31)"

    # For testing - remove later
    existing_term_schedule = False
    if existing_term_schedule is True:
      print(existing_term_schedule_data)
      self.term_availability_drop_down_panel.items = existing_term_schedule_data
    else:
      self.term_availability_drop_down_panel.items = [{'time': t, 'availability': self.availability_codes} for t in self.time_slots]

  def download_term_availability_button_click(self, **event_args):
    json = self.instructor_availability_row['school_term_availability']
    csv_file_name = f"{self.instructor['firstName']}_{self.instructor['surname']}_term_availability.csv"
    anvil.server.call('convert_JSON_to_csv_and_save', json, csv_file_name)


  


 