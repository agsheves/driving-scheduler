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

def json_to_csv(json_data, filename='converted_data.csv'):
    """
    Convert a structured JSON to CSV and add to app files table
    
    :param json_data: Structured JSON dictionary
    :param filename: Desired filename for the CSV
    :return: Media object of the created CSV
    """
    # Create a string buffer to write CSV
    output = io.StringIO()
    
    # If JSON is empty, return None
    if not json_data:
        return None
    
    # Get column headers from the first item's keys
    first_row_data = list(json_data.values())[0]
    headers = ['Time'] + list(first_row_data.keys())
    
    # Create CSV writer
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data rows
    for time, row_data in json_data.items():
        row = [time] + [row_data.get(header, '') for header in headers[1:]]
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


@anvil.server.callable
def convert_JSON_to_csv_and_save(json_data, filename):
    return json_to_csv(json_data, filename)
