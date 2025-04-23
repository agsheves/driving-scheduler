from ._anvil_designer import Instructor_profileTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from ...globals import availability_codes, availability_time_slots, days_full


class Instructor_profile(Instructor_profileTemplate):
  def __init__(self, instructorID,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    instructor = app_tables.users.get(instructorID=instructorID)
    instructor_availability_row = app_tables.instructor_schedules.get(instructor=instructor)

    # Define these from globals so all actions are using the same variables.
    self.time_slots = availability_time_slots
    self.availability_codes = availability_codes
    self.days_formatted = days_full

    # Check instructor profile
    print(instructor['firstName'])
    existing_term_scheule = False # Initialize to False
    existing_term_scheule_data = instructor_availability_row['school_term_availability']
    if existing_term_scheule_data != 'null':
      existing_term_scheule = True
      #print(existing_term_scheule_data)
    existing_vacation_schedule = False # Initialize to False
    school_vacation_availability_data = instructor_availability_row['vacation_days']
    if school_vacation_availability_data != 'null':
      existing_vacation_schedule = True
      print(school_vacation_availability_data)
        
    self.card_title.text = f"Instructor: {instructor['firstName']} {instructor['surname'][0]}."
    self.full_name_label.text = f"Full Name: {instructor['firstName']} {instructor['surname']}"
    self.phone_number_label.text = f"Cell Phone: {instructor['phoneNumber']}"
    self.email_label.text = f"Email: {instructor['email']}"
    self.term_dates_list.text = "**Example** This applies to Fall 2025 (dates 9/1-12/23), Winter 2026 (dates 1/3 - 4/1) and Spring 2026 (4/10 - 7/10)."
    self.vacation_dates_list.text = "**Example** This applies to school vacation. Christmas Break 25-26 (dates 12/23 - 1/2), Spring 22026 (dates 4/1 - 4/9) and Summer vacation 2026 (7/10 - 08/31)"

    if existing_term_scheule is True:
      print(existing_term_scheule_data)
      self.term_availability_drop_down_panel.items = existing_term_scheule_data
    else:
      self.term_availability_drop_down_panel.items = [{'time': t, 'availability': self.availability_codes} for t in self.time_slots]


  


 