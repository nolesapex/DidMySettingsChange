import json
import os
import time
import threading
from threading import Lock
import customtkinter as ctk
import winreg

# -------------------- FILE PATHS --------------------
CONFIG_FILE = 'config.json'
DATABASE_FILE = 'settings_database.json'
LOG_FILE = 'settings_log.txt'
THEME_SETTING_FILE = os.path.join("assets", "themesetting.json")
ICON_PATH = os.path.join("images", "logo.png")

# -------------------- CONFIG HELPERS --------------------
def load_theme_setting():
    if os.path.exists(THEME_SETTING_FILE):
        with open(THEME_SETTING_FILE, 'r') as file:
            return json.load(file).get("theme", "Classic Dark")
    return "Classic Dark"

def save_theme_setting(theme_name):
    os.makedirs("assets", exist_ok=True)
    with open(THEME_SETTING_FILE, 'w') as file:
        json.dump({"theme": theme_name}, file)

def load_config(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as file:
        return json.load(file)

def load_database():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_database(database):
    with open(DATABASE_FILE, 'w') as file:
        json.dump(database, file, indent=4)

# -------------------- REGISTRY ACCESS (DIRECT 64-BIT) --------------------
def read_registry_value(path, name):
    """Read registry value in 64-bit context (bypasses WOW6432 redirection)."""
    try:
        hive_name, subkey = path.split("\\", 1)
        hive = {
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE
        }.get(hive_name.upper())
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value).strip()
    except FileNotFoundError:
        return ""
    except PermissionError:
        return "ACCESS_DENIED"
    except Exception:
        return ""

def normalize_value(val):
    """Normalize for comparison: numeric stays int; strings lowercase; ignore blanks."""
    if val in ("", None, "ACCESS_DENIED"):
        return None
    val = str(val).strip()
    try:
        return int(val)
    except ValueError:
        return val.lower()

# -------------------- SMART MISSING VALUE HANDLER --------------------
# Some privacy keys vanish when enabled (missing = default ON)
MISSING_DEFAULT_ZERO_KEYS = [
    "HttpAcceptLanguageOptOut",                 # "Allow websites to access my language list"
    "TailoredExperiencesWithDiagnosticDataEnabled",  # Tailored Experiences toggle
    "Enabled",                                  # Some toggles disappear when disabled (e.g., Recall)
]

def check_setting(setting):
    """Reads a registry value; handles keys that vanish when toggled ON."""
    path = setting.get("path", "")
    name = setting.get("name", "")
    val = read_registry_value(path, name)

    # Treat missing keys in specific cases as default 0 (ON)
    if val == "":
        if any(keyword.lower() in name.lower() for keyword in MISSING_DEFAULT_ZERO_KEYS):
            return "0", 0
        return "", 1
    return val, 0

def check_settings(config, database):
    """Compare current registry values with saved baseline."""
    changes = []
    current_settings = {}

    for name, info in config.items():
        value, code = check_setting(info)
        norm_val = normalize_value(value)
        current_settings[name] = norm_val

        if norm_val is None:
            continue

        old_val = normalize_value(database.get(name))
        if old_val is None:
            continue

        if norm_val != old_val:
            changes.append((name, norm_val, old_val))

    return changes, current_settings

def log_results(changes):
    with open(LOG_FILE, 'a') as log_file:
        for s, cur, prev in changes:
            log_file.write(f"[CHANGE DETECTED] {s}: was {prev}, now {cur}\n")

