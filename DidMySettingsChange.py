import json
import os
import subprocess
import time
import sys

# Define the settings file paths
CONFIG_FILE = 'config.json'
DATABASE_FILE = 'settings_database.json'
LOG_FILE = 'settings_log.txt'

# Load the configuration from config.json
def load_config():
    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)

# Load the last saved settings from the database
def load_database():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as file:
            return json.load(file)
    else:
        return {}

# Save the current settings to the database
def save_database(database):
    with open(DATABASE_FILE, 'w') as file:
        json.dump(database, file, indent=4)

# Check a specific setting's current value using PowerShell
def check_setting(setting):
    command = f'powershell -Command "Get-ItemProperty -Path {setting["path"]} -Name {setting["name"]} | Select-Object -ExpandProperty {setting["name"]}"'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip()

# Compare the current value with the expected value
def check_settings(config, database):
    changes = []
    current_settings = {}
    
    for setting_name, setting_info in config.items():
        current_value = check_setting(setting_info)
        current_settings[setting_name] = current_value
        
        if setting_name in database and current_value != database[setting_name]:
            changes.append((setting_name, current_value, database[setting_name]))
    
    return changes, current_settings

# Log the results to a file
def log_results(changes):
    with open(LOG_FILE, 'a') as log_file:
        for setting, current_value, expected_value in changes:
            log_file.write(f"[CHANGE DETECTED] Setting: {setting}, Current Value: {current_value}, Expected Value: {expected_value}\n")

# Fancy print with animation
def fancy_print(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.05)
    print("")

# Main function
def main():
    # Load configuration
    if not os.path.exists(CONFIG_FILE):
        print(f"Configuration file '{CONFIG_FILE}' not found. Please create it and specify the settings to monitor.")
        return
    
    config = load_config()
    database = load_database()
    
    # If the database file doesn't exist, create it
    if not os.path.exists(DATABASE_FILE):
        fancy_print("No JSON detected! Setting up JSON...")
        _, current_settings = check_settings(config, {})
        save_database(current_settings)
        print("Initial settings saved to database.")
        return
    
    # Check settings
    changes, current_settings = check_settings(config, database)
    
    # Save current settings to the database
    save_database(current_settings)
    
    # Report results
    if changes:
        print("Changes detected in the following settings:")
        for setting, current_value, expected_value in changes:
            print(f" - {setting}: Current Value = {current_value}, Expected Value = {expected_value}")
        log_results(changes)
    else:
        print("No changes detected in the monitored settings.")

if __name__ == "__main__":
    main()
