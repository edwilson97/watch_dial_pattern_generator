"""End-to-end Tkinter smoke/regression tests; run with a real display or xvfb-run."""
import tempfile
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
