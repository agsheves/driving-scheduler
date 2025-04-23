from ._anvil_designer import instructor_repeating_panelTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class instructor_repeating_panel(instructor_repeating_panelTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.name_label.text = f"{self.item['firstName']} {self.item['surname']}"

    

    # Any code you write here will run before the form opens.

  def schedule_link_click(self, **event_args):
    instructorID = self.item['instructorID']
    from ...Scheduler import Scheduler
    alert(content = Scheduler()(instructorID = instructorID), large=True, dismissible=True)

  def profile_link_click(self, **event_args):
    instructorID = self.item['instructorID']
    from ..Instructor_profile import Instructor_profile
    open_form('Instructors.Instructor_profile', instructorID)