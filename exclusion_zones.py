"""Dial-fixed reserved areas for raster height maps and their Tk editor."""
import math

import numpy as np


ZONE_DEFAULTS = dict(shape='rectangle', x_mm=0., y_mm=7., width_mm=7.,
                     height_mm=2., clearance_mm=0.2, feather_mm=0., level=1.)


def validate_zones(zones):
    """Return independent, JSON-safe zone settings with explicit defaults."""
    if zones is None:
        return []
    if not isinstance(zones, (list, tuple)):
        raise ValueError('Exclusion zones must be a list of objects')
    result = []
    for index, supplied in enumerate(zones, 1):
        prefix = f'Exclusion zone {index}: '
        if not isinstance(supplied, dict) or set(supplied) - set(ZONE_DEFAULTS):
            raise ValueError(prefix + 'expected an object with supported zone fields')
        zone = {**ZONE_DEFAULTS, **supplied}
        if zone['shape'] not in ('circle', 'rectangle'):
            raise ValueError(prefix + 'shape must be circle or rectangle')
        for key in ZONE_DEFAULTS.keys() - {'shape'}:
            try:
                zone[key] = float(zone[key])
            except (TypeError, ValueError, OverflowError):
                raise ValueError(prefix + key + ' must be a finite number') from None
            if not math.isfinite(zone[key]):
                raise ValueError(prefix + key + ' must be a finite number')
        if zone['width_mm'] <= 0 or zone['height_mm'] <= 0:
            raise ValueError(prefix + 'width / diameter and height must be positive')
        if zone['clearance_mm'] < 0 or zone['feather_mm'] < 0:
            raise ValueError(prefix + 'clearance and feather must be nonnegative')
        if not 0 <= zone['level'] <= 1:
            raise ValueError(prefix + 'surface level must be between 0 and 1')
        result.append(zone)
    return result


def apply_zones(height, x, y, zones):
    """Flatten zones after inversion. Image Y points down; zone Y points up.

    Feathering extends outward, preserving the entire footprint and clearance.
    Zones remain fixed to the dial when the pattern rotates or changes phase.
    Later zones take precedence where their influence overlaps earlier zones.
    """
    for zone in zones:
        dx = x - zone['x_mm']
        dy = y + zone['y_mm']
        if zone['shape'] == 'circle':
            distance = np.hypot(dx, dy) - zone['width_mm'] / 2
        else:
            qx = np.abs(dx) - zone['width_mm'] / 2
            qy = np.abs(dy) - zone['height_mm'] / 2
            distance = (np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
                        + np.minimum(np.maximum(qx, qy), 0))
        distance = distance - zone['clearance_mm']
        if zone['feather_mm']:
            t = np.clip(distance / zone['feather_mm'], 0, 1)
            blend = t * t * (3 - 2 * t)
            height = zone['level'] + (height - zone['level']) * blend
        else:
            height = np.where(distance <= 0, zone['level'], height)
    return height


def edit_zones(parent, zones, on_apply):
    """Edit a working copy; Apply updates the main preview without closing."""
    import tkinter as tk
    from tkinter import ttk
    from gui_tooltips import add_tooltip

    working = validate_zones(zones)
    window = tk.Toplevel(parent)
    window.title('Exclusion zones')
    window.transient(parent)
    window.resizable(False, False)
    body = ttk.Frame(window, padding=16)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Reserve flat areas for logos, windows, and markers.',
              font=('TkDefaultFont', 13, 'bold')).pack(anchor='w')
    ttk.Label(body, text='Millimeters from dial center. +X = right; +Y = up.\n'
              'White (1) = highest surface. Feathering extends outside clearance.').pack(anchor='w', pady=(6, 10))
    content = ttk.Frame(body)
    content.pack(fill='both')
    listing = tk.Listbox(content, width=30, height=13, exportselection=False)
    listing.pack(side='left', fill='both', padx=(0, 14))
    form = ttk.Frame(content)
    form.pack(side='left', fill='both')
    variables = {key: tk.StringVar(value=str(value)) for key, value in ZONE_DEFAULTS.items()}
    labels = dict(shape='Shape', x_mm='Center X (mm)', y_mm='Center Y (mm)',
                  width_mm='Width / circle diameter (mm)', height_mm='Rectangle height (mm)',
                  clearance_mm='Clearance (mm)', feather_mm='Edge feather (mm)',
                  level='Flat surface level (0–1)')
    entries = {}
    for row, (key, label) in enumerate(labels.items()):
        ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=3)
        if key == 'shape':
            entry = ttk.Combobox(form, textvariable=variables[key], state='readonly',
                                 values=('rectangle', 'circle'), width=17)
        else:
            entry = ttk.Entry(form, textvariable=variables[key], width=19)
        entry.grid(row=row, column=1, pady=3)
        add_tooltip(entry, label + '. Changes are committed with Add or Update selected, then Apply to dial.')
        entries[key] = entry
    error = tk.StringVar()
    ttk.Label(body, textvariable=error, wraplength=590).pack(anchor='w', pady=(10, 0))

    def shape_changed(*_):
        entries['height_mm'].configure(state='disabled' if variables['shape'].get() == 'circle' else 'normal')

    variables['shape'].trace_add('write', shape_changed)

    def refresh(selection=None):
        listing.delete(0, 'end')
        for index, zone in enumerate(working, 1):
            listing.insert('end', f"{index}. {zone['shape']} ({zone['x_mm']:g}, {zone['y_mm']:g})")
        if selection is not None:
            listing.selection_set(selection)
            listing.see(selection)

    def select(event=None):
        if listing.curselection():
            for key, value in working[listing.curselection()[0]].items():
                variables[key].set(str(value))
        error.set('')

    def store(update=False):
        selection = listing.curselection()
        if update and not selection:
            error.set('Select a zone to update.')
            return
        try:
            supplied = {key: value.get() for key, value in variables.items()}
            if supplied['shape'] == 'circle':
                supplied['height_mm'] = supplied['width_mm']
            zone = validate_zones([supplied])[0]
        except ValueError as exc:
            error.set(str(exc))
            return
        if update:
            index = selection[0]
            working[index] = zone
        else:
            index = len(working)
            working.append(zone)
        refresh(index)
        error.set('Zone saved in list. Choose Apply to dial to preview it.')

    def remove():
        if listing.curselection():
            del working[listing.curselection()[0]]
            refresh()
            error.set('Zone removed. Choose Apply to dial to preview the change.')

    def apply():
        on_apply(validate_zones(working))
        error.set(f'Applied {len(working)} exclusion zone(s) to the dial.')

    actions = ttk.Frame(body)
    actions.pack(fill='x', pady=(10, 0))
    for label, callback, help_text in (
        ('Add', lambda: store(), 'Add the form settings as a new zone in the list.'),
        ('Update selected', lambda: store(True), 'Replace the selected zone with the form settings.'),
        ('Remove selected', remove, 'Remove the selected zone from the list.'),
        ('Apply to dial', apply, 'Apply the saved list to the preview, 3D view, and exports.'),
        ('Close', window.destroy, 'Close the editor. Only changes already applied to the dial are kept.'),
    ):
        button = ttk.Button(actions, text=label, command=callback)
        button.pack(side='left', padx=(0, 5))
        add_tooltip(button, help_text)
    listing.bind('<<ListboxSelect>>', select)
    refresh(0 if working else None)
    select()
    shape_changed()
    window.grab_set()
    return window
