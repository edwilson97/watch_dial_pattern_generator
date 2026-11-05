"""Bounded sliders paired with the GUI's precise numeric entry fields."""
import math
import tkinter as tk
from tkinter import ttk


def add_range_slider(parent, variable, bounds, on_change):
    """Keep a slider synchronized without rewriting typed or incomplete values."""
    lower, upper, step = bounds
    position = tk.DoubleVar(master=parent, value=lower)
    slider = ttk.Scale(parent, from_=lower, to=upper, variable=position,
                       orient='horizontal', length=180)

    def sync(*_):
        try:
            value = float(variable.get())
        except ValueError:
            return
        if math.isfinite(value):
            # An exact typed value may fall between slider increments.
            position.set(min(upper, max(lower, value)))

    def change(raw):
        if slider.instate(['disabled']):
            return
        value = min(upper, max(lower, round(float(raw) / step) * step))
        variable.set(f'{value:.6g}')
        on_change()

    def move(delta):
        change(position.get() + delta)
        return 'break'

    sync()
    trace = variable.trace_add('write', sync)
    slider.configure(command=change)
    for key, delta in (('Left', -step), ('Down', -step), ('Right', step), ('Up', step)):
        slider.bind('<' + key + '>', lambda event, delta=delta: move(delta))
    slider.bind('<Home>', lambda event: move(lower - position.get()))
    slider.bind('<End>', lambda event: move(upper - position.get()))

    def point(event):
        if not slider.instate(['disabled']):
            if event.type == tk.EventType.ButtonPress:
                slider.focus_set()
            change(slider.get(event.x, event.y))
        # The native scale class steps by 1 on trough clicks, which spans the
        # entire range of a 0–1 control. Use its pixel-to-value mapping instead
        # and suppress native stepping/repeat behavior during clicks and drags.
        return 'break'

    slider.bind('<ButtonPress-1>', point)
    slider.bind('<B1-Motion>', point)
    slider.bind('<ButtonRelease-1>', point)

    def cleanup(event):
        if event.widget is slider:
            variable.trace_remove('write', trace)

    slider.bind('<Destroy>', cleanup)
    return slider
