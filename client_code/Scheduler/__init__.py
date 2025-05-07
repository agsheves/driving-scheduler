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
from datetime import date, time, datetime
import plotly.graph_objects as go
from ..globals import current_teen_driving_schedule

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
    self.merged_schedule = ""
    self.cohort_name = ""
    
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
    school_list = app_tables.schools.search()
    self.school_selector.items = [(s['school_name'], s['abbreviation']) for s in school_list]
    self.filter_instructors = False

    cohort_placeholder = [("Select a cohort", None)]
    current_cohorts = app_tables.cohorts.search()
    cohort_items = [(c['cohort_name'], c['cohort_name']) for c in current_cohorts]
    self.cohort_Selector.items = cohort_placeholder + cohort_items
    self.cohort_Selector.selected_value = None
    
    instructor_placeholder = [("Select an instructor", None)]
    self.instructors = app_tables.users.search(is_instructor=True)
    instructor_items = [(i['firstName'] + ' ' + i['surname'], i) for i in self.instructors]
    self.instructor_1_selector.items = instructor_placeholder + instructor_items
    self.instructor_2_selector.items = instructor_placeholder + instructor_items
    self.instructor_1_selector.selected_value = None
    self.instructor_2_selector.selected_value = None
    
    self.populate_instructor_filter_drop_down()
    self.refresh_schedule_display()


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