# -------------------- UI APPLICATION --------------------
class DidMySettingsChangeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Did My Settings Change")
        self.geometry("800x560+560+260")
        self.resizable(False, False)
        self.log_lock = Lock()
        self.set_icon()

        # Themes
        self.themes = {
            "Classic Dark": {"bg": "#1E1E1E", "fg": "#2B2B2B", "accent": "#0078D7", "text": "#FFFFFF"},
            "Midnight Blue": {"bg": "#0D1B2A", "fg": "#1B263B", "accent": "#415A77", "text": "#E0E1DD"},
            "Cyber Neon": {"bg": "#0C0C0C", "fg": "#121212", "accent": "#39FF14", "text": "#FFFFFF"},
            "System Light": {"bg": "#F3F3F3", "fg": "#FFFFFF", "accent": "#007ACC", "text": "#000000"},
        }
        self.current_theme = load_theme_setting()
        self.apply_theme(self.themes[self.current_theme])

        # Theme selector
        self.theme_menu = ctk.CTkOptionMenu(self, values=list(self.themes.keys()), command=self.change_theme)
        self.theme_menu.set(self.current_theme)
        self.theme_menu.place(x=660, y=10)

        # Log textbox
        self.textbox = ctk.CTkTextbox(self, width=760, height=400, corner_radius=10, font=("Consolas", 13))
        self.textbox.place(x=20, y=70)
        self.textbox.configure(state="disabled")

        # Buttons (2 centered)
        button_y = 490
        button_width = 220
        spacing = 40
        start_x = (800 - (button_width * 2 + spacing)) // 2

        self.monitor_button = ctk.CTkButton(
            self, text="Monitor Privacy Settings", width=button_width, height=38,
            command=self.monitor_privacy_settings,
            fg_color=self.themes[self.current_theme]['accent'], hover_color="#005FCC", corner_radius=12
        )
        self.monitor_button.place(x=start_x, y=button_y)

        self.save_button = ctk.CTkButton(
            self, text="Save Current Settings", width=button_width, height=38,
            command=self.save_current_settings,
            fg_color=self.themes[self.current_theme]['accent'], hover_color="#005FCC", corner_radius=12
        )
        self.save_button.place(x=start_x + button_width + spacing, y=button_y)

    # -------------------- ICON HANDLING --------------------
    def set_icon(self):
        """Set custom window icon (.ico preferred for Windows)."""
        ico_path = os.path.join("images", "logo.ico")
        png_path = os.path.join("images", "logo.png")

        try:
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
                print(f"[ICON] Loaded ICO icon from {ico_path}")
            elif os.path.exists(png_path):
                import tkinter as tk
                img = tk.PhotoImage(file=png_path)
                self.iconphoto(False, img)
                print(f"[ICON] Loaded PNG icon from {png_path}")
            else:
                print("[ICON] No logo.ico or logo.png found in /images/")
        except Exception as e:
            print(f"[ICON ERROR] Failed to set icon: {e}")

    # -------------------- THEME HANDLING --------------------
    def apply_theme(self, theme):
        self.configure(fg_color=theme['bg'])
        ctk.set_default_color_theme("dark-blue")

    def change_theme(self, theme_name):
        theme = self.themes[theme_name]
        self.current_theme = theme_name
        self.apply_theme(theme)
        self.textbox.configure(fg_color=theme['fg'], text_color=theme['text'])
        for btn in [self.monitor_button, self.save_button]:
            btn.configure(fg_color=theme['accent'], hover_color=theme['accent'])
        save_theme_setting(theme_name)

    # -------------------- LOGGING --------------------
    def animated_log(self, message, delay=0.02):
        def run():
            with self.log_lock:
                self.textbox.configure(state="normal")
                for ch in message:
                    self.textbox.insert("end", ch)
                    self.textbox.update_idletasks()
                    time.sleep(delay)
                self.textbox.insert("end", "\n")
                self.textbox.configure(state="disabled")
                self.textbox.see("end")
        threading.Thread(target=run, daemon=True).start()

    # -------------------- ALERT --------------------
    def show_change_alert(self, message):
        theme = self.themes[self.current_theme]
        bubble = ctk.CTkFrame(self, width=680, height=70, corner_radius=25,
                              fg_color=("#2B2B2B", "#1E1E1E"),
                              border_width=1, border_color="#1C1C1C")
        icon = ctk.CTkLabel(bubble, text="⚠️", font=("Segoe UI Emoji", 20))
        label = ctk.CTkLabel(bubble, text=message, font=("Segoe UI Semibold", 14),
                             text_color=theme["text"], justify="left", wraplength=620)
        icon.place(x=10, y=10)
        label.place(x=45, y=10)
        bubble.place(x=-720, y=360)

        def slide_in(pos=-720):
            if pos < 20:
                bubble.place(x=pos, y=360)
                self.after(10, lambda: slide_in(pos + 20))
            else:
                self.after(5000, bubble.destroy)
        slide_in()

    # -------------------- ACTIONS --------------------
    def monitor_privacy_settings(self):
        config = load_config(CONFIG_FILE)
        baseline = load_database()
        self.animated_log("Checking privacy settings...")

        changes, _ = check_settings(config, baseline)
        if not changes:
            self.animated_log("No privacy setting changes detected.")
        else:
            self.animated_log(f"{len(changes)} privacy change(s) detected:")
            for s, c, p in changes:
                self.animated_log(f"- {s}: was {p}, now {c}")
                self.show_change_alert(f"{s} changed from {p} to {c}")
            log_results(changes)

    def save_current_settings(self):
        config = load_config(CONFIG_FILE)
        snapshot = {}
        self.animated_log("Saving current settings as baseline...")

        for s, info in config.items():
            val, code = check_setting(info)
            norm_val = normalize_value(val)
            if code == 0 and norm_val is not None:
                snapshot[s] = norm_val
                self.animated_log(f"[SAVED] {s}: {val}")
            else:
                self.animated_log(f"[SKIPPED] {s}: Key missing or inaccessible.")

        save_database(snapshot)
        self.animated_log("✅ Baseline saved. Future checks will compare against this snapshot.")

# -------------------- RUN --------------------
if __name__ == "__main__":
    app = DidMySettingsChangeApp()
    app.mainloop()


