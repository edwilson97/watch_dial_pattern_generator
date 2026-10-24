"""Regression coverage for subprocesses in source and standalone builds."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import frozen_entry
import inspection


class PackagingTests(unittest.TestCase):
    def test_source_helper_uses_python_and_module(self):
        with patch.object(sys, 'frozen', False, create=True):
            command = inspection.helper_command(Path('a folder/source.npz'))
        self.assertEqual(command, [sys.executable, str(Path(inspection.__file__).resolve()),
                                   str(Path('a folder/source.npz'))])

    def test_frozen_helper_reenters_executable(self):
        with patch.object(sys, 'frozen', True, create=True):
            command = inspection.helper_command('--screenshot-dialog', 'name.png', 'result.txt')
        self.assertEqual(command, [sys.executable, '--inspection-helper',
                                   '--screenshot-dialog', 'name.png', 'result.txt'])

    def test_entry_dispatches_viewer_without_opening_generator(self):
        with patch.object(sys, 'argv', ['app', '--inspection-helper', 'snapshot.npz']), \
                patch('inspection.main') as viewer, patch('dial_patterns.main') as generator:
            frozen_entry.main()
        viewer.assert_called_once_with(['snapshot.npz'])
        generator.assert_not_called()

    def test_screenshot_dialog_result_does_not_depend_on_stdout(self):
        for selection in ('', '/a folder/dial café.png'):
            with self.subTest(selection=selection):
                def child(command, **kwargs):
                    self.assertIn('--screenshot-dialog', command)
                    Path(command[-1]).write_text(selection, encoding='utf-8')
                with patch('inspection.subprocess.run', side_effect=child):
                    self.assertEqual(inspection.screenshot_path('dial.png'), selection)

    def test_screenshot_helper_writes_selection_and_closes_tk(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory)/'selection.txt'
            with patch('tkinter.Tk') as tk, \
                    patch('tkinter.filedialog.asksaveasfilename', return_value='chosen.png'):
                inspection.main(['--screenshot-dialog', 'initial.png', str(result)])
            self.assertEqual(result.read_text(encoding='utf-8'), 'chosen.png')
            tk.return_value.destroy.assert_called_once()

    def test_frozen_inspection_launches_helper_and_cleans_snapshot(self):
        import numpy as np
        parent = Mock()
        with patch.object(sys, 'frozen', True, create=True), \
                patch('inspection.subprocess.Popen') as popen:
            session = inspection.open_inspection(parent, np.zeros((4, 4)), {'pattern': 'brick'})
            command = popen.call_args.args[0]
            self.assertEqual(command[:2], [sys.executable, '--inspection-helper'])
            self.assertTrue(session.source.exists())
            popen.return_value.poll.return_value = 0
            popen.return_value.returncode = 0
            parent.after.call_args.args[1]()
            self.assertFalse(session.source.exists())


if __name__ == '__main__':
    unittest.main()
