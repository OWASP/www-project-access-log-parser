import re
import json
import time

def convert_to_clf(log_entry):
    clf_entry = f"{log_entry['ip']} {log_entry['user']} - [{time.strftime('%d/%b/%Y:%H:%M:%S', time.strptime(log_entry['date'], '%d/%b/%Y:%H:%M:%S'))}  ] \"{log_entry['request']}\" {log_entry['status']} {log_entry['size']}"
    return clf_entry

def parse_original_logs(original_logs):
    parsed_logs = []
    for original_log in original_logs:
        # Example parsing of JSON log entry
        try:
            parsed_log = {
                'ip': original_log['ip'],
                'user': original_log['user'],
                'date': original_log['date'],
                'request': original_log['request'],
                'status': original_log['status'],
                'size': original_log['size']
            }
            parsed_logs.append(parsed_log)
        except KeyError as e:
            print(f"KeyError: {e}. Skipping invalid log entry.")
    
    return parsed_logs

def parse_original_logs(original_logs, field_names):
    def extract_properties(log_entry, field_names):
        extracted_properties = {}
        for key, value in field_names.items():
            if isinstance(value, dict):
                # If the value is a dictionary, recursively extract properties
                extracted_properties[key] = extract_properties(log_entry[key], value)
            else:
                # Otherwise, extract the property from the current level
                extracted_properties[key] = log_entry[value]
        return extracted_properties

    parsed_logs = []

    for original_log in original_logs:
        try:
            parsed_log = extract_properties(original_log, field_names)
            parsed_logs.append(parsed_log)
        except KeyError as e:
            print(f"KeyError: {e}. Skipping invalid log entry.")

    return parsed_logs

def extract_values(input_str):
    # Correct the format of the input string
    data = {key: value for key, value in re.findall(r"(\w+): (\w+)", input_str)}
    return data

# Read JSON log entries from a file
def parseJSONLogs(file_path,output_file_path,fieldNames):
    # file_path = 'CLogs.json'
    # output_file_path = 'caddyLogsTemp.log'

    output_file_path=output_file_path+"jLogs"
    try:
        with open(file_path, 'r') as file:
            original_logs = json.load(file)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        exit()
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {file_path}")
        exit()

    # Parse and convert to CLF
    if fieldNames:
        parsed_logs=parse_original_logs(original_logs,json.loads(json.dumps(extract_values(fieldNames))))
    else:
        parsed_logs = parse_original_logs(original_logs)
    # Write CLF log entries to a file
    with open(output_file_path, 'w') as output_file:
        for parsed_log in parsed_logs:
            clf_log_entry = convert_to_clf(parsed_log)
            output_file.write(f"{clf_log_entry}\n")

    print(f"CLF log entries written to: {output_file_path}")
    return output_file_path
