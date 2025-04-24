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

def json_to_csv(json_data, filename='converted_data.csv'):
    """
    Convert JSON to CSV with flexible nested structure
    
    :param json_data: JSON data (dict or string)
    :param filename: Desired filename for CSV
    :return: Media object of created CSV
    """
    # If json_data is a string, parse it
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    
    # Flatten the JSON
    flattened_data = flatten_json(json_data)
    
    # Create a string buffer to write CSV
    output = io.StringIO()
    
    # If no data, return None
    if not flattened_data:
        return None
    
    # Prepare CSV writer
    writer = csv.writer(output)
    
    # Extract headers and rows
    headers = sorted(set(key.split('_')[-1] for key in flattened_data.keys()))
    writer.writerow(['Attribute'] + headers)
    
    # Group flattened data by first-level key
    grouped_data = {}
    for full_key, value in flattened_data.items():
        # Split the key and get the meaningful parts
        key_parts = full_key.split('_')
        
        # If key has multiple parts, use all but the last
        if len(key_parts) > 1:
            primary_key = '_'.join(key_parts[:-1])
            last_key = key_parts[-1]
            
            if primary_key not in grouped_data:
                grouped_data[primary_key] = {}
            
            grouped_data[primary_key][last_key] = value
    
    # Write rows
    for primary_key, values in grouped_data.items():
        row = [primary_key]
        row.extend([values.get(header, '') for header in headers])
        writer.writerow(row)
    
    # Create media object
    csv_media = anvil.BlobMedia('text/csv', 
                                output.getvalue().encode('utf-8'), 
                                name=filename)
    
    # Add to files table
    app_tables.files.add_row(
        filename=filename,
        file=csv_media,
        file_type='CSV'
    )
    
    return csv_media

# Convenience wrapper
def convert_and_save_csv(json_data, filename='converted_data.csv'):
    """
    Wrapper function to convert JSON to CSV and add to files
    
    :param json_data: JSON data
    :param filename: Desired filename for the CSV
    :return: Media object of the created CSV
    """
    return json_to_csv(json_data, filename)


@anvil.server.callable
def convert_JSON_to_csv_and_save(json_data, filename):
    return json_to_csv(json_data, filename)
