from ._anvil_designer import file_transferTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.media


class file_transfer(file_transferTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.file_contents_drop_down.items = ["User Schedule", "User Profile", "Group Schedule"]
    self.upload_file = None  # Initialize file variable
    self.file_repeating_panel.items = app_tables.files.search()
    
  def file_uploader_change(self, file, **event_args):
    self.upload_file_name.text = file.name
    self.upload_file = file  # Store file in class variable
    
  def upload_file_button_click(self, **event_args):
    if self.upload_file and self.upload_file_name.text:
      filename = self.upload_file_name.text
      app_tables.files.add_row(
        filename=filename, 
        file=self.upload_file, 
        file_type=self.file_contents_drop_down.selected_value
      )
      self.upload_file = None
      self.upload_file_name.text = ""

  def close_button_click(self, **event_args):
    from ..Frame import Frame
    open_form('Frame')
    

