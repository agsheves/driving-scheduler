import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


availability_time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
days_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
days_short = ["mon", "tues", "wed", "thurs", "fri", "sat", "sun"]
availability_codes = ["Unavailable", "Yes - Drive", "Yes - Class", "Yes - Any"]
