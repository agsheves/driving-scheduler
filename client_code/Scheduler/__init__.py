from ._anvil_designer import SchedulerTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
from ..globals import availability_codes, availability_time_slots, days_short,days_full, teen_driving_schedule


class Scheduler(SchedulerTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Better error handling approach
    try:
        # Check if it's a string first
        if isinstance(teen_driving_schedule, str):
            teen_schedule = json.loads(teen_driving_schedule)
        else:
            # It's already a dictionary
            teen_schedule = teen_driving_schedule
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
    
    for event in teen_schedule['lesson_schedule']:
      title = event["title"]
      start_time = event["start_time"]
      end_time = event["end_time"]
      seasonal = event["seasonal"]
      days_term = event['days_term']
      days_vacation = event['days_vacation']
      if 'Drive' in title:
        drive_list_dict.append(event)
        drive_list_print += f"{title} -- Start - {start_time} / end - {end_time} | Seasonal restrictions - {seasonal} | Days available (term) - {days_term} | Days available (vacation) - {days_vacation}\n"
      if 'Class' in title:
        class_list_dict.append(event)
        class_list_print += f"{title} -- Start - {start_time} / end - {end_time} | Seasonal restrictions - {seasonal} | Days available (term) - {days_term} | Days available (vacation) - {days_vacation}\n"
      if 'Break' in title:
        break_list_dict.append(event)
        break_list_print += f"{title} -- Start - {start_time} / end - {end_time}\n"

    self.drive_time_list_label.text = drive_list_print
    self.class_time_list_label.text = class_list_print
    self.break_time_list_label.text = break_list_print