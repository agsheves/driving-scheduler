from ._anvil_designer import ItemTemplate2Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate2(ItemTemplate2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.file_name.text = self.item['filename']
    self.contents_label.text = self.item['file_type']
    

    # Any code you write here will run before the form opens.

  def file_downloader_change(self, file, **event_args):
    # save file
    pass
