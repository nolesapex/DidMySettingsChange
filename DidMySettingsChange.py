import json
import os
import subprocess
import time
import sys
import tkinter as tk
import customtkinter as ctk

# File paths
CONFIG_FILE = 'config.json'
ALL_SETTINGS_FILE = 'all_settings.json'
DATABASE_FILE = 'settings_database.json'
LOG_FILE = 'settings_log.txt'

# Load configuration
def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Load saved settings
def load_database():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save current settings
def save_database(database):
    with open(DATABASE_FILE, 'w') as file:
        json.dump(database, file, indent=4)

# Use PowerShell to check a Windows registry setting
def check_setting(setting):
    command = f'powershell -Command "Get-ItemProperty -Path {setting["path"]} -Name {setting["name"]} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty {setting["name"]}"'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip(), result.returncode

# Compare settings
def check_settings(config, database):
    changes = []
    current_settings = {}

    for setting_name, setting_info in config.items():
        current_value, return_code = check_setting(setting_info)

        if return_code != 0:
            if setting_name.lower() == 'recall':
                print("Warning: Windows recall feature not found, skipping.")
            continue

        current_settings[setting_name] = current_value

        if setting_name in database and current_value != database[setting_name]:
            changes.append((setting_name, current_value, database[setting_name]))

    return changes, current_settings

# Log to file
def log_results(changes):
    with open(LOG_FILE, 'a') as log_file:
        for setting, current, expected in changes:
            log_file.write(f"[CHANGE DETECTED] {setting}: Current={current}, Previous={expected}\n")

# Shared monitoring logic
def monitor_settings(mode, output_widget=None):
    config_file = ALL_SETTINGS_FILE if mode == 'all' else CONFIG_FILE

    if not os.path.exists(config_file):
        msg = f"Configuration file '{config_file}' not found!"
        if output_widget:
            output_widget.insert(tk.END, msg + "\n")
        else:
            print(msg)
        return

    config = load_config(config_file)
    database = load_database()

    if not os.path.exists(DATABASE_FILE):
        _, current_settings = check_settings(config, {})
        save_database(current_settings)
        msg = "Initial setup complete. Settings saved."
        if output_widget:
            output_widget.insert(tk.END, msg + "\n")
        else:
            print(msg)
        return

    changes, current_settings = check_settings(config, database)
    save_database(current_settings)

    if changes:
        output = "Changes detected:\n"
        for setting, current, expected in changes:
            output += f" - {setting}: Current={current}, Previous={expected}\n"
        log_results(changes)
    else:
        output = "No changes detected.\n"

    if output_widget:
        output_widget.insert(tk.END, output + "\n")
        output_widget.see(tk.END)
    else:
        print(output)

# GUI mode using Tkinter
def run_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    window = ctk.CTk()
    window.title("DidMySettingsChange")
    window.geometry("720x480")

    label = ctk.CTkLabel(window, text="🛡️ DidMySettingsChange", font=("Helvetica", 18))
    label.pack(pady=10)

    output_text = ctk.CTkTextbox(window, wrap="word", width=680, height=320)
    output_text.pack(padx=10, pady=10, fill="both", expand=True)

    def monitor_privacy():
        output_text.insert("end", "Checking privacy settings...\n")
        monitor_settings('privacy', output_text)

    def monitor_all():
        output_text.insert("end", "Checking all settings...\n")
        monitor_settings('all', output_text)

    button_frame = ctk.CTkFrame(window)
    button_frame.pack(pady=5)

    btn_privacy = ctk.CTkButton(button_frame, text="Monitor Privacy Settings", command=monitor_privacy, width=200)
    btn_all = ctk.CTkButton(button_frame, text="Monitor All Settings", command=monitor_all, width=200)

    btn_privacy.grid(row=0, column=0, padx=10)
    btn_all.grid(row=0, column=1, padx=10)

    window.mainloop()

# CLI mode
def run_cli():
    print("Monitor 'all' settings or just 'privacy' settings? (all/privacy): ")
    choice = input().strip().lower()

    if choice not in ['all', 'privacy']:
        print("Invalid choice. Exiting.")
        return

    monitor_settings(choice)

# Entry point
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        run_cli()
    else:
        run_gui()
