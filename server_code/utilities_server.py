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

###########################################################
# Data import function to take CSV data and convert to JSON.

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

###########################################################
# Data export function to take JSON data and convert to CSV

def flatten_json(data, parent_key='', sep='_'):
    """
    Recursively flatten a nested JSON dictionary
    
    :param data: Nested dictionary to flatten
    :param parent_key: Key from parent level (for recursion)
    :param sep: Separator for nested keys
    :return: Flattened dictionary
    """
    items = []
    
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            # If value is a dictionary, recurse
            if isinstance(v, dict):
                items.extend(flatten_json(v, new_key, sep=sep).items())
            # If value is a list, convert each item
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    items.extend(flatten_json({str(i): item}, new_key, sep=sep).items())
            # If simple value, add to items
            else:
                items.append((new_key, v))
    else:
        # If input is not a dictionary, return it as is
        return {parent_key: data}
    
    return dict(items)

def export_json_to_csv(json_data, filename='schedule.csv'):

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Get all unique column headers
    all_headers = set()
    for _, event_data in json_data.items():
        all_headers.update(event_data.keys())
    
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
    csv_media = anvil.media.BlobMedia('text/csv', 
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
