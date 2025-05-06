from ._anvil_designer import InstructorsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Instructors(InstructorsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    instructors = app_tables.users.search(is_instructor=True)
    self.instructor_repeating_panel.items = instructors
