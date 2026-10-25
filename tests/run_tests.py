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

here = Path(__file__).resolve().parent.parent
commands = [
    [sys.executable, '-m', 'tests.test_patterns'],
    [sys.executable, '-m', 'unittest', 'tests.test_geometry', 'tests.test_distinct_lattices', 'tests.test_fishscales_relief', 'tests.test_brick', 'tests.test_dimples', 'tests.test_relief_inspection', 'tests.test_packaging', '-v'],
]
for command in commands:
    subprocess.run(command, cwd=here, check=True)

gui_command = [sys.executable, '-m', 'unittest', 'tests.test_gui', 'tests.test_pyvista_viewer', '-v']
if sys.platform.startswith('linux') and shutil.which('xvfb-run'):
    gui_command = ['xvfb-run', '-a'] + gui_command
subprocess.run(gui_command, cwd=here, check=True)
print('All pattern and GUI tests passed.')
