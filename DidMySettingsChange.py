import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import tkinter as tk

# File paths
CONFIG_FILE = 'config.json'
ALL_SETTINGS_FILE = 'all_settings.json'
DATABASE_FILE = 'settings_database.json'
LOG_FILE = 'settings_log.txt'


def stringify(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def emit_message(message: str, output_widget: Optional[tk.Text]) -> None:
    if output_widget:
        try:
            previous_state = output_widget.cget("state")  # type: ignore[call-arg]
        except (tk.TclError, AttributeError):
            previous_state = "normal"

        if previous_state == "disabled":
            try:
                output_widget.configure(state="normal")  # type: ignore[call-arg]
            except (tk.TclError, AttributeError):
                previous_state = "normal"

        output_widget.insert(tk.END, message + "\n")
        output_widget.see(tk.END)

        if previous_state == "disabled":
            try:
                output_widget.configure(state="disabled")  # type: ignore[call-arg]
            except (tk.TclError, AttributeError):
                pass
    else:
        print(message)

class ConfigurationError(Exception):
    """Raised when the configuration file cannot be loaded or is invalid."""


@dataclass
class SettingChange:
    name: str
    current: str
    expected: Optional[str] = None
    previous: Optional[str] = None

    def format_for_output(self) -> str:
        parts = [f"{self.name}: Current={self.current}"]
        if self.expected is not None:
            parts.append(f"Expected={self.expected}")
        if self.previous is not None:
            parts.append(f"Previous={self.previous}")
        return ", ".join(parts)


def load_config(file_path: str) -> Dict[str, Dict[str, str]]:
    """Load and validate the configuration file."""
    if not os.path.exists(file_path):
        raise ConfigurationError(f"Configuration file '{file_path}' not found.")

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Configuration file '{file_path}' is not valid JSON: {exc}.") from exc

    validate_config(config)
    return config

# Load saved settings
def load_database():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            # If the database becomes corrupted, fall back to a clean state.
            return {}
    return {}


def validate_config(config: Dict[str, Dict[str, str]]) -> None:
    """Ensure each configured setting contains the required metadata."""
    errors: List[str] = []
    for setting_name, setting_info in config.items():
        if not isinstance(setting_info, dict):
            errors.append(f"Setting '{setting_name}' must be an object.")
            continue

        for key in ("path", "name"):
            value = setting_info.get(key)
            if not value or not isinstance(value, str):
                errors.append(f"Setting '{setting_name}' is missing a string '{key}'.")

        expected_value = setting_info.get("expected_value")
        if expected_value is not None and not isinstance(expected_value, (str, int, float, bool)):
            errors.append(
                f"Setting '{setting_name}' has an unsupported 'expected_value' type: {type(expected_value).__name__}."
            )

    if errors:
        raise ConfigurationError("\n".join(errors))

# Save current settings
def save_database(database):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as file:
        json.dump(database, file, indent=4)

# Use PowerShell to check a Windows registry setting
def check_setting(setting):
    if shutil.which('powershell') is None and shutil.which('pwsh') is None:
        return '', 1

    path = setting["path"]
    name = setting["name"]
    command = (
        f"$item = Get-ItemProperty -Path '{path}' -Name '{name}' -ErrorAction SilentlyContinue;"
        "if ($null -eq $item) { exit 1 };"
        f"$value = $item.{name};"
        "if ($null -eq $value) { exit 1 };"
        "Write-Output $value"
    )

    powershell = shutil.which('powershell') or shutil.which('pwsh')
    result = subprocess.run(
        [powershell, '-NoProfile', '-Command', command],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode

# Compare settings
def check_settings(
    config: Dict[str, Dict[str, str]], database: Dict[str, str]
) -> Tuple[List[SettingChange], Dict[str, str], List[str]]:
    changes: List[SettingChange] = []
    current_settings: Dict[str, str] = {}
    warnings: List[str] = []

    for setting_name, setting_info in config.items():
        current_value, return_code = check_setting(setting_info)

        if return_code != 0:
            if setting_name.lower() == 'recall':
                warnings.append("Warning: Windows recall feature not found, skipping.")
            else:
                warnings.append(f"Warning: Unable to read setting '{setting_name}'.")
            continue

        current_value = stringify(current_value.strip())
        current_settings[setting_name] = current_value

        previous_value_raw = database.get(setting_name)
        previous_value = stringify(previous_value_raw).strip() if previous_value_raw is not None else None

        expected_value_raw = setting_info.get("expected_value")
        expected_value = stringify(expected_value_raw).strip() if expected_value_raw is not None else None

        mismatched_expected = expected_value is not None and current_value != expected_value
        mismatched_previous = previous_value is not None and current_value != previous_value

        if mismatched_expected or mismatched_previous:
            changes.append(
                SettingChange(
                    name=setting_name,
                    current=current_value,
                    expected=expected_value if mismatched_expected else None,
                    previous=previous_value if mismatched_previous else None,
                )
            )

    return changes, current_settings, warnings

# Log to file
def log_results(changes):
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        for change in changes:
            log_file.write(f"[CHANGE DETECTED] {change.format_for_output()}\n")

# Shared monitoring logic
def monitor_settings(mode, output_widget=None):
    mode = mode.lower()
    if mode not in {'all', 'privacy'}:
        emit_message(f"Unknown monitoring mode '{mode}'.", output_widget)
        return

    config_file = ALL_SETTINGS_FILE if mode == 'all' else CONFIG_FILE

    try:
        config = load_config(config_file)
    except ConfigurationError as exc:
        emit_message(str(exc), output_widget)
        return

    database_exists = os.path.exists(DATABASE_FILE)
    database = load_database() if database_exists else {}

    if not database_exists or not database:
        _, current_settings, warnings = check_settings(config, {})
        save_database(current_settings)
        emit_message("Initial setup complete. Settings saved.", output_widget)
        for warning in warnings:
            emit_message(warning, output_widget)
        return

    changes, current_settings, warnings = check_settings(config, database)
    save_database(current_settings)

    for warning in warnings:
        emit_message(warning, output_widget)

    if changes:
        emit_message("Changes detected:", output_widget)
        for change in changes:
            emit_message(f" - {change.format_for_output()}", output_widget)
        log_results(changes)
    else:
        emit_message("No changes detected.", output_widget)

# GUI mode using Tkinter
def run_gui():
    try:
        import customtkinter as ctk
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "CustomTkinter is required for the GUI. Install it with 'pip install customtkinter'."
        ) from exc

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    window = ctk.CTk()
    window.title("DidMySettingsChange")
    window.geometry("860x540")
    window.minsize(720, 480)

    main_frame = ctk.CTkFrame(window, fg_color="#121212", corner_radius=18)
    main_frame.pack(fill="both", expand=True, padx=24, pady=24)

    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=12, pady=(18, 6))

    title_font = ctk.CTkFont(size=28, weight="bold")
    subtitle_font = ctk.CTkFont(size=14)

    title_label = ctk.CTkLabel(header_frame, text="🛡️ DidMySettingsChange", font=title_font)
    title_label.pack(anchor="w")

    subtitle_label = ctk.CTkLabel(
        header_frame,
        text="Monitor your Windows privacy and system settings with a sleek dark interface.",
        font=subtitle_font,
        text_color="#a0a0a0",
    )
    subtitle_label.pack(anchor="w", pady=(4, 0))

    output_frame = ctk.CTkFrame(main_frame, corner_radius=16)
    output_frame.pack(fill="both", expand=True, padx=18, pady=(6, 18))

    output_text = ctk.CTkTextbox(output_frame, wrap="word", activate_scrollbars=False)
    output_text.pack(fill="both", expand=True, padx=18, pady=18)
    output_text.configure(state="disabled")

    scrollbar = ctk.CTkScrollbar(output_frame, command=output_text.yview)
    scrollbar.place(relx=1, rely=0, relheight=1, anchor="ne")
    output_text.configure(yscrollcommand=scrollbar.set)

    def append_output(message: str) -> None:
        output_text.configure(state="normal")
        output_text.insert(tk.END, message + "\n")
        output_text.see(tk.END)
        output_text.configure(state="disabled")

    def monitor_privacy() -> None:
        append_output("Checking privacy settings...")
        monitor_settings('privacy', output_text)

    def monitor_all() -> None:
        append_output("Checking all settings...")
        monitor_settings('all', output_text)

    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x", padx=18, pady=(0, 18))

    button_font = ctk.CTkFont(size=15, weight="bold")

    btn_privacy = ctk.CTkButton(
        button_frame,
        text="Monitor Privacy Settings",
        command=monitor_privacy,
        width=200,
        height=44,
        font=button_font,
        corner_radius=12,
    )
    btn_privacy.pack(side="left", expand=True, padx=(0, 10))

    btn_all = ctk.CTkButton(
        button_frame,
        text="Monitor All Settings",
        command=monitor_all,
        width=200,
        height=44,
        font=button_font,
        corner_radius=12,
    )
    btn_all.pack(side="left", expand=True, padx=(10, 0))

    window.mainloop()

# CLI mode
def run_cli(mode: Optional[str] = None, reset_baseline: bool = False) -> None:
    if reset_baseline and os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print("Existing baseline removed. A new snapshot will be created.")

    if mode is None:
        print("Monitor 'all' settings or just 'privacy' settings? (all/privacy): ")
        mode = input().strip().lower()

    if mode not in {'all', 'privacy'}:
        print("Invalid choice. Exiting.")
        return

    monitor_settings(mode)


def parse_arguments(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor Windows privacy settings for unexpected changes.")
    parser.add_argument('--cli', action='store_true', help='Run the application in CLI mode.')
    parser.add_argument(
        '--mode',
        choices=['all', 'privacy'],
        help="Choose whether to monitor 'all' configured settings or only the privacy subset.",
    )
    parser.add_argument(
        '--reset-baseline',
        action='store_true',
        help='Recreate the stored baseline before running a check.',
    )
    return parser.parse_args(argv)

# Entry point
if __name__ == '__main__':
    args = parse_arguments()
    if args.cli:
        run_cli(mode=args.mode, reset_baseline=args.reset_baseline)
    else:
        run_gui()
