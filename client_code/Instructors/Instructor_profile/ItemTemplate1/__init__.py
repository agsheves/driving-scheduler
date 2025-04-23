from ._anvil_designer import ItemTemplate1Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate1(ItemTemplate1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    self.hour_label.text = self.item['time']
    
    self.mon_availability.items = self.item['availability']
    self.mon_availability.set_event_handler('change', self.universal_dropdown_change)
    self.tues_availability.items = self.item['availability']
    self.tues_availability.set_event_handler('change', self.universal_dropdown_change)
    self.wed_availability.items = self.item['availability']
    self.wed_availability.set_event_handler('change', self.universal_dropdown_change)
    self.thurs_availability.items = self.item['availability']
    self.thurs_availability.set_event_handler('change', self.universal_dropdown_change)
    self.fri_availability.items = self.item['availability']
    self.fri_availability.set_event_handler('change', self.universal_dropdown_change)
    self.sat_availability.items = self.item['availability']
    self.sat_availability.set_event_handler('change', self.universal_dropdown_change)
    self.sun_availability.items = self.item['availability']
    self.sun_availability.set_event_handler('change', self.universal_dropdown_change)

  def color_code_dropdown(self, value):
      if value:
          if 'Drive Only' in value:
              return 'blue'
          elif 'Class Only' in value:
              return 'blue'
          elif 'Drive or Class' in value:
              return 'purple'
          elif 'Unavailable' in value:
              return 'lightgray'
          else:
              return 'white'  # Default color
      else:
          return 'white'  # Default if no value
  
  # Universal dropdown change handler
  def universal_dropdown_change(self, **event_args):
      # Get the dropdown that triggered the event
      dropdown = event_args['sender']
      
      # Get the selected value
      selected_value = dropdown.selected_value
      
      # Apply the color to the dropdown background
      color = self.color_code_dropdown(selected_value)
      print(color)
      if color != 'lightgray':
        dropdown.foreground = '#ffffff'
      dropdown.background = color



    

