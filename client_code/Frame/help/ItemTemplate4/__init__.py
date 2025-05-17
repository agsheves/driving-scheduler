from ._anvil_designer import ItemTemplate4Template
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class ItemTemplate4(ItemTemplate4Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.item_title.text = self.item['title']
    self.item_description.text = self.item['description']
    self.item_video_url.youtube_id = self.item['youtube_url']
    # Any code you write here will run before the form opens.
