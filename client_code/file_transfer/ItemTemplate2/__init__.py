from ._anvil_designer import ItemTemplate2Template
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.media


class ItemTemplate2(ItemTemplate2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.file_name.text = self.item['filename']
    self.contents_label.text = self.item['file_type']


  def download_link_click(self, **event_args):
    file = self.item['file']
    anvil.media.download(file)


  def delete_file_link_click(self, **event_args):
    file_name = self.item['filename']
    file_row = app_tables.files.get(filename=file_name)
    c = confirm(f"Confirm you want to delete file {file_row['filename']}")
    if c is True:
      file_row.delete()
      open_form('Frame','file_transfer')
    
    