# ##############################################
# Schedule preparation and display

    
  def populate_instructor_filter_drop_down(self):
    """Populate the dropdown with available instructors"""
    # Get all instructors from the database
    instructors = app_tables.users.search(is_instructor=True)
    instructor_names = [f"{instructor['firstName']} {instructor['surname']}" for instructor in instructors]
    instructor_list_text = ", ".join(instructor_names)
    self.instructor_list.text = f"Instructors displayed: {instructor_list_text}"
    
    # Populate dropdown with instructor names
    self.instructor_filter_drop_down.items = [(i['firstName'] + ' ' + i['surname'], i) for i in instructors]
    
    # Select first instructor as default if available
    if self.instructor_filter_drop_down.items:
      self.instructor_filter_drop_down.selected_value = self.instructor_filter_drop_down.items[0][1]
    
    # Initially hide the dropdown since filtering is off by default
    self.instructor_filter_drop_down.visible = False
      
  def refresh_schedule_display(self):

    # Get selected instructors based on filter status
    if self.filter_instructors:
      # When filter is on, use the selected instructor
      if self.instructor_filter_drop_down.selected_value:
        selected_instructors = [self.instructor_filter_drop_down.selected_value]
        self.instructor_list.visible = False
  
    else:
      # When filter is off, get all instructors
      selected_instructors = list(app_tables.users.search(is_instructor=True))
      self.instructor_list.visible = True
    
    # Get data from server
    print("Getting data:\n")
    data = anvil.server.call('process_instructor_availability', selected_instructors)
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
    for row in data['z_values']:
        text_row = []
        for val in row:
            if val == 0:
                text_row.append('Unavailable')
            elif val == 1:
                text_row.append('Any')
            elif val == 2:
              text_row.append('Drive Only')
            elif val == 3:
              text_row.append('Class Only')
            else:
                text_row.append('')
        text_matrix.append(text_row)

    fig = go.Figure(data=go.Heatmap(
        z=data['z_values'],
        x=data['x_labels'],
        y=data['y_labels'],
        colorscale=[
            [0/3, 'DimGrey'],
            [1/3, 'RebeccaPurple'],
            [2/3, 'RebeccaPurple'],
            [3/3, 'RebeccaPurple']
        ],
        text=text_matrix,
        texttemplate="%{text}",
        showscale=False,
        bgcolor='white',
        zmin=0,
        zmax=3
    ))
    
    # Update layout - keeping it very minimal
    title_text = "Weekly Availability"
    if data['instructors']:
      title_text += f": {', '.join(data['instructors'])}"
    
    fig.update_layout(
        title=None,  # Remove title
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(
            side='top',
            tickangle=-45,
            tickfont=dict(color='black')
        ),
        yaxis=dict(
            tickfont=dict(color='black')
        )
    )
    
    # Set the plot's figure
    self.schedule_plot_complete.figure = fig
    self.schedule_plot_complete.visible = True

    
  def refresh_schedule_button_click(self, **event_args):
    # Used for testing
    self.refresh_schedule_display()
  
  def filter_schedule_switch_change(self, **event_args):
    self.filter_instructors = self.filter_schedule_switch.checked
    self.instructor_filter_drop_down.visible = self.filter_instructors
    self.refresh_schedule_display()

  def instructor_filter_drop_down_change(self, **event_args):
    self.filter_instructors = True
    self.refresh_schedule_display()

  def cohort_builder_button_click(self, **event_args):

    if not self.school_selector.selected_value:
        self.schedule_print_box.content = "Please select a school"
        return
        
    if not self.start_date:
        self.schedule_print_box.content = "Please select a start date"
        return
        
    # Convert the string date back to a date object for the API call
    start_date = datetime.strptime(self.start_date, "%m-%d-%Y").date()
    
    self.cohort_schedule = anvil.server.call('create_full_cohort_schedule', 
                              self.school_selector.selected_value, 
                              start_date, 
                              None)
    
    if self.cohort_schedule:
        self.cohort_name = self.cohort_schedule['cohort_name']
        formatted_output = f"Cohort Schedule: {self.cohort_schedule['cohort_name']}\n\n"
        
        #formatted_output += "Class Schedule:\n"
       # for class_slot in self.cohort_schedule['classes']:
            #formatted_output += f"Class {class_slot['class_number']}: {class_slot['date']} ({class_slot['day']})\n"
        
        #formatted_output += "\nDrive Schedule:\n"
        #for drive in self.cohort_schedule['drives']:
            #formatted_output += f"Pair {drive['pair_letter']}: {drive['date']} - Slot {drive['slot']} (Week {drive['week']})\n"
        
        formatted_output += f"\nSummary:\n"
        formatted_output += f"Number of Students: {self.cohort_schedule['num_students']}\n"
        formatted_output += f"Start Date: {self.cohort_schedule['start_date']}\n"
        formatted_output += f"End Date: {self.cohort_schedule['end_date']}"
        
        self.schedule_print_box.content = formatted_output
    else:
        self.schedule_print_box.content = "Error creating schedule"

  def school_selector_change(self, **event_args):
    self.selected_school = self.school_selector.selected_value

  def cohort_start_date_change(self, **event_args):
    start_date = self.cohort_start_date.date
    self.start_date = start_date.strftime("%m-%d-%Y")

  def export_cohort_button_click(self, **event_args):
    name = self.cohort_name
    anvil.server.call('export_merged_cohort_schedule', name)
    self.cohort_name = ""

  def create_availability_report_button_click(self, **event_args):
    anvil.server.call('generate_capacity_report')
    Notification("Your report is available in the file downloader")

  def cohort_Selector_change(self, **event_args):
    cohort = app_tables.cohorts.get(cohort_name=self.cohort_Selector.selected_value)
    self.cohort_name_label.text = f"Cohort selected: School - {cohort['school']}, Start date - {cohort['start_date']}"
    self.cohort = cohort

  def instructor_1_selector_change(self, **event_args):
    self.instructor1 = self.instructor_1_selector.selected_value
    
  def instructor_2_selector_change(self, **event_args):
    self.instructor2 = self.instructor_2_selector.selected_value

  def schedule_instructors_button_click(self, **event_args):
    instructor_allocation = anvil.server.call('schedule_instructors_for_cohort', self.cohort, self.instructor1, self.instructor2)
    self.scheduling_text_box.text = instructor_allocation

  def export_cohort_and_schedule_button_click(self, **event_args):
    name = self.cohort['cohort_name']
    anvil.server.call('export_merged_cohort_schedule', name)
    self.cohort = ""

  def download_availability_button_click(self, **event_args):
    anvil.server.call('export_instructor_eight_monthavailability')
