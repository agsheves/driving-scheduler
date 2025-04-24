import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import json

@anvil.server.callable
def csv_to_structured_json(csv_file):
    """
    Convert a CSV file to a structured JSON format.
    
    :param csv_file: Path to the CSV file or CSV file object
    :return: Structured JSON dictionary
    """
    # Read the CSV file
    if isinstance(csv_file, str):
        print('CSV convert function has file')
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            data = list(reader)
    else:
        # If it's a file-like object from Anvil
        reader = csv.reader(csv_file.get_bytes().decode('utf-8').splitlines())
        data = list(reader)
    
    # Extract headers
    headers = data[0][1:]  # Column headers (excluding first column)
    row_headers = [row[0] for row in data[1:]]  # Row headers (first column)
    
    # Create structured JSON
    structured_data = {}
    for i, row in enumerate(data[1:], start=0):
        row_header = row_headers[i]
        row_data = {}
        
        # Create key-value pairs for this row
        for j, value in enumerate(row[1:], start=0):
            column_header = headers[j]
            row_data[column_header] = value
        
        structured_data[row_header] = row_data
    
    return structured_data

@anvil.server.callable
def convert_file_to_json(file):
  print(f'Running convert file to JSON with file')
  json_payload = csv_to_structured_json(file)
  print(json_payload)
  return json_payload

# Optional: Pretty print the JSON
def print_json(json_data):
    print(json.dumps(json_data, indent=2))
