import os
import sys
import subprocess

# Run dependency checker (waits until it finishes)
check_script = os.path.join("assets", "check_deps.py")
subprocess.call([sys.executable, check_script])

# Run your GUI afterward
splash_script = os.path.join(os.getcwd(), "splash_screen.py")
subprocess.call([sys.executable, splash_script])
