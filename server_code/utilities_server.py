import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import json
import io
import anvil.media
from collections import OrderedDict

###########################################################
# General data import function to take CSV data and convert to JSON.

@anvil.server.callable
def csv_to_structured_json(csv_file):
    if isinstance(csv_file, str):
        print('CSV convert function has file')
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            data = list(reader)
    else:
        reader = csv.reader(csv_file.get_bytes().decode('utf-8').splitlines())
        data = list(reader)

    headers = data[0][1:]  # Column headers (excluding first column)
    row_headers = [row[0] for row in data[1:]]  # Row headers (first column)

    structured_data = {}
    for i, row in enumerate(data[1:], start=0):
        row_header = row_headers[i]
        row_data = {}

        for j, value in enumerate(row[1:], start=0):
            column_header = headers[j]
            row_data[column_header] = value
        
        structured_data[row_header] = row_data
    
    return structured_data

@anvil.server.callable
def convert_csv_to_json(file):
  json_payload = csv_to_structured_json(file)
  print(json_payload)
  return json_payload

# Optional: Pretty print the JSON
def print_json(json_data):
    print(json.dumps(json_data, indent=2))

# Drive schedule spoecifc import function

@anvil.server.callable
def convert_schedule_csv_to_json(csv_file):
    if isinstance(csv_file, str):
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    else:
        content = csv_file.get_bytes().decode('utf-8')
        reader = csv.DictReader(content.splitlines())
        data = list(reader)
    
    structured_data = {}
    
    for row in data:
        # Use the "Title" field as the main key
        title = row.pop('Title', None)
        if title:
            # Add all other columns as properties
            structured_data[title] = {k: v for k, v in row.items() if k}
    
    return structured_data

@anvil.server.callable
def update_teen_drive_schedule(file):
    json_payload = convert_schedule_csv_to_json(file)
    current_variables = app_tables.global_variables_edit_with_care.get(version='latest')
    
    if current_variables:
        current_schedule = current_variables['current_teen_driving_schedule']
        current_variables.update(
            previous_teen_driving_schedule=current_schedule,
            current_teen_driving_schedule=json_payload
        )
        return True
    else:
        app_tables.global_variables_edit_with_care.add_row(
            version='latest',
            current_teen_driving_schedule=json_payload
        )
        return True
  

###########################################################
# Data export function to take JSON data and convert to CSV

def export_json_to_csv(json_data, filename='schedule.csv'):
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Convert JSON to OrderedDict to preserve order
    json_data = OrderedDict(json_data)
    
    # Get all unique column headers
    all_headers = set()
    for _, event_data in json_data.items():
        all_headers.update(event_data.keys())
    all_headers = sorted(all_headers)
    # Write the header row
    writer.writerow(["Title"] + list(all_headers))
    
    # Write each item as a row
    for event_id, event_data in json_data.items():
        row = [event_id]  # Event ID (e.g., "Drive 1") as first column
        
        # Add data for each header
        for header in all_headers:
            row.append(event_data.get(header, ''))
        
        writer.writerow(row)
    
    # Create media object
    csv_media = anvil.BlobMedia('text/csv', 
                                 output.getvalue().encode('utf-8'), 
                                 name=filename)

    app_tables.files.add_row(
        filename=filename,
        file=csv_media,
        file_type='CSV'
    )
  

@anvil.server.callable
def convert_JSON_to_csv_and_save(json_data, filename):
    return export_json_to_csv(json_data, filename) 

