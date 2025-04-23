from ._anvil_designer import Instructor_profileTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users


class Instructor_profile(Instructor_profileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
  
    
    # Define days and time slots
    self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    self.drive_times = ["8:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    self.class_times = ["8:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    
    # Configure the DataGrid with columns for each day
    self.setup_data_grid_drive_term()
    self.setup_data_grid_class_term()

  
  def setup_data_grid_drive_term(self):
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
    self.term_availability_drive_grid.columns = columns
    
    # Prepare the data structure for the repeating panel
    rows = []
    for time in self.drive_times:
      row = {"time_slot": time}
      # Initialize all days as False (not available)
      for day in self.days:
        row[day.lower()] = False
      rows.append(row)
    
    # Set the items property of the RepeatingPanel inside the DataGrid
    self.repeating_panel_2.items = rows

  def setup_data_grid_class_term(self):
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
    self.repeating_panel_1.items = rows


 