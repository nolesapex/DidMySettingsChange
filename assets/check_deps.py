import importlib
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading

# --- Module Check ---
REQUIRED_MODULES = {
    "customtkinter": "customtkinter",
    "requests": "requests",
    "win32api": "pywin32",
    "tkinter": "tkinter",
    "PIL": "Pillow"
}

missing = []

for import_name, pip_name in REQUIRED_MODULES.items():
    try:
        importlib.import_module(import_name)
    except ImportError:
        missing.append(pip_name)

if not missing:
    sys.exit(0)

# --- GUI Installer ---
class DependencyInstaller(tk.Tk):
    def __init__(self, packages):
        super().__init__()
        self.packages = packages
        self.title("Dependency Installer")
        self.geometry("760x480")  # Bigger window
        self.configure(bg="#1e1e1e")  # Dark background

        # Title + Info
        tk.Label(self, text="Missing Dependencies Detected:", font=("Segoe UI", 13, "bold"),
                 fg="white", bg="#1e1e1e").pack(pady=(15, 5))
        tk.Label(self, text=", ".join(packages), fg="#ff7070", bg="#1e1e1e",
                 font=("Segoe UI", 11)).pack()

        # Terminal-style textbox
        self.textbox = scrolledtext.ScrolledText(
            self, width=88, height=22,
            bg="#101010", fg="lime",
            font=("Consolas", 10),
            insertbackground="white", borderwidth=0, relief=tk.FLAT
        )
        self.textbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.textbox.insert(tk.END, "Press 'Install Now' to install required packages...\n")

        # Buttons
        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.pack(pady=5)

        style = {"font": ("Segoe UI", 10), "width": 15, "bg": "#2d2d2d", "fg": "white",
                 "activebackground": "#3c3c3c", "activeforeground": "lime"}

        tk.Button(btn_frame, text="Install Now", command=self.start_install, **style).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=self.quit, **style).pack(side=tk.LEFT, padx=10)

    def start_install(self):
        thread = threading.Thread(target=self.install_packages)
        thread.daemon = True
        thread.start()

    def install_packages(self):
        for pkg in self.packages:
            self.log(f"\nInstalling '{pkg}'...\n")
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                self.log(line)
            process.wait()
            self.log(f"\n✅ Finished installing: {pkg}\n")
        self.log("\n✅ All done. You can now close this window.\n")

    def log(self, text):
        self.textbox.insert(tk.END, text)
        self.textbox.see(tk.END)

if __name__ == "__main__":
    app = DependencyInstaller(missing)
    app.mainloop()
