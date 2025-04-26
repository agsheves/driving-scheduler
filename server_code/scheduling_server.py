import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta


@anvil.server.callable
def process_instuctor_availability(instructors, start_date=None):
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime, timedelta
    
    if start_date is None:
        start_date = datetime.now().date()
    
    all_records = []
    
    for instructor in instructors:
        try:
            # Access the correct key structure
            instructor_schedule = app_tables.instructor_schedules.get(instructor=instructor)
            weekly_data = instructor_schedule['weekly_availability']
            if weekly_data is None or weekly_data is "":
              continue
            print(f"Found data for {instructor['firstName']}: {weekly_data.keys()}")
        except (KeyError, TypeError) as e:
            weekly_data = {}
            print(f"Error getting data for {instructor['firstName']}: {e}")
            continue  # Skip this instructor if no data
            
        availability_mapping = {
            'Unavailable': 0,
            'Yes - Any': 1,
            'Yes - Drive': 2,
            'Yes - Class': 3,
            'Booked': 4
        }
        
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        # Process each day directly from weekly_data
        for day_index, day_name in enumerate(days_of_week):
            try:
                day_availability = weekly_data['weekly_availability'][day_name]
                print(f"Processing {day_name} for {instructor['firstName']}: {len(day_availability)} time slots")
            except (KeyError, TypeError) as e:
                print(f"No data for {day_name}: {e}")
                continue
                
            for hour_str, status in day_availability.items():
                try:
                    value = availability_mapping.get(status, -1)
                    
                    all_records.append({
                        'instructor': instructor['firstName'],
                        'day_index': day_index,
                        'day_name': day_name,
                        'hour': hour_str,
                        'status': status,
                        'value': value
                    })
                except (KeyError, TypeError) as e:
                    print(f"Error with hour {hour_str}: {e}")
                    continue
        
        print(f"Added {instructor['firstName']}")
    
    # Process the data with pandas
    df = pd.DataFrame(all_records)
    
    # Debug print to see sample of the dataframe in terminal
    print(f"Total records: {len(df)}")
    print("Sample of DataFrame (first 20 records):")
    print(df.head(20))
    
    if df.empty:
        return None
    
    # Convert hours to sortable format (removing the ":00" suffix)
    df['hour_24'] = df['hour'].apply(lambda x: int(x.split(':')[0]))
    
    # Create a pivot table for the heatmap: hours vs days
    pivot_df = df.pivot_table(
        values='value',
        index='hour_24',
        columns='day_name',
        aggfunc='first'
    )
    print(pivot_df)
    return {
        'z_values': pivot_df.values.tolist(),
        'x_labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'y_labels': [f"{h}:00" for h in pivot_df.index.tolist()],
        'instructors': [i['firstName'] for i in instructors]
    }
