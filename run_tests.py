#!/usr/bin/env python3
"""Run both pattern and Tkinter GUI tests.

On Linux/headless systems, the GUI suite will automatically run under xvfb-run
when a display is not already available.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
commands = [
    [sys.executable, 'test_patterns.py'],
    [sys.executable, '-m', 'unittest', 'test_geometry', 'test_distinct_lattices', 'test_fishscales_relief', 'test_brick', '-v'],
]
for command in commands:
    subprocess.run(command, cwd=here, check=True)

gui_command = [sys.executable, '-m', 'unittest', 'test_gui', '-v']
if sys.platform.startswith('linux') and shutil.which('xvfb-run'):
    gui_command = ['xvfb-run', '-a'] + gui_command
subprocess.run(gui_command, cwd=here, check=True)
print('All pattern and GUI tests passed.')
