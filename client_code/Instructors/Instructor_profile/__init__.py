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
    instructor = app_tables.users.get(instructorID=instructorID)
    print(instructor['firstName'])
    self.card_title.text = f"Instructor: {instructor['firstName']} {instructor['surname'][0]}."
    self.full_name_label.text = f"Full Name: {instructor['firstName']} {instructor['surname']}"
    self.phone_number_label.text = f"Cell Phone: {instructor['phoneNumber']}"
    self.email_label.text = f"Email: {instructor['email']}"
  
    
    # Define days and time slots
    self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    self.drive_times = ["8:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    self.class_times = ["8:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    
    # Configure the DataGrid with columns for each day
    self.setup_data_grid_drive_term(instructor['email'])
    self.setup_data_grid_class_term(instructor['email'])

  
  def setup_data_grid_drive_term(self, instructorEmail):
    # Configure columns - one for time slot and one for each day
    columns = [
      {"id": "time_slot", "title": "Time Slot", "data_key": "time_slot", "width": 100}
    ]
    instructor = app_tables.users.get(email=instructorEmail)
    instructor_availability_row = app_tables.instructor_schedules.get(instructor=instructor)
    school_term_availability = instructor_availability_row['school_term_availability']
    
    # Extract schedule from the JSON
    schedule = school_term_availability['schedule']
    
    for day in self.days:
      columns.append({
        "id": day.lower(),
        "title": day,
        "data_key": day.lower(),
        "width": 100,
        # Add formatting based on availability
        "background": lambda value: {'green' if value == 'yes' else 'red'}
      })
    
    # Set the columns property of the DataGrid
    self.term_availability_drive_grid.columns = columns
    
    # Prepare the data structure for the repeating panel
    rows = []
    for time in self.drive_times:
      row = {"time_slot": time}
      # Set availability based on schedule JSON
      for day in self.days:
        day_lower = day.lower()
        # Extract availability for this day and time from the JSON
        if day_lower in schedule and 'drive_sessions' in schedule[day_lower]:
          row[day_lower] = schedule[day_lower]['drive_sessions'].get(time, 'no')
        else:
          row[day_lower] = 'no'
      rows.append(row)
    
    # Set the items property of the RepeatingPanel inside the DataGrid
    self.repeating_panel_1.items = rows

  def setup_data_grid_class_term(self, instructorEmail):
    # Configure columns - one for time slot and one for each day
    columns = [
      {"id": "time_slot", "title": "Time Slot", "data_key": "time_slot", "width": 100}
    ]
    
    # Add a column for each day
    for day in self.days:
      columns.append({
        "id": day.lower(),
        "title": day,
        "data_key": day.lower(),
        "width": 100
      })
    
    # Set the columns property of the DataGrid
    self.term_availability_class_grid.columns = columns
    
    # Prepare the data structure for the repeating panel
    rows = []
    for time in self.class_times:
      row = {"time_slot": time}
      # Initialize all days as False (not available)
      for day in self.days:
        row[day.lower()] = False
      rows.append(row)
    
    # Set the items property of the RepeatingPanel inside the DataGrid
    self.repeating_panel_2.items = rows


 