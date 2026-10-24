"""Smoke test the actual executable, without a Python runtime on its PATH."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image


root = Path(__file__).resolve().parent.parent
if sys.platform == 'darwin':
    executable = root/'dist/WatchDialPatternGenerator.app/Contents/MacOS/WatchDialPatternGenerator'
else:
    executable = root/'dist/WatchDialPatternGenerator/WatchDialPatternGenerator.exe'

env = os.environ.copy()
env.pop('PYTHONPATH', None)
env.pop('PYTHONHOME', None)
if sys.platform == 'win32':
    windows = Path(env['SystemRoot'])
    env['PATH'] = os.pathsep.join([str(windows), str(windows/'System32')])
else:
    env['PATH'] = '/usr/bin:/bin'
with tempfile.TemporaryDirectory() as directory:
    def run(*args):
        subprocess.run([str(executable), *args], cwd=directory, env=env,
                       check=True, timeout=120)

    run('--bundle-check')
    output = Path(directory)/'smoke.png'
    run('--cli', '--pattern', 'brick', '--pixels', '128', '--output', str(output))
    with Image.open(output) as image:
        assert image.size == (128, 128)
        assert image.getextrema()[1] > 255, '16-bit relief values were lost'
    with Image.open(output.with_name('smoke_8bit.png')) as image:
        assert image.size == (128, 128)
        assert image.mode == 'L'
    assert json.loads(output.with_suffix('.json').read_text())['pattern'] == 'brick'
print('Packaged Tk, Pillow, VTK mesh, and CLI export checks passed.')
