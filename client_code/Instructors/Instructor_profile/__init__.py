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
    self.term_dates_list.text = "**Example** This applies to Fall 2025 (dates 9/1-12/23), Winter 2026 (dates 1/3 - 4/1) and Spring 2026 (4/10 - 7/10)."
    self.vacation_dates_list.text = "**Example** This applies to school vacation. Christmas Break 25-26 (dates 12/23 - 1/2), Spring 22026 (dates 4/1 - 4/9) and Summer vacation 2026 (7/10 - 08/31)"

    
    # Define days and time slots
    self.time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    self.availability = ["Unavailable", "Drive Only", "Class Only", "Drive or Class"]

    self.term_availability_drop_down_panel.items = [{'time': t, 'availability': self.availability} for t in self.time_slots]



    # Configure the DataGrid with columns for each day
    self.setup_data_grid_term(instructor['email'])
    #self.setup_data_grid_vacation(instructor['email']

  
  def setup_data_grid_term(self, instructorEmail):
      # Configure columns - one for time slot and one for each day
      columns = [
        {"id": "time_slot", "title": "Time Slot", "data_key": "time_slot", "width": 75}
      ]
      instructor = app_tables.users.get(email=instructorEmail)
      instructor_availability_row = app_tables.instructor_schedules.get(instructor=instructor)
      school_term_availability = instructor_availability_row['school_term_availability']
      existing_term_scheule = False # Initialize to False
      if school_term_availability is not 'null':
        existing_term_scheule = True
        print(existing_term_scheule)
      school_vacation_availability = instructor_availability_row['vacation_days']
      existing_vacation_scheule = False # Initialize to False
      if school_vacation_availability is not 'null':
        existing_vacation_scheule = True
  
      # Extract schedule from the JSON
      schedule = school_term_availability.get('weekly_availability', {}) if school_term_availability else {}
  
      for day in self.days:
        day_lower = day.lower()
        columns.append({
          "id": day_lower,
          "title": day,
          "data_key": day_lower,
          "width": 100,
        })
  
      # Set the columns property of the DataGrid
      self.term_availability_grid.columns = columns
  
      # Prepare the data structure for the repeating panel
      rows = []
      for time in self.time_slots:
        row = {"time_slot": time}
        # Set availability based on schedule JSON
        if existing_term_scheule:
          for day in self.days:
            day_lower = day.lower()
            # Extract availability for this day and time from the JSON
            row[day_lower] = schedule.get(day_lower, {}).get(time, 'no')
        else:
          for day in self.days:
            row[day.lower()] = 'no' # Default value if no schedule
        rows.append(row)
  
      # Set the items property of the RepeatingPanel inside the DataGrid
      self.term_availability_repeating_panel.items = rows




 