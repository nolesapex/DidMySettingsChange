# DidMySettingsChange

![Logo](didmysettingschange.png)

Microsoft has been under heavy scrutiny with how they manage Windows over the years, particularly concerning privacy and telemetry settings. Many users find that after disabling certain settings, these settings are mysteriously re-enabled after updates or without any apparent reason. "DidMySettingsChange" is a Python script designed to help users keep track of their Windows privacy and telemetry settings, ensuring that they stay in control of their privacy without the hassle of manually checking each setting.
Features include:

    Comprehensive Checks: Automatically scans all known Windows privacy and telemetry settings.
    Change Detection: Alerts users if any settings have been changed from their preferred state.
    Customizable Configuration: Allows users to specify which settings to monitor.
    Easy to Use: Simple command-line interface that provides clear and concise output.
    Logs and Reports: Generates detailed logs and reports for auditing and troubleshooting.

    Installation

1. Download Release

2. Unzip the contents

       Usage


To run the script, navigate to the directory where you unzipped the release files and use the following command:



bash (IF YOU USE LINUX!!!!!)

In windows, don't type bash please :/


"python DidMySettingsChange.py"



The script will then check all relevant settings and provide a report on any changes detected.

                                                       Configuration

You can customize which settings to monitor by editing the config.json file. This file contains a list of settings and their expected states. For example:

json

{
    "Telemetry": {
        "path": "HKLM:\\Software\\Policies\\Microsoft\\Windows\\DataCollection",
        "name": "AllowTelemetry",
        "expected_value": "0"
    },
    "AdvertisingID": {
        "path": "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo",
        "name": "Enabled",
        "expected_value": "0"
    },
    "Location": {
        "path": "HKLM:\\System\\CurrentControlSet\\Services\\lfsvc\\Service\\Configuration",
        "name": "Status",
        "expected_value": "Disabled"
    }
    // Add more settings as needed
}

Modify the values as per your preferences before running the script.
                                        
                                         Contributing

We welcome contributions from the community! If you'd like to contribute, please follow these steps:

    Fork the repository.
    Create a new branch for your feature or bugfix.
    Commit your changes with descriptive messages.
    Push your branch and create a pull request.

Issues

If you encounter any issues or have suggestions for improvements, please open an issue on GitHub. We appreciate your feedback and contributions to make "DidMySettingsChange" better!

