from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..Instructors import Instructors
from ..Scheduler import Scheduler
from ..file_transfer import file_transfer

class Frame(FrameTemplate):
  def __init__(self, display_form=None, **properties):
    self.init_components(**properties)
    
    anvil.users.login_with_form()
    if display_form is None:
      self.dynamic_panel_1.add_component(Scheduler())
    else:
      self.dynamic_panel_1.add_component(display_form())

    #Set the Plotly plots template to match the theme of the app
    Plot.templates.default = "rally"
    
    #When the app starts up, the Scheduler form is opened by default
    #self.dynamic_panel_1.add_component(Scheduler())
    #Change the color of the selected page_link to indicate that the page that has been selected


  def signout_link_click(self, **event_args):
    anvil.users.logout()
    open_form('Logout')

  def schedule_page_link_click(self, **event_args):
    self.dynamic_panel_1.clear()
    self.dynamic_panel_1.add_component(Scheduler())
    self.schedule_page_link.background = app.theme_colors['Primary Container']
    self.instructor_page_link.background = "transparent"
    self.file_transfer_link.background = "transparent"
    

  def instructor_page_link_click(self, **event_args):
    self.dynamic_panel_1.clear()
    self.dynamic_panel_1.add_component(Instructors())
    self.instructor_page_link.background = app.theme_colors['Primary Container']
    self.schedule_page_link.background = "transparent"
    self.file_transfer_link.background = "transparent"

  def file_transfer_link_click(self, **event_args):
    self.dynamic_panel_1.clear()
    self.dynamic_panel_1.add_component(file_transfer())
    self.file_transfer_link.background = app.theme_colors['Primary Container']
    self.schedule_page_link.background = "transparent"
    self.instructor_page_link.background = "transparent"









