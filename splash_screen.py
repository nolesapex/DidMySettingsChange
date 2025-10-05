import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import subprocess
import sys

gif_path = "Splash.gif"
next_script = "DidMySettingsChange.py"

# Desired display size (small splash box)
desired_size = (300, 300)

# Setup splash window
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg='black')

# Load GIF
img = Image.open(gif_path)

# Create base image with target size
base = Image.new("RGBA", desired_size)

frames = []
durations = []

for frame in ImageSequence.Iterator(img):
    # Resize and paste each frame to avoid disposal/composition issues
    frame = frame.convert("RGBA").resize(desired_size, Image.LANCZOS)
    base.paste(frame, (0, 0), frame)
    frames.append(ImageTk.PhotoImage(base.copy()))
    durations.append(frame.info.get('duration', 100))

# Create label to show frames
label = tk.Label(root, bg='black')
label.pack()

# Center splash window on screen
w, h = desired_size
x = (root.winfo_screenwidth() - w) // 2
y = (root.winfo_screenheight() - h) // 2
root.geometry(f"{w}x{h}+{x}+{y}")

# Animate frames
def animate(i=0):
    label.configure(image=frames[i])
    delay = durations[i]
    root.after(delay, animate, (i + 1) % len(frames))

# Launch app after 3 seconds
def launch_main_app():
    root.destroy()
    subprocess.Popen([sys.executable, next_script])

# Run
root.after(0, animate)
root.after(3000, launch_main_app)
root.mainloop()
