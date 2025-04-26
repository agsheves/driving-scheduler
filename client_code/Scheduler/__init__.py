from ._anvil_designer import SchedulerTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
from datetime import date, time, datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go

class Scheduler(SchedulerTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    current_teen_driving_schedule = app_tables.global_variables_edit_with_care.get(version='latest')['current_teen_driving_schedule']

    # Better error handling approach
    try:
        # Check if it's a string first
        if isinstance(current_teen_driving_schedule, str):
            self.teen_schedule = json.loads(current_teen_driving_schedule)
        else:
            # It's already a dictionary
            self.teen_schedule = current_teen_driving_schedule
    except json.JSONDecodeError:
        # Handle the case where it's a string but not valid JSON
        print("Invalid JSON format")
        # Provide a fallback or raise an appropriate error

    drive_list_dict = []
    class_list_dict = []
    break_list_dict = []
    drive_list_print = ""
    class_list_print = ""
    break_list_print = ""
    
    # New code for flattened structure:
    for title, event in self.teen_schedule.items():
        start_time = event["start_time"]
        end_time = event["end_time"]
        seasonal = event["seasonal"]
        term = event['term']  # Note: renamed from days_term
        vacation = event['vacation']  # Note: renamed from days_vacation
        if 'Drive' in title:
          drive_list_dict.append(event)
          drive_list_print += f"{title} -- Start - {start_time} / end - {end_time} | Seasonal restrictions - {seasonal} | Days available (term) - {term} | Days available (vacation) - {vacation}\n"
        if 'Class' in title:
          class_list_dict.append(event)
          class_list_print += f"{title} -- Start - {start_time} / end - {end_time} | Seasonal restrictions - {seasonal} | Days available (term) - {term} | Days available (vacation) - {vacation}\n"
        if 'Break' in title:
          break_list_dict.append(event)
          break_list_print += f"{title} -- Start - {start_time} / end - {end_time}\n"

    self.drive_time_list_label.text = drive_list_print
    self.class_time_list_label.text = class_list_print
    self.break_time_list_label.text = break_list_print

  def export_schedule_button_click(self, **event_args):
    filename = f"Teen Schedule - version {date.today()}.csv"
    csv_file = anvil.server.call('convert_JSON_to_csv_and_save', self.teen_schedule, filename)

  def upload_new_schedule_button_change(self, file, **event_args):
      if file is not None:
          c = confirm("⚠️ WARNING ⚠️ \nThis will overwrite the current lesson schedule. Only proceed if you are sure.")
          if c is True:
              result = anvil.server.call('update_teen_drive_schedule', file)
              if result is True:
                n = Notification("The schedule has been updated successfully.")

              else:
                n = Notification("There was an error updating the schedule.")
              n.show()
              self.refresh_data_bindings()
          else:
            pass
      from ..Frame import Frame
      open_form('Frame', Scheduler)
