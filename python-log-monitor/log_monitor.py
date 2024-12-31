import os
import re
import requests
import json
from datetime import datetime
import time

# Corrected path to the PostgreSQL log directory (update to match Docker volume path)
LOG_DIR = r'C:\Program Files\PostgreSQL\17\data\log'

# Updated log pattern
LOG_PATTERN = r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} CET) \[(?P<pid>\d+)\].*'

# Updated line start pattern
LINE_START_PATTERN = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} CET \[\d+\]'


# Default timestamp if none is found
DEFAULT_TIMESTAMP = "2024-12-24 00:00:00.000 CET"

# Loki URL
LOKI_URL = "http://localhost:3100/loki/api/v1/push"

# Read logs and process them
def process_log_file():
    while True:
        for log_file in os.listdir(LOG_DIR):
            log_path = os.path.join(LOG_DIR, log_file)

            # Check if the path is a file before opening it
            if os.path.isfile(log_path):
                with open(log_path, 'r') as f:
                    previous_line = ""
                    for line in f:
                        # Check if the line starts with a timestamp (i.e., a new log entry)
                        if re.match(LINE_START_PATTERN, line):
                            # If the previous line exists and isn't part of the current log entry, save it
                            if previous_line:
                                save_log_entry(previous_line)

                            # Start a new log entry
                            previous_line = line.strip()  # Store the current line

                        else:
                            # If the line doesn't start with a timestamp, it's part of the ongoing log entry
                            previous_line += " " + line.strip()

                    # After processing all lines, save the last log entry
                    if previous_line:
                        save_log_entry(previous_line)

        # Here we can break the loop for testing purposes after processing once
        break

def save_log_entry(log_entry):
    # Extract the timestamp from the log entry
    match = re.match(LOG_PATTERN, log_entry)
    
    if match:
        timestamp = match.group('timestamp')
    else:
        # If no timestamp found, use the default timestamp
        timestamp = DEFAULT_TIMESTAMP

    # Send the log entry to Loki
    send_log_to_loki(timestamp, log_entry)

def send_log_to_loki(timestamp, log_entry):
    # Convert timestamp to ISO 8601 format with nanoseconds
    datetime_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f CET")
    timestamp_ns = int(datetime_obj.timestamp() * 1e9)

    # Get current time and use it if the log timestamp is too old
    current_time_ns = int(time.time() * 1e9)

    # If the log timestamp is too far behind, use the current timestamp (no max limit)
    if timestamp_ns < current_time_ns:
        print(f"Log timestamp is too old. Using current timestamp instead.")
        timestamp_ns = current_time_ns

    # Format log entry for Loki
    log_data = {
        "streams": [
            {
                "stream": {
                    "job": "postgresql-logs",  # Labels for the log stream
                    "source": "postgresql"
                },
                "values": [
                    [
                        str(timestamp_ns),  # Timestamp in nanoseconds
                        log_entry  # Log message
                    ]
                ]
            }
        ]
    }

    # Send the log to Loki
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(LOKI_URL, data=json.dumps(log_data), headers=headers)

        if response.status_code == 204:
            print(f"Log sent successfully: {log_entry}")
        else:
            print(f"Failed to send log to Loki: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error sending log to Loki: {e}")
# Main processing loop
if __name__ == "__main__":
    process_log_file()