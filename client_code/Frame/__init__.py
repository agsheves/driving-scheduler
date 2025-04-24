from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..Instructors import Instructors
from ..Scheduler import Scheduler
from ..file_transfer import file_transfer

class Frame(FrameTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    
    # ⚠️  Enable this for testing
    #anvil.users.login_with_form()

    #Set the Plotly plots template to match the theme of the app
    Plot.templates.default = "rally"
    #When the app starts up, the Scheduler form is opened by defauly
    #self.content_panel.add_component(Scheduler())
    #Change the color of the selected page_link to indicate that the page that has been selected
    self.schedule_page_link.background = app.theme_colors['Primary Container']


  # ⚠️ If using the Users service, uncomment this code to log out the user:
  def signout_link_click(self, **event_args):
    pass
  
  #   anvil.users.logout()
  #   open_form('Logout')

  def schedule_page_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(Scheduler())
    self.schedule_page_link.background = app.theme_colors['Primary Container']
    self.instructor_page_link.background = "transparent"
    self.file_transfer_link.background = "transparent"
    

  def instructor_page_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(Instructors())
    self.instructor_page_link.background = app.theme_colors['Primary Container']
    self.schedule_page_link.background = "transparent"
    self.file_transfer_link.background = "transparent"

  def file_transfer_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(file_transfer())
    self.file_transfer_link.background = app.theme_colors['Primary Container']
    self.schedule_page_link.background = "transparent"
    self.instructor_page_link.background = "transparent"

    









