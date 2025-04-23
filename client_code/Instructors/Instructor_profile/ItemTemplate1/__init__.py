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
    self.tues_availability.items = self.item['availability']
    self.wed_availability.items = self.item['availability']
    self.thurs_availability.items = self.item['availability']
    self.fri_availability.items = self.item['availability']
    self.sat_availability.items = self.item['availability']
    self.sun_availability.items = self.item['availability']



    

