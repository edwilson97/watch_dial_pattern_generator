"""End-to-end Tkinter smoke/regression tests; run with a real display or xvfb-run."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from PIL import Image
import dial_patterns as app


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class GuiTests(unittest.TestCase):
    def test_pattern_controls_preview_and_export(self):
        errors = []
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'gui_export.png'

            def scripted_mainloop(root, *args, **kwargs):
                try:
                    root.update_idletasks()
                    widgets = list(descendants(root))
                    combo = next(w for w in widgets if isinstance(w, ttk.Combobox) and tuple(w.cget('values')) == tuple(app.PATTERNS.values()))
                    buttons = {w.cget('text'): w for w in widgets if isinstance(w, ttk.Button)}
                    self.assertIn('Export PNG + settings', buttons)
                    self.assertIn('Update preview', buttons)
                    self.assertIn('Reset to defaults', buttons)
                    # Every editable control has help, including hidden pattern fields.
                    controls = [w for w in widgets if isinstance(
                        w, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton))]
                    self.assertTrue(all(w.tooltip.text for w in controls))
                    # Hover help appears without stealing focus, then closes on exit.
                    button = buttons['Update preview']
                    button.focus_force()
                    root.update()
                    button.event_generate('<Enter>')
                    deadline = time.monotonic() + 2
                    while button.tooltip.window is None and time.monotonic() < deadline:
                        root.update()
                        time.sleep(.01)
                    self.assertIsNotNone(button.tooltip.window)
                    self.assertEqual(root.focus_get(), button)
                    button.event_generate('<Leave>')
                    self.assertIsNone(button.tooltip.window)
                    button.event_generate('<Enter>')
                    button.event_generate('<Leave>')
                    self.assertIsNone(button.tooltip.timer)
                    fields = {}
                    for w in widgets:
                        if isinstance(w, ttk.Frame):
                            labels = [c.cget('text') for c in w.winfo_children() if isinstance(c, ttk.Label)]
                            inputs = [c for c in w.winfo_children() if isinstance(c, (ttk.Entry, ttk.Combobox))]
                            if labels and inputs and labels[0] in {spec[0] for spec in app.FIELD_SPECS.values()}:
                                fields[labels[0]] = (w, inputs[0])
                    for index, pattern in enumerate(app.PATTERNS):
                        combo.current(index)
                        combo.event_generate('<<ComboboxSelected>>')
                        root.update()
                        expected = set(app.COMMON_FIELDS + app.PATTERN_FIELDS[pattern])
                        visible = {label for label, (frame, _) in fields.items() if frame.winfo_manager()}
                        expected_labels = {app.FIELD_SPECS[key][0] for key in expected}
                        self.assertEqual(visible, expected_labels, pattern)
                    # Verify refined controls appear only for their owning pattern.
                    for pat, label in [('hobnail','Hobnail plateau width (mm)'),
                                       ('wave','Wave lateral meander (mm)'),
                                       ('graindorge','Grain length / width ratio'),
                                       ('flamme','Flame outward taper (0–1)'),
                                       ('panier','Panier ribbon curvature (0–2)'),
                                       ('rosette','Rosette second harmonic (0–1)'),
                                       ('fishscales','Fish scales relief style'),
                                       ('brick','Brick width (mm)'),
                                       ('brick','Brick joint width (mm)'),
                                       ('brick','Brick relief style'),
                                       ('asanoha','Asanoha line width (mm)'),
                                       ('asanoha','Asanoha relief style'),
                                       ('isometriccubes','Cube border groove (mm)'),
                                       ('isometriccubes','Cube face height step (0–0.5)')]:
                        combo.current(list(app.PATTERNS).index(pat))
                        combo.event_generate('<<ComboboxSelected>>')
                        root.update()
                        self.assertTrue(fields[label][0].winfo_manager(), pat)
                    # Reset must restore ALL values, including hidden fields and toggles.
                    combo.current(list(app.PATTERNS).index('brick'))
                    combo.event_generate('<<ComboboxSelected>>')
                    root.update()
                    fields['Brick width (mm)'][1].delete(0, 'end')
                    fields['Brick width (mm)'][1].insert(0, '2.25')
                    fields['Brick relief style'][1].set('rounded')
                    # Verify the control works for both edited and hidden fields.
                    combo.current(list(app.PATTERNS).index('tapisserie'))
                    combo.event_generate('<<ComboboxSelected>>')
                    root.update()
                    fields['Groove width (mm)'][1].delete(0, 'end')
                    fields['Groove width (mm)'][1].insert(0, '0.30')
                    checks = [w for w in widgets if isinstance(w, ttk.Checkbutton)]
                    self.assertEqual(len(checks), 2)
                    checks[0].invoke()
                    checks[1].invoke()
                    root.update()
                    buttons['Reset to defaults'].invoke()
                    root.update()
                    self.assertEqual(combo.current(), 0)
                    for key, (label, default) in app.FIELD_SPECS.items():
                        if key == 'pitch_mm':
                            default = str(app.default_pitch('hobnail'))
                        self.assertEqual(fields[label][1].get(), default, key)
                    self.assertTrue(all(not w.instate(['selected']) for w in checks))
                    visible = {label for label,(frame,_) in fields.items() if frame.winfo_manager()}
                    self.assertEqual(visible, {app.FIELD_SPECS[k][0] for k in app.COMMON_FIELDS + app.PATTERN_FIELDS['hobnail']})
                    combo.current(list(app.PATTERNS).index('tapisserie'))
                    combo.event_generate('<<ComboboxSelected>>')
                    root.update()
                    for name, value in [('Output pixels / side', '256'), ('Groove width (mm)', '0.30')]:
                        match = [entry for label, (_, entry) in fields.items() if label == name]
                        self.assertEqual(len(match), 1, name)
                        match[0].delete(0, 'end')
                        match[0].insert(0, value)
                    buttons['Update preview'].invoke()
                    groove = fields['Groove width (mm)'][1]
                    depth = fields['Target depth (mm)'][1]
                    groove.focus_force()
                    root.update()
                    with patch.object(app, 'render', wraps=app.render) as preview_render:
                        groove.delete(0, 'end')
                        groove.insert(0, '0.25')
                        root.update()
                        preview_render.assert_not_called()
                        depth.focus_set()
                        root.update()
                        preview_render.assert_called_once()
                        self.assertEqual(preview_render.call_args.kwargs['groove_width_mm'], .25)
                        # Moving between unchanged fields does not render again.
                        groove.focus_set()
                        root.update()
                        depth.focus_set()
                        root.update()
                        self.assertEqual(preview_render.call_count, 1)
                        # Invalid values leave the last valid preview in place.
                        preview_widget = next(w for w in descendants(root)
                                              if isinstance(w, ttk.Label) and w.cget('image'))
                        image = preview_widget.cget('image')
                        groove.focus_set()
                        root.update()
                        groove.delete(0, 'end')
                        depth.focus_set()
                        root.update()
                        self.assertEqual(preview_widget.cget('image'), image)
                        groove.insert(0, '0.30')
                    with patch('inspection.open_inspection') as launch:
                        launch.return_value.alive.return_value = True
                        buttons['Inspect enlarged / 3D'].invoke()
                        launch.assert_called_once()
                        self.assertEqual(launch.call_args.args[1].shape, (256, 256))
                        session = launch.return_value

                        def pump_until(predicate, timeout=3):
                            deadline = time.monotonic() + timeout
                            while not predicate() and time.monotonic() < deadline:
                                root.update()
                                time.sleep(.01)
                            self.assertTrue(predicate())

                        groove = fields['Groove width (mm)'][1]
                        groove.delete(0, 'end')
                        groove.insert(0, '0.25')
                        groove.delete(0, 'end')
                        groove.insert(0, '0.15')
                        pump_until(lambda: session.update.call_count == 1)
                        updated, meta = session.update.call_args.args
                        expected, _ = app.render(pattern='tapisserie', pixels=256, groove_width_mm=.15)
                        import numpy as np
                        np.testing.assert_array_equal(updated, expected)
                        # An incomplete entry retains the last good viewer frame.
                        groove.delete(0, 'end')
                        deadline = time.monotonic() + .5
                        while time.monotonic() < deadline:
                            root.update()
                            time.sleep(.01)
                        self.assertEqual(session.update.call_count, 1)
                        groove.insert(0, '0.20')
                        checks[0].invoke()
                        combo.current(list(app.PATTERNS).index('wave'))
                        combo.event_generate('<<ComboboxSelected>>')
                        pump_until(lambda: session.update.call_count == 2)
                        self.assertEqual(session.update.call_args.args[1]['pattern'], 'wave')
                        buttons['Reset to defaults'].invoke()
                        # Keep the native test small while verifying reset propagation.
                        pixels = fields['Output pixels / side'][1]
                        pixels.delete(0, 'end')
                        pixels.insert(0, '256')
                        pump_until(lambda: session.update.call_count == 3)
                        self.assertEqual(session.update.call_args.args[1]['pattern'], 'hobnail')
                    buttons['Export PNG + settings'].invoke()
                    self.assertTrue(target.is_file())
                    with Image.open(target) as im:
                        self.assertEqual(im.size, (256, 256))
                        self.assertIn(im.mode, ('I;16', 'I;16B', 'I'))
                    with Image.open(target.with_name('gui_export_8bit.png')) as im:
                        self.assertEqual(im.mode, 'L')
                    self.assertTrue(target.with_suffix('.json').is_file())
                except Exception as exc:
                    errors.append(exc)
                finally:
                    root.destroy()

            with patch.object(tk.Tk, 'mainloop', scripted_mainloop), \
                 patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)), \
                 patch('tkinter.messagebox.showinfo'), \
                 patch('tkinter.messagebox.showerror', side_effect=lambda *args: self.fail(str(args))):
                app.run_gui()
        if errors:
            raise errors[0]


if __name__ == '__main__':
    unittest.main()
