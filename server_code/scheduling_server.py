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
        
        business_hours = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00']
        for day_index, day_name in enumerate(days_of_week):
            try:
                day_availability = weekly_data['weekly_availability'][day_name]
                print(f"Processing {day_name} for {instructor['firstName']}: {len(day_availability)} time slots")
            except (KeyError, TypeError) as e:
                print(f"No data for {day_name}: {e}")
                continue
                
            for hour_str, status in day_availability.items():
              if hour_str in business_hours:
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
        columns=['day_name', 'instructor'],
        aggfunc='first'
    )
    pivot_df = pivot_df.sort_index(ascending=False)

    # Create flattened day-instructor labels
    flat_columns = []
    for col in pivot_df.columns:
        day, instructor = col
        flat_columns.append((day, instructor, f"{day.capitalize()} - {instructor}"))
    
    # Define day order
    day_order = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    
    # Sort flat columns by day first, then by instructor
    flat_columns.sort(key=lambda x: (day_order[x[0]], x[1]))
    
    # Extract just the formatted labels
    flat_labels = [item[2] for item in flat_columns]
    
    # Reorder the z-values to match the new column order
    z_values_ordered = []
    for row in pivot_df.values.tolist():
        # Create a new row with values in the correct order
        new_row = []
        for day, instructor, _ in flat_columns:
            col_idx = list(pivot_df.columns).index((day, instructor))
            new_row.append(row[col_idx])
        z_values_ordered.append(new_row)
    
    # Return the properly ordered data
    return {
        'z_values': z_values_ordered,
        'x_labels': flat_labels,
        'y_labels': [f"{h}:00" for h in pivot_df.index.tolist()],
        'instructors': [i['firstName'] for i in instructors]
    }
