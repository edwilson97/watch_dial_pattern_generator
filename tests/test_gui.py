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
    def exercise_exclusion_editor(self, root):
        root.update()
        buttons = {w.cget('text'): w for w in descendants(root) if isinstance(w, ttk.Button)}
        with patch.object(app, 'render_preview', wraps=app.render_preview) as preview:
            buttons['Exclusion zones (0)…'].invoke()
            root.update()
            editor = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            controls = {w.cget('text'): w for w in descendants(editor) if isinstance(w, ttk.Button)}
            fields = {}
            for w in descendants(editor):
                if isinstance(w, (ttk.Entry, ttk.Combobox)):
                    row = w.grid_info()['row']
                    label = next(c for c in w.master.winfo_children()
                                 if isinstance(c, ttk.Label) and c.grid_info()['row'] == row)
                    fields[label.cget('text')] = w
            controls['Add'].invoke()
            controls['Apply to dial'].invoke()
            root.update()
            zones = preview.call_args.kwargs['exclusion_zones']
            self.assertEqual(len(zones), 1)
            self.assertEqual(zones[0]['shape'], 'rectangle')
            fields['Shape'].set('circle')
            fields['Shape'].event_generate('<<ComboboxSelected>>')
            self.assertTrue(fields['Rectangle height (mm)'].instate(['disabled']))
            fields['Width / circle diameter (mm)'].delete(0, 'end')
            fields['Width / circle diameter (mm)'].insert(0, '-1')
            controls['Update selected'].invoke()
            controls['Apply to dial'].invoke()
            self.assertEqual(preview.call_args.kwargs['exclusion_zones'][0]['shape'], 'rectangle')
            fields['Width / circle diameter (mm)'].delete(0, 'end')
            fields['Width / circle diameter (mm)'].insert(0, '3')
            controls['Update selected'].invoke()
            controls['Apply to dial'].invoke()
            zone = preview.call_args.kwargs['exclusion_zones'][0]
            self.assertEqual(zone['shape'], 'circle')
            self.assertEqual(zone['width_mm'], 3)
            controls['Close'].invoke()
            with patch('inspection.open_inspection') as launch:
                buttons['Inspect enlarged / 3D'].invoke()
                self.assertEqual(launch.call_args.args[2]['exclusion_zones'][0], zone)
                launch.call_args.kwargs['on_ready']()
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'zones.png'
                with patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)), \
                     patch('tkinter.messagebox.showinfo'):
                    buttons['Export PNG + settings'].invoke()
                import json
                meta = json.loads(target.with_suffix('.json').read_text())
                self.assertEqual(meta['exclusion_zones'][0], zone)
            # Reopen, remove, and apply; closing an unapplied edit discards it.
            buttons['Exclusion zones (0)…'].invoke()
            root.update()
            editor = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            controls = {w.cget('text'): w for w in descendants(editor) if isinstance(w, ttk.Button)}
            controls['Remove selected'].invoke()
            controls['Apply to dial'].invoke()
            self.assertEqual(preview.call_args.kwargs['exclusion_zones'], [])
            controls['Add'].invoke()
            controls['Close'].invoke()
            self.assertEqual(preview.call_args.kwargs['exclusion_zones'], [])
            # Reset clears applied zones as well as the ordinary controls.
            buttons['Exclusion zones (0)…'].invoke()
            root.update()
            editor = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            controls = {w.cget('text'): w for w in descendants(editor) if isinstance(w, ttk.Button)}
            controls['Add'].invoke()
            controls['Apply to dial'].invoke()
            controls['Close'].invoke()
            buttons['Reset to defaults'].invoke()
            self.assertEqual(preview.call_args.kwargs['exclusion_zones'], [])

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
                    self.assertNotIn('Update preview', buttons)
                    self.assertIn('Reset to defaults', buttons)
                    # Every editable control has help, including hidden pattern fields.
                    controls = [w for w in widgets if isinstance(
                        w, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton))]
                    self.assertTrue(all(w.tooltip.text for w in controls))
                    # Hover help appears without stealing focus, then closes on exit.
                    button = buttons['Reset to defaults']
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
                    # Wheel events over inputs and labels scroll their containing panel.
                    canvas = next(w for w in widgets if isinstance(w, tk.Canvas))
                    aqua = root.tk.call('tk', 'windowingsystem') == 'aqua'
                    delta = 2 if aqua else 120
                    entry = fields['Area width (mm)'][1]
                    original_value = entry.get()
                    canvas.yview_moveto(0)
                    entry.event_generate('<MouseWheel>', delta=-delta)
                    root.update()
                    self.assertGreater(canvas.yview()[0], 0)
                    self.assertEqual(entry.get(), original_value)
                    entry.event_generate('<MouseWheel>', delta=delta)
                    root.update()
                    self.assertEqual(canvas.yview()[0], 0)
                    precise_scroll = bool(root.tk.call('info', 'commands', 'tk::PreciseScrollDeltas'))
                    if precise_scroll:
                        # Tk 9 sends real trackpad gestures as packed X/Y deltas,
                        # rather than the MouseWheel events tested above.
                        entry.event_generate('<TouchpadScroll>', delta=(3 << 16) | (-32 & 0xffff))
                        root.update()
                        self.assertGreater(canvas.yview()[0], 0)
                        self.assertEqual(entry.get(), original_value)
                        entry.event_generate('<TouchpadScroll>', delta=32)
                        root.update()
                        self.assertEqual(canvas.yview()[0], 0)
                        entry.event_generate('<TouchpadScroll>', delta=3 << 16)
                        root.update()
                        self.assertEqual(canvas.yview()[0], 0)
                        # Small deltas accumulate instead of being discarded.
                        for _ in range(16):
                            entry.event_generate('<TouchpadScroll>', delta=0xffff)
                        root.update()
                        self.assertGreater(canvas.yview()[0], 0)
                        canvas.yview_moveto(0)
                    label = fields['Area width (mm)'][0].winfo_children()[0]
                    label.event_generate('<MouseWheel>', delta=-delta)
                    root.update()
                    self.assertGreater(canvas.yview()[0], 0)
                    previous_view = canvas.yview()
                    buttons['Reset to defaults'].event_generate('<MouseWheel>', delta=-delta)
                    self.assertEqual(canvas.yview(), previous_view)
                    canvas.yview_moveto(0)
                    # Parameter dropdowns also scroll the panel without changing selection.
                    combo.current(list(app.PATTERNS).index('fishscales'))
                    combo.event_generate('<<ComboboxSelected>>')
                    root.update()
                    style = fields['Fish scales relief style'][1]
                    canvas.yview_moveto(1)
                    root.update()
                    previous_view, previous_style = canvas.yview(), style.get()
                    style.event_generate('<MouseWheel>', delta=delta)
                    root.update()
                    self.assertLess(canvas.yview()[0], previous_view[0])
                    self.assertEqual(style.get(), previous_style)
                    if precise_scroll:
                        canvas.yview_moveto(1)
                        root.update()
                        previous_view = canvas.yview()
                        style.event_generate('<TouchpadScroll>', delta=32)
                        root.update()
                        self.assertLess(canvas.yview()[0], previous_view[0])
                        self.assertEqual(style.get(), previous_style)
                    canvas.yview_moveto(0)
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
                                       ('horizontalribbing','Groove width (mm)'),
                                       ('graindorge','Grain length / width ratio'),
                                       ('flamme','Flame outward taper (0–1)'),
                                       ('panier','Panier ribbon curvature (0–2)'),
                                       ('rosette','Rosette second harmonic (0–1)'),
                                       ('fishscales','Fish scales relief style'),
                                       ('brick','Brick width (mm)'),
                                       ('brick','Brick joint width (mm)'),
                                       ('brick','Brick relief style'),
                                       ('brick','Brick layout'),
                                       ('dimples','Dimple diameter (mm)'),
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
                    layout = fields['Brick layout'][1]
                    layout.set('herringbone')
                    layout.event_generate('<<ComboboxSelected>>')
                    root.update()
                    self.assertTrue(fields['Brick row offset (0–1)'][1].instate(['disabled']))
                    self.assertFalse(any(w.cget('text').startswith('Preview error:')
                                         for w in widgets if isinstance(w, ttk.Label)))
                    layout.set('running_bond')
                    layout.event_generate('<<ComboboxSelected>>')
                    root.update()
                    self.assertFalse(fields['Brick row offset (0–1)'][1].instate(['disabled']))
                    layout.set('herringbone')
                    layout.event_generate('<<ComboboxSelected>>')
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
                    groove = fields['Groove width (mm)'][1]
                    depth = fields['Target depth (mm)'][1]
                    groove.event_generate('<FocusOut>')
                    root.update()
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
                        previous_cursor = root.cget('cursor')
                        buttons['Inspect enlarged / 3D'].invoke()
                        launch.assert_called_once()
                        self.assertEqual(launch.call_args.args[1].shape, (256, 256))
                        expected_cursor = ('spinning' if root.tk.call('tk', 'windowingsystem') == 'aqua'
                                           else 'watch')
                        self.assertEqual(root.cget('cursor'), expected_cursor)
                        self.assertTrue(buttons['Inspect enlarged / 3D'].instate(['disabled']))
                        launch.call_args.kwargs['on_ready']()
                        self.assertEqual(root.cget('cursor'), previous_cursor)
                        self.assertFalse(buttons['Inspect enlarged / 3D'].instate(['disabled']))
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
                    with patch('inspection.open_inspection', side_effect=RuntimeError('Launch failed')), \
                         patch('tkinter.messagebox.showerror') as showerror:
                        buttons['Inspect enlarged / 3D'].invoke()
                        self.assertEqual(root.cget('cursor'), previous_cursor)
                        self.assertFalse(buttons['Inspect enlarged / 3D'].instate(['disabled']))
                        showerror.assert_called_once_with('Inspection failed', 'Launch failed')
                    buttons['Export PNG + settings'].invoke()
                    self.assertTrue(target.is_file())
                    with Image.open(target) as im:
                        self.assertEqual(im.size, (256, 256))
                        self.assertIn(im.mode, ('I;16', 'I;16B', 'I'))
                    with Image.open(target.with_name('gui_export_8bit.png')) as im:
                        self.assertEqual(im.mode, 'L')
                    self.assertTrue(target.with_suffix('.json').is_file())
                    self.exercise_exclusion_editor(root)
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
