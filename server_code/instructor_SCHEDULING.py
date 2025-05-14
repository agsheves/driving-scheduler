import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime
from .globals import LESSON_SLOTS, AVAILABILITY_MAPPING

@anvil.server.callable
def schedule_instructors_for_classroom(classroom_name, instructor1, instructor2, instructor3, task_id):
  anvil.server.launch_background_task('schedule_instructors_for_classroom_and_export_background', classroom_name, instructor1, instructor2, instructor3, task_id)

@anvil.server.background_task
def schedule_instructors_for_classroom_and_export_background(classroom_name, instructor1, instructor2, instructor3, task_id):
  print("Checking for classroom")
  try:
    classroom = app_tables.classrooms.get(classroom_name=classroom_name)
    print(f"Found {classroom_name}")
    if not classroom:
      raise ValueError(f"classroom {classroom_name} not found")
  
    print("Checking for instructors")
    print(instructor1["firstName"])
    print(instructor2["firstName"])
    print(instructor3["firstName"])
  
    if not instructor1 or not instructor2 or not instructor3:
      raise ValueError("Some instructors not found")
  
    print("Checking for instructor schedules")
    instructor1_schedule = app_tables.instructor_schedules.get(instructor=instructor1)
    instructor2_schedule = app_tables.instructor_schedules.get(instructor=instructor2)
    instructor3_schedule = app_tables.instructor_schedules.get(instructor=instructor3)
  
    if not instructor1_schedule or not instructor2_schedule or not instructor3_schedule:
      raise ValueError("Some instructor schedules not found")
  
    instructor1_availability = instructor1_schedule["current_seven_month_availability"]
    instructor2_availability = instructor2_schedule["current_seven_month_availability"]
    instructor3_availability = instructor3_schedule["current_seven_month_availability"]
  
    daily_schedules = classroom["complete_schedule"]
    print("Checked initial info collection")
  
    daily_schedules = _schedule_classes(
      daily_schedules,
      instructor1,
      instructor2,
      instructor3,
      instructor1_availability,
      instructor2_availability,
      instructor3_availability,
    )
  
    daily_schedules = _schedule_drives(
      daily_schedules,
      instructor1,
      instructor2,
      instructor3,
      instructor1_availability,
      instructor2_availability,
      instructor3_availability,
    )
  
    classroom.update(complete_schedule_with_instructors=daily_schedules)
  
    _persist_instructor_availability(instructor1, instructor1_availability)
    _persist_instructor_availability(instructor2, instructor2_availability)
    _persist_instructor_availability(instructor3, instructor3_availability)
  
    results_message = f"Instructors added to {classroom_name} successfully\n"
    print("Exporting full schedule with instructors")
    filename, download_message = anvil.server.call('export_merged_classroom_schedule', classroom_name, 'instructors')
    results_message += f"Export results: {download_message}"
    
    task_row = app_tables.background_tasks_table.get(task_id=task_id)
    now = datetime.now()
    if task_row:
      task_row.update(
        status='complete',
        results_text=results_message,
        end_time=now,
        output_filename=filename
    )
  
  except Exception as e:
    task_row = app_tables.background_tasks_table.get(task_id=task_id)
    now = datetime.now()
    error_message = f"An error occurred: {e}"
    if task_row:
      task_row.update(
        status='error',
        results_text=error_message,
        end_time=now
      )


def _get_primary_instructor(date_str, instructor1, instructor2, instructor3):
  date = datetime.strptime(date_str, "%Y-%m-%d")
  week_number = date.isocalendar()[1]
  instructors = [instructor1, instructor2, instructor3]
  return instructors[week_number % len(instructors)]


def _schedule_classes(
  daily_schedules,
  instructor1,
  instructor2,
  instructor3,
  instructor1_availability,
  instructor2_availability,
  instructor3_availability,
):
  instructors = [instructor1, instructor2, instructor3]
  availabilities = {
    instructor1: instructor1_availability,
    instructor2: instructor2_availability,
    instructor3: instructor3_availability,
  }

  for day in daily_schedules:
    date_str = day["date"]
    primary_instructor = _get_primary_instructor(date_str, *instructors)
    secondary_instructors = [i for i in instructors if i != primary_instructor]

    for slot, slot_data in day["slots"].items():
      if slot_data["type"] == "class":
        if _can_teach_class(availabilities[primary_instructor], date_str, slot):
          slot_data["instructor"] = primary_instructor["firstName"]
          _update_instructor_availability(availabilities[primary_instructor], date_str, slot, primary_instructor)
        else:
          for instructor in secondary_instructors:
            if _can_teach_class(availabilities[instructor], date_str, slot):
              slot_data["instructor"] = instructor["firstName"]
              _update_instructor_availability(availabilities[instructor], date_str, slot, instructor)
              break

  return daily_schedules


def _schedule_drives(
  daily_schedules,
  instructor1,
  instructor2,
  instructor3,
  instructor1_availability,
  instructor2_availability,
  instructor3_availability,
):
  instructors = [instructor1, instructor2, instructor3]
  availabilities = {
    instructor1: instructor1_availability,
    instructor2: instructor2_availability,
    instructor3: instructor3_availability,
  }

  for day in daily_schedules:
    date_str = day["date"]
    primary_instructor = _get_primary_instructor(date_str, *instructors)
    secondary_instructors = [i for i in instructors if i != primary_instructor]

    for slot, slot_data in day["slots"].items():
      if slot_data["type"] == "drive" and "instructor" not in slot_data:
        if _can_teach_drive(availabilities[primary_instructor], date_str, slot):
          slot_data["instructor"] = primary_instructor["firstName"]
          _update_instructor_availability(availabilities[primary_instructor], date_str, slot, primary_instructor)
        else:
          for instructor in secondary_instructors:
            if _can_teach_drive(availabilities[instructor], date_str, slot):
              slot_data["instructor"] = instructor["firstName"]
              _update_instructor_availability(availabilities[instructor], date_str, slot, instructor)
              break

  return daily_schedules


def _can_teach_class(availability, date_str, slot):
  if date_str not in availability or slot not in availability[date_str]:
    return False

  slot_availability = availability[date_str][slot]
  return slot_availability in [
    AVAILABILITY_MAPPING["Yes"],
    AVAILABILITY_MAPPING["Class Only"],
  ]


def _can_teach_drive(availability, date_str, slot):
  if date_str not in availability or slot not in availability[date_str]:
    return False

  slot_availability = availability[date_str][slot]
  return slot_availability in [
    AVAILABILITY_MAPPING["Yes"],
    AVAILABILITY_MAPPING["Drive Only"],
  ]

def _update_instructor_availability(availability, date_str, slot, instructor):
  if date_str in availability and slot in availability[date_str]:
    availability[date_str][slot] = AVAILABILITY_MAPPING["Scheduled"]

def _persist_instructor_availability(instructor, availability):
  schedule_row = app_tables.instructor_schedules.get(instructor=instructor)
  if schedule_row:
    schedule_row.update(current_seven_month_availability=availability)
