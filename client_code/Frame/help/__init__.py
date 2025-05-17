from ._anvil_designer import helpTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class help(helpTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    help_items = app_tables.help_items.search(youtube_url=q.not_(None))
    self.help_items_panel.items = help_items

    # Any code you write here will run before the form opens.
